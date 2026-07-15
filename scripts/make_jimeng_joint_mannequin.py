import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO


LIMBS = (
    (5, 7, "arm"), (7, 9, "arm"), (6, 8, "arm"), (8, 10, "arm"),
    (11, 13, "leg"), (13, 15, "leg"), (12, 14, "leg"), (14, 16, "leg"),
)
JOINTS = (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)


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


def bgr(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) != 6:
        raise argparse.ArgumentTypeError("colors must use #RRGGBB")
    return int(value[4:6], 16), int(value[2:4], 16), int(value[0:2], 16)


class JointSmoother:
    def __init__(self, alpha: float, threshold: float, hold_frames: int, track_hold: int):
        self.alpha = alpha
        self.threshold = threshold
        self.hold_frames = hold_frames
        self.track_hold = track_hold
        self.tracks: dict[int, dict[str, object]] = {}

    def update(self, track_id: int, points: np.ndarray, scores: np.ndarray, box: np.ndarray, frame_index: int):
        state = self.tracks.get(track_id)
        if state is None:
            ages = np.where(scores >= self.threshold, 0, self.hold_frames + 1).astype(np.int32)
            state = {
                "points": points.copy(), "scores": scores.copy(), "ages": ages,
                "box": box.copy(), "last_seen": frame_index,
            }
            self.tracks[track_id] = state
            return state

        old_points = state["points"]
        old_scores = state["scores"]
        ages = state["ages"]
        for index, score in enumerate(scores):
            if score >= self.threshold:
                if ages[index] <= self.hold_frames:
                    old_points[index] = old_points[index] * (1 - self.alpha) + points[index] * self.alpha
                else:
                    old_points[index] = points[index]
                old_scores[index] = score
                ages[index] = 0
            elif ages[index] < self.hold_frames:
                ages[index] += 1
                old_scores[index] *= 0.85
            else:
                ages[index] += 1
                old_scores[index] = 0
        state["box"] = state["box"] * (1 - self.alpha) + box * self.alpha
        state["last_seen"] = frame_index
        return state

    def active(self, frame_index: int):
        expired = [key for key, state in self.tracks.items() if frame_index - state["last_seen"] > self.track_hold]
        for key in expired:
            del self.tracks[key]
        return list(self.tracks.items())


def visible(scores: np.ndarray, *indices: int) -> bool:
    return all(scores[index] > 0 for index in indices)


def point(points: np.ndarray, index: int) -> tuple[int, int]:
    return tuple(np.round(points[index]).astype(int))


def draw_capsule(canvas, start, end, width, fill, outline):
    cv2.line(canvas, start, end, outline, width + 4, cv2.LINE_AA)
    cv2.line(canvas, start, end, fill, width, cv2.LINE_AA)


