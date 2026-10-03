#!/bin/bash
# 新会话启动时准备视频制作环境：中文字体、HyperFrames / ListenHub CLI 缓存（只在云端会话运行）
set -euo pipefail
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi
cd "$CLAUDE_PROJECT_DIR"
bash tools/cloud-setup.sh
