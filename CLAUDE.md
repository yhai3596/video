# 视频制作仓库 · 新会话启动说明

用 Claude 写代码出知识解说视频：HTML + GSAP（HyperFrames）→ 逐帧渲染 → MP4，配音用 ListenHub 克隆音色。
用户是 Alan，做制造业 AI 落地咨询；默认观众是工厂老板，默认竖屏 9:16。

**和 `ai-video-production` skill 冲突时以本文件为准**。skill 里有两条已过时：
1. 「云端连不上 ListenHub，只能在 Mac 上配音」——现在云端可以直接调用（见下文「环境」）
2. skill 没写语速——默认 1.1 倍，用 atempo 后处理，不用 ListenHub 的 speed 参数

## 环境（开工先确认）

- **SessionStart hook** 会自动运行 `tools/cloud-setup.sh`：装中文字体 `fonts-noto-cjk`，预热 HyperFrames / ListenHub CLI 缓存。
  如果中文渲染成方框，手动跑一次 `bash tools/cloud-setup.sh`。
- **Default 环境需要的配置**（用户已配好；不通时提醒用户检查，不要让用户把 Key 贴进聊天）：
  - API credentials：`api.marswave.ai`，Bearer，代理注入 Key，会话里读不到
  - Network access：Custom + 默认包管理器列表 + `assets.marswaveai.cn`（ListenHub 生成的音乐下载地址）
- **会被网络策略拦的**：huggingface.co（Whisper 用不了）、mckinsey.com / gov.cn / weforum.org 等官网（WebFetch 读不了）
- **验证 ListenHub 通不通**（不扣积分）：
  `NODE_USE_ENV_PROXY=1 LISTENHUB_API_KEY=x npx -y @marswave/listenhub-cli@0.0.22 openapi speakers list --language zh --json`，能看到 Alan 就通

## 制作流程（按顺序，前三步不过不动手）

1. **故事主线 + 一句话结论**：用户给的结论有问题（喊口号、和数据冲突、口径不对）就先指出并给改写建议，用户拍板后再往下
2. **分镜表**：`bash tools/new-project.sh <目录名>` 建项目，填 `storyboard.md`（段 / 句 / 时长 / 解说词 / 画面 / 来源），
   **用户确认解说词后才配音**，改词要重配
3. **事实核查**：每个数字都要有来源、口径、可信度，写进 `storyboard.md` 的核查表
4. **配音**：写 `narration.json`，`python3 tools/narrate.py <项目>`
5. **画面**：写 `index.html.tpl`，动画时间点一律用 `T.Lxx.start` / `T.Lxx.marks[i]`，不写死秒数；`python3 tools/narrate.py <项目>` 重新生成 `index.html`
6. **检查 + 渲染**：`cd <项目> && ../tools/hf check && ../tools/hf render --output out/vo.mp4`
7. **质检**（见下文），有问题回到第 5 步
8. **混音交付**：`python3 ../tools/finalize.py out/vo.mp4 final/<名称>.mp4 --bgm audio/bgm/bgm.mp3`，
   字幕 `subtitles.srt` 复制到 `final/`；用 SendUserFile 发给用户；commit + push

## 各环节规则和已踩过的坑

**事实核查**
- 官网 WebFetch 被拦：用 WebSearch 加 `allowed_domains` 限定到官网取原文摘要，再找第二个独立来源交叉核对
- 先查有没有更新版本（例：麦肯锡 State of AI 已有 2026 年 8 月版，2025 版数字过时）
- 区分口径：全球 vs 中国、受访者 vs 企业、「智能化改造整体成效」≠「AI 成效」、政策原文的统计对象
- 有争议的数字（如 MIT NANDA「95% 试点无回报」：初步报告、未同行评审）不用，懂行的观众会拿来挑刺

**配音**（`tools/narrate.py`）
- `tts` 字段写读法，数字写成汉字（百分之六、二零二七年）；`sub` 字段写字幕，用阿拉伯数字
- `marks` 写解说词里的关键词，脚本按字符位置估算它被念到的时刻，画面在那个时刻动作
- 语速默认 1.1（`speed` 可覆盖）：按正常语速生成，再用 atempo 精确变速。
  不用 ListenHub 的 speed 参数：实测 speed=1.1 只是提示，10 句整体只快 4.9%，单句 0.91–1.28 倍不等
