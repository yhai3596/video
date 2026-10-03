#!/usr/bin/env python3
"""成片响度归一：两遍 loudnorm 到 -16 LUFS / TP -1.5，视频流直接复制。

用法：python3 tools/finalize.py <输入.mp4> <输出.mp4>
"""
import json
import re
import subprocess
import sys

TARGET = "I=-16:TP=-1.5:LRA=11"


def main():
    src, dst = sys.argv[1], sys.argv[2]
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", src, "-af", f"loudnorm={TARGET}:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    ).stderr
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", probe).group(0))
    af = (f"loudnorm={TARGET}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", src, "-c:v", "copy", "-af", af, "-ar", "48000",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst],
        check=True,
    )
    print(f"{src}: {m['input_i']} LUFS → {dst}")


if __name__ == "__main__":
    main()
