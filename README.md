# video

用 Claude + HyperFrames 做知识解说视频（代码即视频：HTML + GSAP → 逐帧截图 → MP4）。

## 项目

- `hello-explainer/`：10 秒最小闭环样例，用来验证环境能跑通，不涉及真实选题。

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
- 实测速度：10 秒 1080p30 渲染约 15 秒（4 核）。