- `audio/raw/manifest.json` 记录每句的引擎、音色、文本指纹，改了哪句只重配哪句；改语速不重配、不扣积分
- 配音直接 curl 调 `POST https://api.marswave.ai/openapi/v1/tts`，不走 CLI（CLI 0.0.22 的 `--speed` 有浮点校验 bug）
- 句内字幕切换点自动对齐到 0.5 秒内检测到的真实停顿
- 克隆音色 ID：`voice-clone-69539213672c8112766c3f4a`（Alan，男声，中文）

**画面**（竖屏 1080×1920）
- 安全区：顶部 200px、底部 400px 留给平台 UI 和字幕；主体内容放在 y 290–1330，来源脚注在 y=1360，字幕 `padding-bottom: 360px`
- 内容组 `.grp` 在这个区间内垂直居中；内容比区间高时，必须保留 `.grp > * { flex-shrink: 0; }`，否则元素会被压扁重叠
- 每个数字下方用小字标来源和口径
- GSAP 用本地 `assets/gsap.min.js`（渲染用的 Chromium 不走代理，CDN 会失败）；只用 opacity / x / y / scale 等属性，确定性逻辑
- 风格：深色工程蓝图；冷色 = 稳定 / 已验证，暖色 = 警示 / 差距
- 不用世界地图（国内发布有「问题地图」风险），用按地区的柱状图或点阵

**渲染**
- 用 `tools/hf`（自动找预装浏览器），必须在前台跑；约 70 秒竖屏渲染 1.5–2 分钟
- `hf check` 只查文字重叠，**查不出图形压住文字**（例：点阵压到脚注），所以必须看抽帧

**质检**（交付前必做）
- 抽帧拼联系表：每句结束前 0.3 秒一帧 + 每句中段一帧，逐张看是否出界、遮挡、状态与解说一致
- 字幕：narrate.py 已自动对齐停顿；可用 silencedetect 复核偏差
- 响度：成片约 -16 LUFS，峰值 ≤ -1.5 dBFS
- Claude 听不了音频：交付时按时间点列出最容易读错的词（AI、数字密集句、专有名词）请用户听

**背景音乐**
- 生成：`NODE_USE_ENV_PROXY=1 LISTENHUB_API_KEY=x npx -y @marswave/listenhub-cli@0.0.22 openapi music instrumental --prompt "..." --json`
  （每次 10 积分；返回 `tracks[0].audioUrl`，用 curl 下载到 `audio/bgm/bgm.mp3`）
- 提示词要点：克制、无人声、无强旋律、动态平稳，让人声清楚
- 先看音乐每 5 秒的响度起伏，挑和片子节奏对得上的起点（`--bgm-start`）
- `finalize.py --bgm`：音乐统一到 -28 LUFS，人声侧链轻度避让（实测比人声低约 17–19 LU）

## 命令速查

```bash
bash tools/new-project.sh <目录名> [portrait|landscape]   # 新建项目骨架
python3 tools/narrate.py <项目>                              # 配音 + 时间轴 + 字幕 + index.html
python3 tools/narrate.py <项目> --force L03                  # 强制重配某句
cd <项目> && ../tools/hf check                               # 检查
../tools/hf render --output out/vo.mp4                       # 渲染（前台）
python3 ../tools/finalize.py out/vo.mp4 final/x.mp4 --bgm audio/bgm/bgm.mp3   # 混音 + 响度
```

## 成本

- 消耗 ≈ 调用次数 × 上下文长度：**每条视频开一个新会话**，不要在长会话里接着做
- 返工渲染最费：分镜阶段把每段画面的版面写具体，渲染前先 `hf check`，一次渲染后集中改完再渲染
- 改语速、改画面、重新混音都不扣 ListenHub 积分；改解说词、换音色、重新生成音乐才扣

## 参考项目

- `mfg-ai/`：制造业 AI 落地（竖屏 65 秒），完整示例：分镜与核查表、配音配置、画面模板、成片
- `hello-explainer/`：最早的横屏样例
