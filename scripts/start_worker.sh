#!/bin/sh
set -e
python -m http.server "${PORT:-10000}" &
exec python -m app.realtime.webrtc_agent dev
