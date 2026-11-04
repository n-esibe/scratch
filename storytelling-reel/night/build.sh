#!/usr/bin/env bash
# Builds storytelling-night-reel.mp4 (1080x1920, 30 fps, 10 s, H.264 + AAC; no text, logos or flags).
# Needs: node + playwright (Chromium), `npm install` here (three.js), python3 + numpy + scipy, ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
WORK="${WORK:-$(mktemp -d)}"
[ -d node_modules/three ] || npm install
[ -f waternormals.jpg ] || curl -sSLo waternormals.jpg https://raw.githubusercontent.com/mrdoob/three.js/r160/examples/textures/waternormals.jpg

node render.js "$WORK/frames" 30 10
python3 make_audio.py "$WORK/raw.wav"
# loudness: -15 LUFS integrated, limiter at -1 dBFS
I=$(ffmpeg -hide_banner -i "$WORK/raw.wav" -af ebur128 -f null - 2>&1 | grep -E '^\s+I:' | awk '{print $2}')
G=$(python3 -c "print(-15.0-($I))")
ffmpeg -y -loglevel error -i "$WORK/raw.wav" -af "volume=${G}dB,alimiter=limit=0.89:level=false" -ar 48000 "$WORK/sound.wav"

ffmpeg -y -framerate 30 -i "$WORK/frames/f_%04d.png" -i "$WORK/sound.wav" \
  -c:v libx264 -preset slow -crf 19 -maxrate 14M -bufsize 28M -tune grain -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -c:a aac -b:a 192k -ar 48000 -shortest \
  storytelling-night-reel.mp4
