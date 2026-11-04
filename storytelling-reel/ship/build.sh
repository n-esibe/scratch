#!/usr/bin/env bash
# Builds storytelling-palestine-ship-reel.mp4 (1080x1920, 30 fps, 10 s, H.264 + AAC, ambient sound only).
# Needs: node + playwright (Chromium), `npm install` here (three.js), python3 + numpy + scipy, ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
WORK="${WORK:-$(mktemp -d)}"
[ -d node_modules/three ] || npm install
[ -f waternormals.jpg ] || curl -sSLo waternormals.jpg https://raw.githubusercontent.com/mrdoob/three.js/r160/examples/textures/waternormals.jpg

node render.js "$WORK/frames" 30 10
python3 make_audio.py "$WORK/ambience.wav"

ffmpeg -y -framerate 30 -i "$WORK/frames/f_%04d.png" -i "$WORK/ambience.wav" \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -c:a aac -b:a 192k -ar 48000 -shortest \
  storytelling-palestine-ship-reel.mp4
