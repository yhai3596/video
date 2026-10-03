#!/usr/bin/env python3
"""逐句配音 → 真实时长 → 字幕与画面时间轴。

用法：python3 tools/narrate.py <项目目录> [--force L03] [--mac-script]

项目目录需要：
  narration.json  {"engine": "listenhub|kokoro", "voice": "...", "speed": 1.1,  # speed 默认 1.1
                   "lines": [{"id": "L01", "scene": "s1", "tts": "读法文本", "sub": "字幕文本",
                              "marks": ["关键词"]}]}  # marks 可选
  index.html.tpl   含占位符：{{TOTAL}}、{{<scene>.start}}、{{<scene>.dur}}、{{<Lxx>.start}}、{{<Lxx>.dur}}、
                  <!-- AUTO:MEDIA -->（替换为每句 <audio> 与字幕 clip）、/* AUTO:TIMING */（替换为 const T = {...}）

配音引擎：
  listenhub  环境里配 API credentials（host: api.marswave.ai）或设置 LISTENHUB_API_KEY；voice 填 speakerId
  kokoro     HyperFrames 内置本地模型，中文只有 zf_xiaobei
audio/raw/manifest.json 记录本脚本生成的每句用了哪个引擎、音色、语速和文本；任一变化自动重配那一句，
--force <id> 强制重配。不是本脚本生成的 audio/raw/<id>.mp3|.wav 视为手动放入，优先使用，不会被删除。
云端连不上 ListenHub 时，用 --mac-script 生成 audio/listenhub_tts.command，在 Mac 上双击逐句生成。

产物：audio/<id>.wav（去首尾静音、响度 -16 LUFS）、durations.json、timeline.json、subtitles.srt、index.html
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

LEAD_IN = 0.4   # 第一句前留白
GAP = 0.3       # 句间停顿
TAIL = 1.0      # 最后一句后留白
SUB_MAX = 18    # 单条字幕最多字数，超过按标点拆分
HF = ["npx", "-y", "hyperframes@0.8.114"]
LISTENHUB_TTS_URL = "https://api.marswave.ai/openapi/v1/tts"
DEFAULT_SPEED = 1.1  # 默认语速：1.0 偏慢，统一后处理加速到 1.1 倍（narration.json 里写 speed 可覆盖）


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.stdout.strip())


def fingerprint(engine, voice, text):
    # 语速是后处理（atempo），不进指纹：改语速不需要重新生成配音
    return hashlib.sha1(f"{engine}|{voice}|{text}".encode()).hexdigest()[:12]


def file_hash(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


def synth(line, raw_dir, manifest, engine, voice, force):
    lid = line["id"]
    fp = fingerprint(engine, voice, line["tts"])
    existing = [p for p in (raw_dir / f"{lid}.mp3", raw_dir / f"{lid}.wav") if p.exists()]
    rec = manifest.get(lid)
    # 本脚本生成的文件：文件名和内容哈希都与 manifest 记录一致；其余视为手动放入（如 Mac 上生成后传回）
    ours = [p for p in existing if rec and p.name == rec["file"] and file_hash(p) == rec["sha"]]
    manual = [p for p in existing if p not in ours]
    if not force:
        if manual:
            print(f"  {lid}: 使用手动放入的 {manual[0].name}（改了文本不会自动重配，需要重新生成后替换）")
            return manual[0]
        if ours and rec["fp"] == fp:
            return ours[0]
    # 先生成到临时文件，成功后再替换旧文件；调用失败时已有音频不受影响
    ext = "mp3" if engine == "listenhub" else "wav"
    out, tmp = raw_dir / f"{lid}.{ext}", raw_dir / f"{lid}.tmp.{ext}"
    if engine == "listenhub":
        # 直接调 OpenAPI，不走 listenhub CLI（CLI 0.0.22 的 --speed 校验用浮点乘法，1.1 会被误拒）。
        # 不传 speed：实测 ListenHub 的 speed=1.1 只是生成提示，10 句整体只快 4.9%，单句 0.91–1.28 倍不等。
        # curl 默认走 HTTPS_PROXY；环境配了 API credentials 时 Key 由代理注入，否则用 LISTENHUB_API_KEY。
        body = json.dumps({"input": line["tts"], "voice": voice, "response_format": "mp3"}, ensure_ascii=False)
        cmd = ["curl", "-sS", "--fail-with-body", "--max-time", "180", "-X", "POST", LISTENHUB_TTS_URL,
               "-H", "Content-Type: application/json", "--data-binary", "@-", "-o", str(tmp)]
        if os.environ.get("LISTENHUB_API_KEY"):
            cmd[1:1] = ["-H", f"Authorization: Bearer {os.environ['LISTENHUB_API_KEY']}"]
        r = subprocess.run(cmd, input=body, capture_output=True, text=True)
        if r.returncode != 0:
            err = (tmp.read_text(errors="ignore") if tmp.exists() else "") or r.stderr
            tmp.unlink(missing_ok=True)
            raise SystemExit(f"{lid}: ListenHub 调用失败。\n{err.strip()[-800:]}\n"
                             "检查：环境的 API credentials 是否配了 api.marswave.ai，或设置 LISTENHUB_API_KEY；"
                             "云端不通时用 --mac-script 在 Mac 上生成。")
    else:
        run(HF + ["tts", line["tts"], "-v", voice, "-o", str(tmp)])
    for p in (existing if force else ours):
        p.unlink(missing_ok=True)
    tmp.rename(out)
    manifest[lid] = {"fp": fp, "file": out.name, "sha": file_hash(out)}
    return out


def write_mac_script(proj, cfg):
    """生成 Mac 上双击运行的逐句配音脚本（已存在的文件跳过），产物放进 audio/raw/。"""
    voice = cfg["voice"]
    lines = [
        "#!/bin/bash",
        "# 由 tools/narrate.py --mac-script 生成：逐句调用 ListenHub OpenAPI，已存在的跳过",
        "# 需要先 export LISTENHUB_API_KEY=你的Key。按正常语速生成，语速由 narrate.py 后处理",
        'cd "$(dirname "$0")/raw" || exit 1',
        ': "${LISTENHUB_API_KEY:?先 export LISTENHUB_API_KEY}"',
        "gen() {",
        '  if [ -s "$1.mp3" ]; then echo "skip $1"; return; fi',
        f'  python3 -c \'import json,sys; print(json.dumps({{"input": sys.argv[1], "voice": {json.dumps(voice)}, '
        '"response_format": "mp3"}, ensure_ascii=False))\' "$2" \\',
        f'    | curl -sS --fail-with-body -X POST {LISTENHUB_TTS_URL} -H "Authorization: Bearer $LISTENHUB_API_KEY" '
        '-H "Content-Type: application/json" --data-binary @- -o "$1.mp3" && echo "done $1"',
        "}",
    ]
    lines += [f"gen {line['id']} {shlex.quote(line['tts'])}" for line in cfg["lines"]]
    lines += ['echo "全部完成，把 audio/raw/ 下的 mp3 传回项目后重新运行 narrate.py"', "read -n 1 -s -r -p '按任意键关闭'"]
    path = proj / "audio" / "listenhub_tts.command"
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o755)
    print(f"已生成 {path}")


def clean(src, dst, speed):
    # 去掉首尾静音（尾部用 areverse 翻转后再去一次），按 speed 精确变速（atempo 不变调），再统一响度和采样率
    af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
          "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,"
          f"atempo={speed},loudnorm=I=-16:TP=-1.5:LRA=11")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", "48000", "-ac", "1", str(dst)])


def pauses(path):
    """检测句内停顿，返回各停顿中点（秒，相对本句开头）。"""
    out = subprocess.run(["ffmpeg", "-i", str(path), "-af", "silencedetect=noise=-32dB:d=0.12", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return [(a + b) / 2 for a, b in zip(starts, ends)]


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
    ap.add_argument("--force", action="append", default=[])
    ap.add_argument("--mac-script", action="store_true")
    args = ap.parse_args()

    proj = Path(args.project).resolve()
    cfg = json.loads((proj / "narration.json").read_text())
    engine = cfg.get("engine", "kokoro")
    voice = cfg.get("voice", "zf_xiaobei")
    speed = cfg.get("speed", DEFAULT_SPEED)
    raw_dir = proj / "audio" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if args.mac_script:
        write_mac_script(proj, cfg)
        return
    manifest_path = raw_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    t = LEAD_IN
    timeline, durations, media, srt = [], {}, [], []
    for line in cfg["lines"]:
        lid = line["id"]
        src = synth(line, raw_dir, manifest, engine, voice, lid in args.force)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        dst = proj / "audio" / f"{lid}.wav"
        clean(src, dst, speed)
        d = round(duration(dst), 3)
        durations[lid] = d

        # 字幕切换点：先按字数比例估算，再对齐到 0.5 秒内最近的真实停顿
        chunks = split_sub(line["sub"])
        total_w = sum(w for _, w in chunks)
        ps = pauses(dst)
        bounds, acc = [0.0], 0.0
        for _, w in chunks[:-1]:
            acc += d * w / total_w
            near = min(ps, key=lambda p: abs(p - acc), default=None)
            bounds.append(near if near is not None and abs(near - acc) <= 0.5 and near > bounds[-1] else acc)
        bounds.append(d)
        subs = [{"start": round(t + a, 3), "dur": round(b - a, 3), "text": text}
                for (text, _), a, b in zip(chunks, bounds, bounds[1:])]
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
