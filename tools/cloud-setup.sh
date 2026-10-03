#!/bin/bash
# 云端环境的 Setup script（复制到环境设置里）。新会话启动时运行一次，结果会被缓存。
# 中文字体（缺了中文渲染成方框）
apt-get update -qq && apt-get install -y -qq fonts-noto-cjk > /dev/null
# Kokoro 备选配音的依赖
pip install -q kokoro-onnx soundfile
# 预热 npx 缓存，免得每次会话重新下载
npx -y hyperframes@0.8.114 --version
npx -y @marswave/listenhub-cli@0.0.22 --version
exit 0
