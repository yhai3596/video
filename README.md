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
python3 tools/narrate.py hello-explainer            # 已有的 audio/raw/Lxx 会跳过；改了某句就加 --force L02
cd hello-explainer && npx -y hyperframes@0.8.114 check
npx -y hyperframes@0.8.114 render --output out/vo.mp4
python3 ../tools/finalize.py out/vo.mp4 out/final.mp4
```

配音来源：`audio/raw/<id>.mp3|.wav` 已存在就直接用，所以在 Mac 上用 ListenHub 逐句生成后放进来即可；
没有的话用 HyperFrames 内置 Kokoro（中文只有一个女声 `zf_xiaobei`，语速约每秒 3.9 字，比常见知识类视频慢）。

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
