# Seedance 参考视频商品替换 Skill

[English](README.md) | [简体中文](README.zh-CN.md)

这是一个面向 Codex 的 Skill 和 Python 工具集，可把本地视频、抖音分享链接或分镜图整理成结构化、带确认门槛的 Seedance 参考素材包。它覆盖分镜提取、对白转写与校对、商品替换规划、提示词生成、视频增强、成片超分以及审核友好的动作参考转换。

本项目负责分析素材、生成参考图和提示词，不会直接调用 Seedance，也不会自行生成最终创意视频。

## 主要能力

- 解析本地视频或抖音分享链接，得到本地参考视频。
- 检测时长、分辨率、帧率、宽高比和音频流。
- 最多抽取 24 张代表帧并生成 `storyboard_grid.jpg`。
- 保留原始 ASR，校对转写，生成 SRT 字幕和带时间戳的对白时间线。
- 分析待替换商品，生成逐镜头的商品替换方案。
- 用户确认分镜、替换目标、对白处理、时长、比例和音频模式后，才生成并校验 Seedance 提示词。
- 使用 Real-ESRGAN 或 FFmpeg 兜底增强低质量参考视频，获得更清晰的分镜。
- 使用 `realesr-animevideov3` 对已生成的 AI 成片进行超分。
- 生成平面动画、人物独立遮罩或 2.5D 关节白模动作参考。

## 标准工作流

1. 解析参考素材来源。
2. 分析视频并提取分镜。
3. 必要时先增强参考视频，再重新提取清晰分镜。
4. 转写和校对对白，不补写无法确认的内容。
5. 要求用户确认分镜图、对白、替换目标、时长、宽高比和音频模式。
6. 分析商品并生成 `replacement_plan.md`。
7. 用户确认替换方案后，生成并校验 `seedance_prompt.md`。
8. 把 `storyboard_grid.jpg` 上传到 Seedance，再粘贴生成的提示词。

原视频和增强视频仅用于分析、抽帧和推断时间线。除非用户明确要求视频转视频，否则最终视觉参考始终是分镜图。

## 环境要求

| 组件 | 用途 | 说明 |
| --- | --- | --- |
| Python 3.10+ | 全部脚本 | 推荐 Python 3.11 或 3.12。 |
| FFmpeg、FFprobe | 视频分析、抽帧和编码 | 两个命令都必须在 `PATH` 中。 |
| `requests` | 下载抖音视频 | 由 `requirements.txt` 安装。 |
| `social-media-parser` Skill | 解析抖音分享链接 | 本地视频不需要。 |
| faster-whisper | 本地语音识别 | 可选，由 `requirements-ai.txt` 安装。 |
| Real-ESRGAN NCNN Vulkan | AI 增强和超分 | 参考增强可选，成片超分必需。 |
| OpenCV、NumPy | 审核友好转换 | 由 `requirements-ai.txt` 安装。 |
| PyTorch、Ultralytics | 人物遮罩和关节白模 | PyTorch 需按本机 CUDA 环境单独安装。 |
| Meta SAM 2 | 人物遮罩混合传播 | 可选；缺失时可逐帧回退。 |

## 安装

### 1. 安装到 Codex Skills 目录

```powershell
pwsh -NoProfile -Command "git clone https://github.com/asen5269/video-dashi-skills.git `$HOME/.codex/skills/seedance-reference-product-replacer"
```

安装后重启 Codex，让它重新发现 `SKILL.md`。

### 2. 安装 Python 依赖

基础解析依赖：

```powershell
pwsh -NoProfile -Command "python -m pip install -r `$HOME/.codex/skills/seedance-reference-product-replacer/requirements.txt"
```

可选语音识别和计算机视觉依赖：

```powershell
pwsh -NoProfile -Command "python -m pip install -r `$HOME/.codex/skills/seedance-reference-product-replacer/requirements-ai.txt"
```

PyTorch 请根据 CPU/CUDA 环境从官方软件源单独安装。需要 SAM 2 视频目标传播时，再单独安装 Meta SAM 2。

### 3. 安装 FFmpeg

验证：

```powershell
pwsh -NoProfile -Command "ffmpeg -version; ffprobe -version"
```

### 4. 可选安装 Real-ESRGAN

把 `realesrgan-ncnn-vulkan` 加入 `PATH`，或解压到以下目录任意子目录：

```text
seedance-reference-product-replacer/vendor/
```

脚本会递归搜索 `PATH` 和 `vendor/`。第三方二进制与模型权重不会提交到本仓库，其授权以各自上游协议为准。

### 5. 可选安装抖音解析 Skill

将 `social-media-parser` 安装到以下任一位置：

```text
~/.codex/skills/social-media-parser/
~/.codex/skills/social-media-parser/social-media-parser/
```

也可通过 `--parser-root` 指定自定义目录。

## 快速开始

解析本地视频：

```powershell
pwsh -NoProfile -Command "`$skill=`$HOME+'/.codex/skills/seedance-reference-product-replacer'; `$work='work/seedance-run'; python `$skill/scripts/resolve_reference_video.py --input 'C:/videos/reference.mp4' --out-dir `$work/source"
```

读取 `work/seedance-run/source/reference_input.json` 后，分析视频：

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/analyze_video.py --video 'C:/videos/reference.mp4' --out 'work/seedance-run/video_analysis.json'"
```

