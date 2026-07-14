#!/bin/sh
set -e
mkdir -p /tmp/stub_root
(cd /tmp/stub_root && python -m http.server "${PORT:-10000}") &
exec python -m app.realtime.webrtc_agent dev
