# Video Dashi Skills（视频大师 Skills）

[![CI](https://github.com/asen5269/video-dashi-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/asen5269/video-dashi-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | [简体中文](README.zh-CN.md)

一个面向实际生产流程的 Codex Skill：把本地视频、抖音分享链接或已有分镜图，转换成经过用户确认的 Seedance 参考素材包。

项目把 Agent 工作流与确定性的 Python 工具结合起来，覆盖视频检测、分镜提取、精确对白处理、商品替换规划、提示词生成、参考视频增强、最终成片超分以及审核友好的动作参考转换。

## 这是什么

- 可直接安装的 Codex Skill，包含规范的 `SKILL.md` 元数据。
- 支持本地视频和抖音分享链接，并统一解析为可分析的本地参考视频。
- 带确认门槛的工作流：用户确认视觉参考和修改目标后，才生成最终提示词。
- 可复查的产物管线：每个阶段都写入明确文件，不把关键状态藏在对话里。

## 这不是什么

- 不会直接调用 Seedance，也不会生成最终创意视频。
- 不保证 Seedance、即梦或其他平台审核通过。
- 不绕过登录、付费墙、DRM、私密内容或平台审核。
- 除非用户明确要求视频转视频，否则不会把原视频当作 Seedance 主视觉参考。

## 功能范围

| 功能 | 输入 | 主要输出 |
| --- | --- | --- |
| 素材解析 | 本地视频或抖音分享文本/链接 | `source/reference_input.json`、本地参考视频 |
| 视频分析 | 本地视频 | `video_analysis.json` |
| 分镜提取 | 原视频或增强视频 | `frames/`、`storyboard_grid.jpg` |
| 语音转写 | 带对白的视频 | 原始转写和原始 SRT |
| 转写校对 | 原始 ASR | 校对稿、对白时间线、字幕 |
| 商品替换规划 | 分镜图和商品图 | `product_analysis.md`、`replacement_plan.md` |
| Seedance 提示词 | 已确认方案 | `seedance_prompt.md` 和校验结果 |
| 参考视频增强 | 低质量参考视频 | 用于清晰抽帧的增强视频 |
| 最终成片超分 | 已完成的生成视频 | 超分视频和元数据 |
| 平面审核参考 | 视频 | 非写实动作参考视频 |
| 人物遮罩 | 视频 | 带跟踪的人物遮罩视频 |
| 2.5D 白模 | 视频 | 关节白模绿幕视频 |

## 工作原理

```text
用户素材
   │
   ├─ 本地路径 ───────────────────────┐
   └─ 抖音分享文本 → 链接解析与视频下载
                                      │
                                  本地视频
                                      │
                       视频分析 + 分镜 + 语音识别
                                      │
                                 用户确认
                                      │
                         替换方案 + Seedance 提示词
                                      │
                           校验后的完整素材包
```

Agent 负责判断、交互和确认门槛；Python 脚本负责可重复的视频检测、解析、渲染、格式化和校验。

## 仓库结构

```text
video-dashi-skills/
├── SKILL.md                         Agent 工作流和触发元数据
├── agents/openai.yaml              Codex 界面元数据
├── references/                     按需加载的高级模式说明
│   ├── prompt-workflow.md
│   ├── video-enhancement.md
│   └── jimeng-reference-modes.md
├── scripts/                         确定性 Python 工具
├── templates/                       提示词和替换方案模板
├── fixtures/                        测试元数据
├── tests/                           单元测试
├── requirements.txt                 基础解析依赖
├── requirements-ai.txt              可选 ASR/CV 依赖
├── requirements-dev.txt             测试和代码检查依赖
├── pyproject.toml                    Pytest 和 Ruff 配置
└── .github/workflows/ci.yml          Linux/Windows 自动验证
```

`SKILL.md` 只保留核心流程。高级能力放在 `references/` 中，让 Codex 只加载当前任务需要的说明。

## 环境要求

### 基础环境

- 支持本地 Skill 发现的 Codex
- Python 3.10 或更高版本，推荐 3.11 或 3.12
- `PATH` 中可用的 FFmpeg 和 FFprobe
- 用户有权处理的公开素材

### 可选组件

| 组件 | 用途 |
| --- | --- |
| faster-whisper | 本地语音识别 |
| Real-ESRGAN NCNN Vulkan | AI 参考增强和最终成片超分 |
| OpenCV、NumPy | 审核友好渲染 |
| PyTorch、Ultralytics | 人物遮罩和白模模式 |
| Meta SAM 2 | 混合式视频目标遮罩传播 |
| NVIDIA CUDA | 让遮罩和白模模式具备实用速度 |

## 安装

### 安装为 Codex Skill

PowerShell：

```powershell
pwsh -NoProfile -Command "git clone https://github.com/asen5269/video-dashi-skills.git `$HOME/.codex/skills/video-dashi-skills"
```

目录已经存在时更新：

```powershell
pwsh -NoProfile -Command "git -C `$HOME/.codex/skills/video-dashi-skills pull --ff-only"
```

首次安装后重启 Codex，让它重新发现 `SKILL.md` 和 `agents/openai.yaml`。

### 安装基础依赖

```powershell
pwsh -NoProfile -Command "python -m pip install -r `$HOME/.codex/skills/video-dashi-skills/requirements.txt"
```

基础依赖包括用于链接解析和视频下载的 `requests`、`certifi` 和 `yt-dlp`。

### 安装可选 AI 依赖

```powershell
pwsh -NoProfile -Command "python -m pip install -r `$HOME/.codex/skills/video-dashi-skills/requirements-ai.txt"
```

PyTorch 请根据本机 CPU/CUDA 环境从对应软件源单独安装。只有需要混合人物遮罩传播时，才需要额外安装 Meta SAM 2。

### 安装 FFmpeg

验证两个命令：

```powershell
pwsh -NoProfile -Command "ffmpeg -version; ffprobe -version"
```

### 可选安装 Real-ESRGAN

把 `realesrgan-ncnn-vulkan` 加入 `PATH`，或解压到：

```text
video-dashi-skills/vendor/
```

脚本会递归搜索 `PATH` 和 `vendor/`。第三方程序、模型权重、示例视频和压缩包不会提交进 Git。

## 调用 Skill

示例：

```text
使用 $video-dashi-skills 分析这个视频，并生成 Seedance 分镜素材包。
```

```text
使用 $video-dashi-skills 把这个抖音视频里的瓶子换成我上传的商品，保留人物、手部动作、场景、对白和镜头。
```

```text
使用 $video-dashi-skills 把这个已经生成好的 720p AI 视频超分到 1080p。
```

```text
使用 $video-dashi-skills 生成 2.5D 关节白模绿幕动作参考。
```

## 手工快速运行

正常情况下由 Codex 调用这些脚本，也可以手工执行。

解析素材：

```powershell
pwsh -NoProfile -Command "`$skill=`$HOME+'/.codex/skills/video-dashi-skills'; python `$skill/scripts/resolve_reference_video.py --input 'C:/videos/reference.mp4' --out-dir 'work/seedance-run/source'"
```

分析视频：

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/analyze_video.py --video 'C:/videos/reference.mp4' --out 'work/seedance-run/video_analysis.json'"
```

提取分镜：

```powershell
pwsh -NoProfile -Command "python `$HOME/.codex/skills/video-dashi-skills/scripts/extract_storyboard.py --video 'C:/videos/reference.mp4' --out-dir 'work/seedance-run' --max-frames 24"
```

随后 Agent 会检查分镜、处理对白、收集确认，并生成替换方案和提示词。

## 确认门槛

生成最终提示词前，Skill 必须确认：

- `storyboard_grid.jpg` 是主视觉参考
- 分镜读取顺序
- 校对后的精确对白及处理方式
- 替换目标和新商品
- 需要保留的人物、手部、姿态、场景、字幕和 CTA
- 输出时长和宽高比
- 音频模式

该门槛用于防止“格式正确但创意方向错误”的提示词直接进入生产流程。

## 输出素材包

根据启用的工作流：

```text
work/seedance-run/
├── source/
│   ├── reference_input.json
│   └── reference_video.mp4
├── video_analysis.json
├── video_quality.json
├── frames/
├── storyboard_grid.jpg
├── enhanced/
│   ├── enhanced_reference.mp4
│   └── enhancement_metadata.json
├── raw_transcript.txt
├── raw_subtitles.srt
├── clean_transcript.md
├── dialogue_timeline.md
├── subtitles.srt
├── shot_analysis.md
├── product_analysis.md
├── replacement_plan.md
├── prompt_values.json
└── seedance_prompt.md
```

最终成片超分和即梦动作参考模式会写入独立子目录，并生成对应元数据。

## 高级模式

- [转写、商品替换和提示词流程](references/prompt-workflow.md)
- [视频增强和最终成片超分](references/video-enhancement.md)
- [即梦审核友好动作参考模式](references/jimeng-reference-modes.md)

## 开发与验证

安装开发依赖：

```powershell
pwsh -NoProfile -Command "python -m pip install -r requirements-dev.txt"
```

验证 Skill 包结构：

```powershell
pwsh -NoProfile -Command "python scripts/validate_skill.py ."
```

检查代码并运行测试：

```powershell
pwsh -NoProfile -Command "python -m ruff check scripts tests; python -m pytest"
```

CI 会在 Windows 和 Linux 上执行 Skill 结构校验、Python 语法编译、Ruff 和单元测试。

## 常见问题

- 找不到 `ffmpeg` 或 `ffprobe`：把 FFmpeg 的 `bin` 目录加入 `PATH`。
- 抖音解析没有返回视频：确认链接公开且内容是视频而非图文，然后更新 `yt-dlp`。
- 找不到 `realesrgan-ncnn-vulkan`：把程序加入 `PATH` 或放到 `vendor/` 下。
- CUDA 报错：安装与显卡驱动匹配的 PyTorch；支持的模式也可加 `--allow-cpu`。
- SAM 2 不可用：人物遮罩混合模式会自动回退到逐帧精修。
- 遮罩合并或缺少肢体：严重模糊和遮挡需要手工关键帧或专业转描。
- 提示词校验失败：查看 `seedance_prompt.lint.txt`，补齐缺失的确认项或参考图规则后重新校验。

## 内容与安全规则

- 只处理用户有权使用和修改的素材。
- 不编造对白、商品功效、姓名、金额或时间戳。
- 只有确认授权并测量准确区域后，才能移除水印或覆盖层。
- 审核参考模式只有在用户确认音频授权后才保留音频。
- 不把“审核友好”描述成“保证过审”。

## 协议

本项目原创源码和文档使用 [MIT License](LICENSE)。

FFmpeg、Real-ESRGAN、PyTorch、Ultralytics、SAM 2、模型权重及其他第三方组件适用各自的上游协议。
