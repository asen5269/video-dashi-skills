import argparse
import contextlib
import gc
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import SAM, YOLO


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames",
            "-show_entries", "stream=codec_type,width,height,r_frame_rate,nb_read_frames",
            "-show_entries", "format=duration,size", "-of", "json", str(path),
        ],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout)


def parse_rect(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    parts = tuple(float(x) for x in value.split(","))
    if len(parts) != 4 or any(x < 0 or x > 1 for x in parts):
        raise argparse.ArgumentTypeError("watermark rect must be normalized x,y,w,h values from 0 to 1")
    x, y, w, h = parts
    if x + w > 1 or y + h > 1:
        raise argparse.ArgumentTypeError("watermark rect exceeds frame bounds")
    return parts


def largest_component(mask: np.ndarray) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if count <= 1:
        return mask
    largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    return (labels == largest).astype(np.uint8) * 255


def clean_mask(mask: np.ndarray, median: int, morph_kernel: np.ndarray) -> np.ndarray:
    mask = largest_component(mask)
    if median > 1:
        mask = cv2.medianBlur(mask, median)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, morph_kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, morph_kernel)
    return largest_component(mask)


def detect_people(detector, frame: np.ndarray, args, device, width: int, height: int):
    result = detector.predict(
        frame, classes=[0], conf=args.conf, iou=args.iou,
        imgsz=args.det_imgsz, device=device, verbose=False,
    )[0]
    boxes = result.boxes.xyxy.cpu().numpy() if result.boxes is not None else []
    polygons = result.masks.xy if result.masks is not None else []
    found = []
    for box, polygon in zip(boxes, polygons):
        if (box[2] - box[0]) * (box[3] - box[1]) <= width * height * 0.001:
            continue
        coarse = np.zeros((height, width), np.uint8)
        cv2.fillPoly(coarse, [np.round(polygon).astype(np.int32)], 255)
        found.append((box, coarse))
    return found


def masks_per_frame(detector, sam, frame, args, device, width, height, dilate_kernel, morph_kernel):
    detections = detect_people(detector, frame, args, device, width, height)
    if not detections:
        return []
    boxes = [box.tolist() for box, _ in detections]
    result = sam.predict(frame, bboxes=boxes, imgsz=args.sam_imgsz, device=device, verbose=False)[0]
    if result.masks is None:
        return []
    masks = []
    for prediction, (box, coarse) in zip(result.masks.data.cpu().numpy(), detections):
        mask = cv2.resize(prediction.astype(np.float32), (width, height), interpolation=cv2.INTER_LINEAR)
        mask = (mask > 0.5).astype(np.uint8) * 255
        x1, y1, x2, y2 = box
        px, py = (x2 - x1) * args.box_pad, (y2 - y1) * args.box_pad
        x1, y1 = max(0, int(x1 - px)), max(0, int(y1 - py))
        x2, y2 = min(width, int(x2 + px)), min(height, int(y2 + py))
        limited = np.zeros((height, width), np.uint8)
        limited[y1:y2, x1:x2] = mask[y1:y2, x1:x2]
        coarse = cv2.dilate(coarse, dilate_kernel, iterations=1)
        masks.append(clean_mask(cv2.bitwise_and(limited, coarse), args.median, morph_kernel))
    return masks