提取分镜：

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/extract_storyboard.py --video 'C:/videos/reference.mp4' --out-dir 'work/seedance-run' --max-frames 24"
```

输出包括 `frames/` 和 `storyboard_grid.jpg`。

## 常用命令

### 检查参考视频质量

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/check_video_quality.py --video 'C:/videos/reference.mp4' --out 'work/seedance-run/video_quality.json'"
```

### 增强参考视频以获得清晰分镜

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/enhance_video.py --video 'C:/videos/reference.mp4' --out-dir 'work/seedance-run/enhanced' --backend auto --profile compressed --scale 2"
```

`auto` 会优先使用 Real-ESRGAN，找不到时回退到 FFmpeg。增强结果仅用于提取清晰分镜，不作为 Seedance 最终视频参考。

### 转写并校对对白

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/transcribe_audio.py --video 'C:/videos/reference.mp4' --out 'work/seedance-run/raw_transcript.txt' --srt-out 'work/seedance-run/raw_subtitles.srt'"
```

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/clean_transcript.py --input 'work/seedance-run/raw_transcript.txt' --clean-out 'work/seedance-run/clean_transcript.md' --timeline-out 'work/seedance-run/dialogue_timeline.md' --srt-out 'work/seedance-run/subtitles.srt'"
```

Agent 还必须人工检查校对稿。无法确认的内容标记为 `[unclear]`，用户确认前不得生成最终提示词。

### 生成并校验提示词包

通过确认门槛后，创建 `prompt_values.json` 并运行：

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/build_prompt_pack.py --input 'work/seedance-run/prompt_values.json' --out-dir 'work/seedance-run'"
```

单独校验提示词：

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/lint_seedance_prompt.py --prompt 'work/seedance-run/seedance_prompt.md' --speech unknown"
```

### 对最终视频进行超分

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/upscale_video.py --video 'C:/videos/final.mp4' --out-dir 'work/seedance-run/upscaled' --scale 2 --target-height 1080 --model realesr-animevideov3 --tile 0"
```

成片超分必须使用 Real-ESRGAN，此阶段不会用 FFmpeg 插值代替 AI 超分。

### 审核友好平面动画

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/make_jimeng_review_friendly.py --video 'C:/videos/reference.mp4' --out-dir 'work/jimeng-review'"
```

### 人物独立遮罩

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/make_jimeng_person_mask.py --video 'C:/videos/reference.mp4' --out-dir 'work/jimeng-person-mask'"
```

默认要求 CUDA。`--allow-cpu` 可启用 CPU，但速度很慢。混合模式使用 SAM 2；SAM 2 VOS 不可用时自动回退到逐帧 YOLO/SAM 精修。

### 2.5D 关节白模

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/seedance-reference-product-replacer/scripts/make_jimeng_joint_mannequin.py --video 'C:/videos/reference.mp4' --out-dir 'work/jimeng-joint-mannequin'"
```

该模式是带跟踪的 2.5D 姿态表达，不是恢复出的 3D 人体网格。

## 输出约定

根据启用的工作流，Skill 会生成：

```text
source/reference_input.json
source/reference_video.mp4
video_analysis.json
video_quality.json
frames/
storyboard_grid.jpg
enhanced/enhanced_reference.mp4
enhanced/enhancement_metadata.json
raw_transcript.txt
clean_transcript.md
dialogue_timeline.md
subtitles.srt
shot_analysis.md
product_analysis.md
replacement_plan.md
seedance_prompt.md
upscaled/upscaled_video.mp4
upscaled/upscale_metadata.json
```

## 内容与安全规则

- 只替换用户明确确认的商品或对象。
- 除非用户明确要求，否则保留人物、手部、姿势、背景、光照、镜头、剪辑节奏和 CTA。
- 不得编造对白、商品功效、姓名、金额或时间戳。
- 审核参考模式默认移除音频；只有确认音频已授权时才保留。
- 只有确认内容允许修改并测量出准确区域后，才能移除水印或覆盖层。
- “审核友好”不代表保证过审，也不能用于掩盖本身违规的内容。

## 项目结构

```text
SKILL.md                 Codex 行为和工作流契约
scripts/                 可执行 Python 工具
templates/               替换方案和提示词模板
fixtures/                测试元数据
tests/                   Pytest 测试集
requirements.txt         基础 Python 依赖
requirements-ai.txt      可选 ASR/CV 依赖
```

## 测试

```powershell
pwsh -NoProfile -Command "python -m pytest tests -q"
```

部分测试或处理模式需要 FFmpeg、GPU 依赖、模型权重或第三方可执行程序。

## 常见问题

- 找不到 `ffmpeg` 或 `ffprobe`：安装 FFmpeg，并把 `bin` 目录加入 `PATH`。
- 找不到 `social-media-parser`：把解析 Skill 安装到默认 Codex 目录，或传入 `--parser-root`。
- 找不到 `realesrgan-ncnn-vulkan`：将程序加入 `PATH`，或解压到本 Skill 的 `vendor/` 下。
- CUDA 报错：安装与 NVIDIA 驱动/CUDA 环境匹配的 PyTorch；支持的脚本也可加 `--allow-cpu`。
- SAM 2 不可用：人物遮罩混合模式会输出提示，并自动使用逐帧精修。
- 人体遮罩合并或缺少肢体：严重遮挡和运动模糊需要手工关键帧修正或专业转描。

## 协议

本项目原创源码和文档使用 [MIT License](LICENSE)。FFmpeg、Real-ESRGAN、模型权重、PyTorch、Ultralytics、SAM 2 等第三方组件适用各自的上游协议。

