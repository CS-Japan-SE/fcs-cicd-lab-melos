#!/bin/sh
set -e

# Falcon Container Sensor のインストール（環境変数が設定されている場合のみ）
if [ -n "$FALCON_CLIENT_ID" ] && [ -n "$FALCON_CLIENT_SECRET" ] && [ -n "$FALCON_CID" ]; then
    echo "[entrypoint] Installing Falcon Container Sensor..."
    falconutil install \
        --client-id "$FALCON_CLIENT_ID" \
        --client-secret "$FALCON_CLIENT_SECRET" \
        --cid "$FALCON_CID" || echo "[entrypoint] Warning: falconutil install failed, continuing without sensor"
else
    echo "[entrypoint] Falcon credentials not set, skipping sensor installation"
fi

# アプリ起動
exec python -m flask run --host=0.0.0.0 --port=5000