def masks_hybrid(predictor, detector, frames, frame_dir, args, device, width, height, morph_kernel):
    detections = detect_people(detector, frames[0], args, device, width, height)
    if not detections:
        return {}
    shutil.rmtree(frame_dir, ignore_errors=True)
    frame_dir.mkdir(parents=True)
    for index, frame in enumerate(frames):
        cv2.imwrite(str(frame_dir / f"{index:05d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

    masks_by_frame: dict[int, list[np.ndarray]] = {}
    autocast = torch.autocast("cuda", dtype=torch.bfloat16) if torch.cuda.is_available() else contextlib.nullcontext()
    with torch.inference_mode(), autocast:
        state = predictor.init_state(
            video_path=str(frame_dir), offload_video_to_cpu=True, offload_state_to_cpu=True,
        )
        try:
            for object_id, (box, _) in enumerate(detections):
                predictor.add_new_points_or_box(state, frame_idx=0, obj_id=object_id, box=box)
            for frame_index, _, logits in predictor.propagate_in_video(state):
                masks = []
                for prediction in logits:
                    mask = (prediction[0] > 0).cpu().numpy().astype(np.uint8) * 255
                    if mask.shape != (height, width):
                        mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
                    masks.append(clean_mask(mask, args.median, morph_kernel))
                masks_by_frame[int(frame_index)] = masks
        finally:
            predictor.reset_state(state)
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return masks_by_frame


def render_frame(frame, masks, gradient, outline, outline_width, watermark_mask):
    if watermark_mask is not None:
        frame = cv2.inpaint(frame, watermark_mask, 5, cv2.INPAINT_TELEA)
    for mask in masks:
        frame[mask > 0] = gradient[mask > 0]
    if outline_width > 0:
        for mask in masks:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(frame, contours, -1, outline, outline_width, cv2.LINE_AA)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--mode", choices=["hybrid", "per-frame"], default="hybrid")
    parser.add_argument("--redetect-interval", type=int, default=24)
    parser.add_argument("--detector", default="yolo11s-seg.pt")
    parser.add_argument("--sam", default="sam2.1_t.pt")
    parser.add_argument("--sam-config", default="configs/sam2.1/sam2.1_hiera_t.yaml")
    parser.add_argument("--det-imgsz", type=int, default=1280)
    parser.add_argument("--sam-imgsz", type=int, default=1024)
    parser.add_argument("--conf", type=float, default=0.08)
    parser.add_argument("--iou", type=float, default=0.50)
    parser.add_argument("--coarse-dilate", type=int, default=15)
    parser.add_argument("--box-pad", type=float, default=0.05)
    parser.add_argument("--median", type=int, default=9)
    parser.add_argument("--morph", type=int, default=5)
    parser.add_argument("--outline", type=int, default=1)
    parser.add_argument("--fill-top", default="#2c0977")
    parser.add_argument("--fill-bottom", default="#180348")
    parser.add_argument("--outline-color", default="#ffffff")
    parser.add_argument("--watermark-rect")
    parser.add_argument("--keep-audio", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--crf", type=int, default=20)
    args = parser.parse_args()

    if args.redetect_interval < 1:
        raise SystemExit("--redetect-interval must be at least 1")
    if args.median > 1 and args.median % 2 == 0:
        raise SystemExit("--median must be odd")
    if not torch.cuda.is_available() and not args.allow_cpu:
        raise SystemExit("CUDA PyTorch required. Install a CUDA build or pass --allow-cpu for very slow processing.")
    device = 0 if torch.cuda.is_available() else "cpu"
    video = Path(args.video).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / "_person_mask_work.mp4"
    frame_dir = out_dir / "_person_mask_frames"
    output = out_dir / "jimeng_person_mask.mp4"

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(work), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    detector = YOLO(args.detector)
    sam = None
    predictor = None
    actual_mode = args.mode
    if actual_mode == "hybrid":
        try:
            from sam2.build_sam import build_sam2_video_predictor
            predictor = build_sam2_video_predictor(args.sam_config, args.sam, device="cuda" if device == 0 else "cpu")
        except ImportError:
            actual_mode = "per-frame"
            print("sam2 VOS package unavailable; falling back to per-frame refinement")
    if actual_mode == "per-frame":
        sam = SAM(args.sam)

    rect = parse_rect(args.watermark_rect)
    watermark_mask = None
    if rect:
        x, y, w, h = rect
        watermark_mask = np.zeros((height, width), np.uint8)
        cv2.rectangle(
            watermark_mask, (int(x * width), int(y * height)),
            (int((x + w) * width), int((y + h) * height)), 255, -1,
        )

    def rgb_to_bgr(value: str) -> np.ndarray:
        value = value.lstrip("#")
        return np.array([int(value[4:6], 16), int(value[2:4], 16), int(value[0:2], 16)], np.float32)

    top = rgb_to_bgr(args.fill_top)
    bottom = rgb_to_bgr(args.fill_bottom)
    outline = tuple(int(x) for x in rgb_to_bgr(args.outline_color))
    gradient = np.empty((height, width, 3), np.uint8)
    for y in range(height):
        ratio = y / max(1, height - 1)
        gradient[y, :, :] = (top * (1 - ratio) + bottom * ratio).astype(np.uint8)

    dilate_kernel = np.ones((args.coarse_dilate, args.coarse_dilate), np.uint8)
    morph_kernel = np.ones((args.morph, args.morph), np.uint8)
    frames_rendered = 0
    try:
        while True:
            frames = []
            limit = args.redetect_interval if actual_mode == "hybrid" else 1
            for _ in range(limit):
                ok, frame = cap.read()
                if not ok:
                    break
                frames.append(frame)
            if not frames:
                break
            if actual_mode == "hybrid":
                masks_by_frame = masks_hybrid(
                    predictor, detector, frames, frame_dir, args, device, width, height, morph_kernel,
                )
                for index, frame in enumerate(frames):
                    writer.write(render_frame(frame, masks_by_frame.get(index, []), gradient, outline, args.outline, watermark_mask))
                    frames_rendered += 1
            else:
                masks = masks_per_frame(
                    detector, sam, frames[0], args, device, width, height, dilate_kernel, morph_kernel,
                )
                writer.write(render_frame(frames[0], masks, gradient, outline, args.outline, watermark_mask))
                frames_rendered += 1
            print(f"rendered {frames_rendered}", end="\r", flush=True)
    finally:
        cap.release()
        writer.release()
        shutil.rmtree(frame_dir, ignore_errors=True)

    if frames_rendered == 0:
        raise SystemExit("no frames rendered")

    command = ["ffmpeg", "-y", "-i", str(work)]
    if args.keep_audio:
        command += ["-i", str(video), "-map", "0:v:0", "-map", "1:a?", "-c:a", "copy"]
    else:
        command += ["-map", "0:v:0", "-an"]
    command += [
        "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ]
    run(command)
    work.unlink(missing_ok=True)

    metadata = {
        "input_video": str(video), "output_video": str(output),
        "pipeline": (
            "YOLO11s-seg periodic detection + SAM 2.1 VOS propagation + mask cleanup"
            if actual_mode == "hybrid"
            else "YOLO11s-seg per-frame detection + SAM 2.1 per-frame refinement + mask intersection"
        ),
        "mode_requested": args.mode, "mode_used": actual_mode,
        "device": str(device), "audio_preserved": bool(args.keep_audio),
        "parameters": vars(args), "before": probe(video), "after": probe(output),
        "review_note": "Compliance-oriented preprocessing only; platform approval is not guaranteed.",
    }
    (out_dir / "jimeng_person_mask_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n{output}")


if __name__ == "__main__":
    main()