def draw_mannequin(canvas: np.ndarray, state: dict[str, object], colors: dict[str, tuple[int, int, int]]):
    points = state["points"]
    scores = state["scores"]
    x1, y1, x2, y2 = state["box"]
    height = max(1.0, y2 - y1)
    arm_width = max(7, int(height * 0.028))
    leg_width = max(9, int(height * 0.040))
    joint_radius = max(4, int(height * 0.012))

    for start, end, kind in LIMBS:
        if visible(scores, start, end):
            draw_capsule(
                canvas, point(points, start), point(points, end),
                arm_width if kind == "arm" else leg_width,
                colors["fill"], colors["outline"],
            )

    if visible(scores, 5, 6, 11, 12):
        torso = np.array([point(points, 5), point(points, 6), point(points, 12), point(points, 11)], np.int32)
        center = torso.mean(axis=0)
        inner = np.round(center + (torso - center) * 0.94).astype(np.int32)
        cv2.fillConvexPoly(canvas, torso, colors["outline"], cv2.LINE_AA)
        cv2.fillConvexPoly(canvas, inner, colors["fill"], cv2.LINE_AA)
    else:
        shoulder_indices = [index for index in (5, 6) if scores[index] > 0]
        hip_indices = [index for index in (11, 12) if scores[index] > 0]
        if shoulder_indices and hip_indices:
            shoulder = tuple(np.round(points[shoulder_indices].mean(axis=0)).astype(int))
            hip = tuple(np.round(points[hip_indices].mean(axis=0)).astype(int))
            draw_capsule(canvas, shoulder, hip, max(arm_width * 2, leg_width), colors["fill"], colors["outline"])

    head_indices = [index for index in range(5) if scores[index] > 0]
    head_center = None
    if head_indices:
        head_center = tuple(np.round(points[head_indices].mean(axis=0)).astype(int))
        head_radius = max(8, int(height * 0.052))
        if visible(scores, 5, 6):
            shoulder = tuple(np.round((points[5] + points[6]) / 2).astype(int))
            neck_end = (head_center[0], head_center[1] + head_radius)
            draw_capsule(canvas, shoulder, neck_end, arm_width, colors["fill"], colors["outline"])
        cv2.circle(canvas, head_center, head_radius + 2, colors["outline"], -1, cv2.LINE_AA)
        cv2.circle(canvas, head_center, head_radius, colors["fill"], -1, cv2.LINE_AA)
        cv2.ellipse(
            canvas, head_center, (max(2, head_radius - 3), max(2, head_radius - 3)),
            0, 205, 335, colors["shade"], 2, cv2.LINE_AA,
        )

    for index in JOINTS:
        if scores[index] <= 0:
            continue
        center = point(points, index)
        cv2.circle(canvas, center, joint_radius + 2, colors["outline"], -1, cv2.LINE_AA)
        cv2.circle(canvas, center, joint_radius, colors["joint"], -1, cv2.LINE_AA)
        cv2.circle(canvas, center, max(1, joint_radius // 3), colors["fill"], -1, cv2.LINE_AA)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--pose-model", default="yolo11n-pose.pt")
    parser.add_argument("--tracker", default="botsort.yaml")
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--conf", type=float, default=0.15)
    parser.add_argument("--iou", type=float, default=0.50)
    parser.add_argument("--keypoint-conf", type=float, default=0.25)
    parser.add_argument("--smooth-alpha", type=float, default=0.65)
    parser.add_argument("--hold-frames", type=int, default=6)
    parser.add_argument("--track-hold", type=int, default=2)
    parser.add_argument("--green", default="#00ff00")
    parser.add_argument("--fill", default="#f4f4f4")
    parser.add_argument("--joint", default="#d8d8d8")
    parser.add_argument("--shade", default="#c4c4c4")
    parser.add_argument("--outline-color", default="#9a9a9a")
    parser.add_argument("--keep-audio", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--crf", type=int, default=18)
    args = parser.parse_args()

    if not 0 < args.smooth_alpha <= 1:
        raise SystemExit("--smooth-alpha must be in (0, 1]")
    if not torch.cuda.is_available() and not args.allow_cpu:
        raise SystemExit("CUDA PyTorch required. Pass --allow-cpu for slow CPU processing.")
    device = 0 if torch.cuda.is_available() else "cpu"
    video = Path(args.video).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / "_joint_mannequin_work.mp4"
    output = out_dir / "jimeng_joint_mannequin.mp4"

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(work), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    model = YOLO(args.pose_model)
    smoother = JointSmoother(args.smooth_alpha, args.keypoint_conf, args.hold_frames, args.track_hold)
    colors = {
        "green": bgr(args.green), "fill": bgr(args.fill), "joint": bgr(args.joint),
        "shade": bgr(args.shade), "outline": bgr(args.outline_color),
    }

    frame_index = 0
    peak_people = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            result = model.track(
                frame, persist=True, tracker=args.tracker, imgsz=args.imgsz,
                conf=args.conf, iou=args.iou, device=device, verbose=False,
            )[0]
            if result.boxes is not None and result.keypoints is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                ids = result.boxes.id.cpu().numpy().astype(int) if result.boxes.id is not None else np.arange(len(boxes))
                points = result.keypoints.xy.cpu().numpy()
                scores = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else np.ones(points.shape[:2])
                for track_id, pose, confidence, box in zip(ids, points, scores, boxes):
                    smoother.update(int(track_id), pose, confidence, box, frame_index)

            active = smoother.active(frame_index)
            peak_people = max(peak_people, len(active))
            canvas = np.full((height, width, 3), colors["green"], np.uint8)
            active.sort(key=lambda item: float(item[1]["box"][3]))
            for _, state in active:
                draw_mannequin(canvas, state, colors)
            writer.write(canvas)
            frame_index += 1
            print(f"rendered {frame_index}", end="\r", flush=True)
    finally:
        cap.release()
        writer.release()

    if frame_index == 0:
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
        "pipeline": "YOLO11 Pose + BoT-SORT + temporal joint smoothing + 2.5D articulated mannequin rendering",
        "keypoint_layout": "COCO 17", "peak_people": peak_people,
        "device": str(device), "audio_preserved": bool(args.keep_audio),
        "parameters": vars(args), "before": probe(video), "after": probe(output),
        "review_note": "Compliance-oriented motion reference only; platform approval is not guaranteed.",
    }
    (out_dir / "jimeng_joint_mannequin_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n{output}")


if __name__ == "__main__":
    main()
