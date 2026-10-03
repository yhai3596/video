#!/usr/bin/env python3
"""成片收尾：可选混入背景音乐（人声出现时自动压低），再两遍 loudnorm 到 -16 LUFS / TP -1.5，视频流直接复制。

用法：python3 tools/finalize.py <输入.mp4> <输出.mp4> [--bgm 音乐文件] [--bgm-lufs -28] [--bgm-start 0]
"""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

TARGET = "I=-16:TP=-1.5:LRA=11"


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def mix_bgm(src, bgm, out, lufs, start):
    """人声 + 背景音乐：音乐先统一到 lufs，裁到片长并首尾淡入淡出，再用人声做侧链压缩自动避让。"""
    d = duration(src)
    fc = (
        "[0:a]aresample=48000,asplit=2[vo][sc];"
        f"[1:a]aresample=48000,atrim=start={start}:duration={d},asetpts=PTS-STARTPTS,"
        f"loudnorm=I={lufs}:TP=-6,afade=t=in:d=1.5,afade=t=out:st={max(d - 2.5, 0)}:d=2.5[bg];"
        # 本类片子几乎全程有人声，避让要轻：实测压低后音乐约比人声低 18–19 LU（常见做法 15–20 dB）
        "[bg][sc]sidechaincompress=threshold=0.08:ratio=2.5:attack=30:release=500[bgd];"
        "[vo][bgd]amix=inputs=2:duration=first:normalize=0[mix]"
    )
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-i", str(bgm), "-filter_complex", fc,
                    "-map", "0:v", "-map", "[mix]", "-c:v", "copy", "-c:a", "pcm_s16le", str(out)], check=True)


def loudnorm(src, dst):
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(src), "-af", f"loudnorm={TARGET}:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    ).stderr
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", probe).group(0))
    af = (f"loudnorm={TARGET}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "copy", "-af", af, "-ar", "48000",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)],
        check=True,
    )
    return m["input_i"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--bgm", help="背景音乐文件")
    ap.add_argument("--bgm-lufs", type=float, default=-28.0, help="混音前把音乐统一到的响度（越小越轻）")
    ap.add_argument("--bgm-start", type=float, default=0.0, help="从音乐的第几秒开始用")
    args = ap.parse_args()

    src = Path(args.src)
    with tempfile.TemporaryDirectory() as tmp:
        if args.bgm:
            mixed = Path(tmp) / "mixed.mkv"
            mix_bgm(src, args.bgm, mixed, args.bgm_lufs, args.bgm_start)
            src = mixed
        before = loudnorm(src, args.dst)
    print(f"{args.src}{' + ' + args.bgm if args.bgm else ''}: {before} LUFS → {args.dst}")


if __name__ == "__main__":
    main()
