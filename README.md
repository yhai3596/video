# video

用 Claude + HyperFrames 做知识解说视频（代码即视频：HTML + GSAP → 逐帧截图 → MP4）。

**新会话从 `CLAUDE.md` 开始**；给其他 agent 复用这套方法用 `docs/video-agent-prompt.md`。完整流程、环境要求、踩过的坑、命令速查都在那里，Claude Code 打开仓库会自动读取。

## 项目

- `mfg-ai/`：制造业 AI 落地，竖屏 9:16、65 秒、ListenHub 克隆音色 1.1 倍速。分镜与事实核查见 `mfg-ai/storyboard.md`，成片在 `mfg-ai/final/`（带背景音乐；另有无配乐版本）。
- `hello-explainer/`：26 秒带 ListenHub 克隆音色配音和字幕的最小闭环样例，用来验证环境，不涉及真实选题。
- `tools/narrate.py`：逐句配音 → 去首尾静音 → 量真实时长 → 生成字幕、`.srt` 和 `index.html`（由 `index.html.tpl` 套模板）。句内字幕切换点自动对齐到 0.5 秒内检测到的真实停顿。
- `tools/finalize.py`：成片两遍 loudnorm 到 -16 LUFS；`--bgm 音乐文件` 混入背景音乐（统一到 -28 LUFS、首尾淡入淡出、人声侧链轻度避让）。
  ListenHub 生成的音乐下载地址在 `assets.marswaveai.cn`，环境网络要放行这个域名。
- `tools/hf`：HyperFrames 包装，自动找到云端预装的 headless shell，不需要设 `HYPERFRAMES_BROWSER_PATH`。
- `tools/cloud-setup.sh`：云端环境准备（装中文字体、预热 npx 缓存），由 `.claude/hooks/session-start.sh` 在每个新会话自动运行。
- `tools/new-project.sh`：新建视频项目骨架（以 `mfg-ai` 的竖屏模板为起点）。

## 制作流程

```bash
# 1. 改解说词：<项目>/narration.json（tts 用读法写数字，sub 用阿拉伯数字；marks 是要对齐画面动作的关键词）
# 2. 改画面：<项目>/index.html.tpl（用 T.L02.start / T.L02.marks[i] 安排动画，不写死秒数）
python3 tools/narrate.py hello-explainer            # 只重配文本/音色变了的句子；--force L02 强制重配
cd hello-explainer && ../tools/hf check
../tools/hf render --output out/vo.mp4
python3 ../tools/finalize.py out/vo.mp4 out/final.mp4
```

## 配音（ListenHub 为主）

`narration.json` 里设 `"engine": "listenhub"`，`"voice"` 填 speakerId（克隆音色 `voice-clone-69539213672c8112766c3f4a`）。

**云端直接生成**（推荐，配一次以后都不用碰 Mac）：
环境设置的 **API credentials** 里加一条：Allowed websites `api.marswave.ai`，Header `Authorization` / Prefix `Bearer` / Value 填 Key。
真实 Key 由平台代理在请求离开容器后加上，会话里看不到；narrate.py 在没有 `LISTENHUB_API_KEY` 时给 CLI 填占位值。
已验证可用（2026-10-03）。narrate.py 用 curl 直接调 `POST https://api.marswave.ai/openapi/v1/tts`，不走 listenhub CLI：
CLI 0.0.22 的 `--speed` 校验有浮点 bug（1.1 会被误拒），且它用 Node 内置 fetch，需要 `NODE_USE_ENV_PROXY=1` 才走代理。
手动调 CLI 的其他命令（如 `openapi music instrumental`）时记得加这个变量。

**语速**：默认 1.1 倍（`narration.json` 的 `speed` 可覆盖）。配音按正常语速生成，再用 ffmpeg `atempo` 精确变速（不变调）。
不用 ListenHub 的 speed 参数：实测 speed=1.1 只是生成提示，10 句整体只快 4.9%，单句 0.91–1.28 倍不等。
语速不进 manifest 指纹，改语速不会重新生成配音、不扣积分。
没有 API credentials 的套餐改为在环境变量里设 `LISTENHUB_API_KEY`。

**Mac 兜底**：`python3 tools/narrate.py <项目> --mac-script` 生成 `audio/listenhub_tts.command`，
在 Mac 上双击逐句生成 mp3 到 `audio/raw/`，传回仓库后重新运行 narrate.py。

`audio/raw/manifest.json` 记录脚本生成的每句用了什么引擎、音色、语速和文本，改了任一项会自动只重配那一句；
手动放进 `audio/raw/` 的文件优先使用、不会被删除（但改了文本不会自动重配，脚本会提示）。

备选引擎 `kokoro`：HyperFrames 内置本地模型，不需要网络和 Key，中文只有一个女声 `zf_xiaobei`，约每秒 3.9 字。

## 云端环境要点（已验证）

- 环境的 Setup script 用 `tools/cloud-setup.sh` 的内容（中文字体 `fonts-noto-cjk`，不装的话中文会渲染成方框）。
  没配 Setup script 的环境，先手动跑一次 `bash tools/cloud-setup.sh`。
- 检查和渲染用 `tools/hf`（自动找预装浏览器），渲染必须在前台跑。
- GSAP 已放在 `assets/gsap.min.js`，不走 CDN（渲染用的 Chromium 不走代理）。
- 实测速度：26 秒 1080p30 带音频渲染约 28 秒（4 核）。
- 云端连不上 huggingface.co（网络策略），Whisper 模型下载不了，暂时没法做语音转写回检。
