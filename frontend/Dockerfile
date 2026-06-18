FROM python:3.11-slim

WORKDIR /app

# falconutil インストール（Falcon Container Sensor用）
RUN apt-get update && apt-get install -y curl && \
    curl -L https://github.com/CrowdStrike/falcon-container-sensor/releases/latest/download/falconutil-linux-amd64 \
    -o /usr/local/bin/falconutil && \
    chmod +x /usr/local/bin/falconutil && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Falcon Sensor をインストールしてからアプリを起動するエントリーポイント
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
