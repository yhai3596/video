#!/usr/bin/env python3
"""逐句配音 → 真实时长 → 字幕与画面时间轴。

用法：python3 tools/narrate.py <项目目录> [--voice zf_xiaobei] [--force L03]

项目目录需要：
  narration.json  {"voice": "...", "lines": [{"id": "L01", "scene": "s1", "tts": "读法文本", "sub": "字幕文本",
                                              "marks": ["关键词"]}]}  # marks 可选
  index.html.tpl   含占位符：{{TOTAL}}、{{<scene>.start}}、{{<scene>.dur}}、{{<Lxx>.start}}、{{<Lxx>.dur}}、
                  <!-- AUTO:MEDIA -->（替换为每句 <audio> 与字幕 clip）、/* AUTO:TIMING */（替换为 const T = {...}）

音频来源：audio/raw/<id>.mp3|.wav 已存在就直接用（比如在 Mac 上用 ListenHub 生成后上传），
否则用 HyperFrames 内置 Kokoro 生成。改了某句的 tts 文本，用 --force <id> 重新生成那一句。

产物：audio/<id>.wav（去首尾静音、响度 -16 LUFS）、durations.json、timeline.json、subtitles.srt、index.html
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

LEAD_IN = 0.4   # 第一句前留白
GAP = 0.3       # 句间停顿
TAIL = 1.0      # 最后一句后留白
SUB_MAX = 18    # 单条字幕最多字数，超过按标点拆分
HF = ["npx", "-y", "hyperframes@0.8.114"]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.stdout.strip())


def synth(line, raw_dir, voice, speed, force):
    existing = [p for p in (raw_dir / f"{line['id']}.mp3", raw_dir / f"{line['id']}.wav") if p.exists()]
    if existing and not force:
        return existing[0]
    out = raw_dir / f"{line['id']}.wav"
    run(HF + ["tts", line["tts"], "-v", voice, "-s", str(speed), "-o", str(out)])
    return out


def clean(src, dst):
    # 去掉首尾静音（尾部用 areverse 翻转后再去一次），再统一响度和采样率
    af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
          "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,"
          "loudnorm=I=-16:TP=-1.5:LRA=11")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", "48000", "-ac", "1", str(dst)])


def split_sub(text):
    """按标点切成不超过 SUB_MAX 字的若干条，返回 [(文本, 字数权重)]。"""
    parts = [p for p in re.split(r"(?<=[，。！？；：,.!?;:])", text) if p.strip()]
    chunks, cur = [], ""
    for p in parts:
        if cur and len(cur) + len(p) > SUB_MAX:
            chunks.append(cur)
            cur = p
        else:
            cur += p
    if cur:
        chunks.append(cur)
    # 字幕里去掉句末标点，句中的句号逗号换成空格；按字数分配时长
    return [(re.sub(r"[，。；,;.]", "\u3000", c.rstrip("，。；：,.;:")), len(c)) for c in chunks]


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--voice")
    ap.add_argument("--force", action="append", default=[])
    args = ap.parse_args()

    proj = Path(args.project).resolve()
    cfg = json.loads((proj / "narration.json").read_text())
    voice = args.voice or cfg.get("voice", "zf_xiaobei")
    raw_dir = proj / "audio" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    t = LEAD_IN
    timeline, durations, media, srt = [], {}, [], []
    for line in cfg["lines"]:
        lid = line["id"]
        src = synth(line, raw_dir, voice, cfg.get("speed", 1.0), lid in args.force)
        dst = proj / "audio" / f"{lid}.wav"
        clean(src, dst)
        d = round(duration(dst), 3)
        durations[lid] = d

        subs, cursor = [], t
        chunks = split_sub(line["sub"])
        total_w = sum(w for _, w in chunks)
        for text, w in chunks:
            sd = d * w / total_w
            subs.append({"start": round(cursor, 3), "dur": round(sd, 3), "text": text})
            cursor += sd
        # marks：解说词里的关键词出现时刻，按字符位置比例估算，用来对齐画面动作
        marks = [round(t + d * line["tts"].index(k) / len(line["tts"]), 3) for k in line.get("marks", [])]
        timeline.append({"id": lid, "scene": line.get("scene"), "start": round(t, 3), "dur": d,
                         "marks": marks, "subs": subs})

        media.append(f'<audio id="vo-{lid}" src="audio/{lid}.wav" data-start="{t:.3f}" data-duration="{d:.3f}"></audio>')
        for i, s in enumerate(subs):
            media.append(
                f'<div id="sub-{lid}-{i}" class="clip sub" data-start="{s["start"]:.3f}" '
                f'data-duration="{s["dur"]:.3f}"><span>{s["text"]}</span></div>'
            )
            srt.append(f"{len(srt) + 1}\n{srt_time(s['start'])} --> {srt_time(s['start'] + s['dur'])}\n{s['text']}\n")
        t += d + GAP
    total = round(t - GAP + TAIL, 3)

    # 场景时长：从该场景第一句开始，到下一场景第一句开始（最后一个场景到片尾）
    scenes = {}
    for item in timeline:
        sc = item["scene"]
        if sc and sc not in scenes:
            scenes[sc] = item["start"] - GAP / 2
    names = list(scenes)
    vals = {"TOTAL": f"{total:.3f}"}
    for i, sc in enumerate(names):
        start = 0.0 if i == 0 else scenes[sc]
        end = scenes[names[i + 1]] if i + 1 < len(names) else total
        vals[f"{sc}.start"] = f"{start:.3f}"
        vals[f"{sc}.dur"] = f"{end - start:.3f}"
    for item in timeline:
        vals[f"{item['id']}.start"] = f"{item['start']:.3f}"
        vals[f"{item['id']}.dur"] = f"{item['dur']:.3f}"

    timing_js = "const T = " + json.dumps(
        {"total": total, **{i["id"]: {"start": i["start"], "dur": i["dur"], "marks": i["marks"]} for i in timeline}},
        ensure_ascii=False,
    ) + ";"

    html = (proj / "index.html.tpl").read_text()
    html = html.replace("<!-- AUTO:MEDIA -->", "\n      ".join(media))
    html = html.replace("/* AUTO:TIMING */", timing_js)
    html = re.sub(r"\{\{([\w.]+)\}\}", lambda m: vals[m.group(1)], html)
    (proj / "index.html").write_text(html)

    (proj / "durations.json").write_text(json.dumps(durations, ensure_ascii=False, indent=2))
    (proj / "timeline.json").write_text(json.dumps({"total": total, "lines": timeline}, ensure_ascii=False, indent=2))
    (proj / "subtitles.srt").write_text("\n".join(srt))
    print(f"total {total:.2f}s · {len(timeline)} lines · {len(srt)} subtitles")
    for item in timeline:
        print(f"  {item['id']} {item['start']:6.2f}s +{item['dur']:.2f}s  {item['scene']}")


if __name__ == "__main__":
    main()
