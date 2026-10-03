#!/bin/bash
# 云端环境准备（幂等）：SessionStart hook 每次新会话自动运行，也可复制到环境的 Setup script。
# 中文字体（缺了中文渲染成方框）
if ! fc-list 2>/dev/null | grep -q "Noto Sans CJK SC"; then
  apt-get update -qq && apt-get install -y -qq fonts-noto-cjk > /dev/null
fi
# Kokoro 备选配音的依赖
python3 -c "import kokoro_onnx, soundfile" 2>/dev/null || pip install -q kokoro-onnx soundfile 2>/dev/null || true
# 预热 npx 缓存，免得每次会话重新下载
npx -y hyperframes@0.8.114 --version > /dev/null
npx -y @marswave/listenhub-cli@0.0.22 --version > /dev/null
echo "cloud-setup: ok"
