# video

用 Claude + HyperFrames 做知识解说视频（代码即视频：HTML + GSAP → 逐帧截图 → MP4）。

## 项目

- `hello-explainer/`：31 秒带配音字幕的最小闭环样例，用来验证环境，不涉及真实选题。
- `tools/narrate.py`：逐句配音 → 去首尾静音 → 量真实时长 → 生成字幕、`.srt` 和 `index.html`（由 `index.html.tpl` 套模板）。
- `tools/finalize.py`：成片两遍 loudnorm 到 -16 LUFS。

## 制作流程

```bash
# 1. 改解说词：<项目>/narration.json（tts 用读法写数字，sub 用阿拉伯数字；marks 是要对齐画面动作的关键词）
# 2. 改画面：<项目>/index.html.tpl（用 T.L02.start / T.L02.marks[i] 安排动画，不写死秒数）
python3 tools/narrate.py hello-explainer            # 只重配文本/音色变了的句子；--force L02 强制重配
cd hello-explainer && npx -y hyperframes@0.8.114 check
npx -y hyperframes@0.8.114 render --output out/vo.mp4
python3 ../tools/finalize.py out/vo.mp4 out/final.mp4
```

## 配音（ListenHub 为主）

`narration.json` 里设 `"engine": "listenhub"`，`"voice"` 填 speakerId（克隆音色 `voice-clone-69539213672c8112766c3f4a`）。

**云端直接生成**（推荐，配一次以后都不用碰 Mac）：
1. 环境设置 → Network access 选 Custom，Allowed domains 加 `api.marswave.ai`（保留默认包管理器列表）
2. 环境设置里加环境变量 `LISTENHUB_API_KEY`
3. 新开会话后 `python3 tools/narrate.py <项目>` 会逐句调用 ListenHub

**Mac 兜底**：`python3 tools/narrate.py <项目> --mac-script` 生成 `audio/listenhub_tts.command`，
在 Mac 上双击逐句生成 mp3 到 `audio/raw/`，传回仓库后重新运行 narrate.py。

`audio/raw/manifest.json` 记录脚本生成的每句用了什么引擎、音色、语速和文本，改了任一项会自动只重配那一句；
手动放进 `audio/raw/` 的文件优先使用、不会被删除（但改了文本不会自动重配，脚本会提示）。

备选引擎 `kokoro`：HyperFrames 内置本地模型，不需要网络和 Key，中文只有一个女声 `zf_xiaobei`，约每秒 3.9 字。

## 云端环境要点（已验证）

```bash
# 1. 中文字体（不装的话中文会渲染成方框）
apt-get install -y fonts-noto-cjk

# 2. 用预装的 headless shell 渲染，不用 `hyperframes browser ensure` 去下载
export HYPERFRAMES_BROWSER_PATH=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell

# 3. 检查 + 渲染（必须在前台跑）
cd hello-explainer
npx -y hyperframes@0.8.114 check
npx -y hyperframes@0.8.114 render --output out/hello-explainer.mp4
```

- GSAP 已放在 `assets/gsap.min.js`，不走 CDN（渲染用的 Chromium 不走代理）。
- 实测速度：31 秒 1080p30 带音频渲染约 53 秒（4 核）。
- 云端连不上 huggingface.co（网络策略），Whisper 模型下载不了，暂时没法做语音转写回检。
