#!/bin/bash
# 新建视频项目骨架：bash tools/new-project.sh <目录名> [portrait|landscape]
# 复制渲染所需文件；画面模板以 mfg-ai 的竖屏组件库为起点（点阵、对比柱、卡片、横条、时间表、曲线、结论、评论框）
set -euo pipefail
cd "$(dirname "$0")/.."
name="${1:?用法：bash tools/new-project.sh <目录名> [portrait|landscape]}"
ratio="${2:-portrait}"
[ -e "$name" ] && { echo "$name 已存在"; exit 1; }

mkdir -p "$name/assets" "$name/final"
cp mfg-ai/assets/gsap.min.js "$name/assets/"
cp mfg-ai/hyperframes.json "$name/"
sed "s/mfg-ai/$name/" mfg-ai/package.json > "$name/package.json"
printf '{\n  "id": "%s",\n  "name": "%s",\n  "createdAt": "%s"\n}\n' "$name" "$name" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$name/meta.json"

cat > "$name/narration.json" <<'JSON'
{
  "engine": "listenhub",
  "voice": "voice-clone-69539213672c8112766c3f4a",
  "speed": 1.1,
  "lines": [
    {
      "id": "L01",
      "scene": "s1",
      "tts": "配音读法：数字写成汉字，比如百分之六、二零二七年。",
      "sub": "字幕写法：数字用阿拉伯数字，比如6%、2027年。",
      "marks": ["比如"]
    }
  ]
}
JSON

if [ "$ratio" = "portrait" ]; then
  cp mfg-ai/index.html.tpl "$name/index.html.tpl"
  echo "已从 mfg-ai 复制竖屏模板：保留 <style> 和组件写法，替换各 section 内容和 <script> 里的动画。"
else
  sed -e 's/data-resolution="portrait"/data-resolution="landscape"/' \
      -e 's/width=1080, height=1920/width=1920, height=1080/' \
      -e 's/data-width="1080"/data-width="1920"/' -e 's/data-height="1920"/data-height="1080"/' \
      mfg-ai/index.html.tpl > "$name/index.html.tpl"
  echo "已从 mfg-ai 复制模板并改为横屏画布；坐标、安全区、字号都按竖屏写的，需要重排版面。"
fi

cat > "$name/storyboard.md" <<'MD'
# <选题> · 分镜表（待确认）

- **结论**：
- **观众**：
- **规格**：
- **结尾号召**：

## 分镜

| 段 | 句 | 约时长 | 解说词（字幕版） | 画面 | 来源 |
|---|---|---|---|---|---|

## 事实核查

| # | 说法 | 核实结果 | 口径 / 风险 | 可信度 |
|---|---|---|---|---|

## 配音易错词（交付时请听）
MD
echo "已创建 $name/：narration.json、index.html.tpl、storyboard.md 待填写"
