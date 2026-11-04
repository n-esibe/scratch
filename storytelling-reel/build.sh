#!/usr/bin/env bash
# Builds storytelling-palestine-reel.mp4 (1080x1920, 30 fps, 10 s, H.264 + AAC).
# Needs: node + playwright (Chromium), python3 + numpy + scipy, ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
WORK="${WORK:-$(mktemp -d)}"

node render.js "$WORK/frames" 30 10
python3 make_audio.py "$WORK/soundtrack.wav"

ffmpeg -y -framerate 30 -i "$WORK/frames/f_%04d.png" -i "$WORK/soundtrack.wav" \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -c:a aac -b:a 192k -ar 48000 -shortest \
  storytelling-palestine-reel.mp4
