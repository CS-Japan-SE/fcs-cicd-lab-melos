# メロスに聞け！

> 問え。メロスが答える。

CrowdStrike Falcon CI/CD デモ環境です。GitHub Actions と Render を使い、コンテナイメージのビルド・スキャン・デプロイを自動化します。

## アーキテクチャ

```
GitHub (push)
  → GitHub Actions
      1. アプリイメージをビルド
      2. falconutil patch-image でFalcon Sensorを埋め込む
      3. FCS Scan (IaC / Image Scan / SBOM)
      4. ghcr.io にpush
  → Render Deploy Hook
      → センサー入りイメージをデプロイ

                    ┌──────────────────┐
                    │   Render         │
              ┌─────┴──────┬───────────┴──────┐
         frontend          mock-api
       (Flask + Sensor)   (FastAPI, 内部のみ)
```

| サービス | 役割 | Falcon Sensor |
|---|---|---|
| **frontend** | チャットUI・AIプロキシ | ビルド時に falconutil で埋め込み |
| **mock-api** | OpenAI互換モックAPI（走れメロス返答） | なし（内部通信のみ） |

## CI/CDパイプライン

| ステップ | 内容 |
|---|---|
| Docker Build | frontend（ベース）/ mock-api をビルド |
| Falcon Sensor Pull | CrowdStrike レジストリから最新センサーイメージを取得 |
| falconutil patch-image | frontendイメージにFalcon Sensorを埋め込み |
| IaC Scan | Dockerfile・render.yaml の設定ミスを検出 |
| Image Scan | センサー入りイメージの脆弱性スキャン |
| SBOM Generation | ソフトウェア部品表を生成 |
| Push to ghcr.io | センサー入りイメージをGitHub Container Registryにpush |
| Deploy | Render Deploy Hook でデプロイをトリガー |

## セットアップ

### 1. GitHub Secrets の設定

| Secret名 | 用途 |
|---|---|
| `FALCON_CLIENT_ID` | Falcon API 認証（センサー取得・FCS Scan） |
| `FALCON_CLIENT_SECRET` | Falcon API 認証（センサー取得・FCS Scan） |
| `FALCON_CID` | Falcon Container Sensor の CID（ビルド時に埋め込み） |
| `RENDER_DEPLOY_HOOK_FRONTEND` | Render frontend デプロイフック URL |
| `RENDER_DEPLOY_HOOK_MOCK_API` | Render mock-api デプロイフック URL |

### 2. Render の設定

Render Dashboard で render.yaml をインポート後、`melos-frontend` サービスに以下を手動設定：

- `FLASK_SECRET_KEY`（任意のランダム文字列: `openssl rand -hex 32` で生成）
- `LOGIN_PASSWORD`（チャット画面のログインパスワード）
- `DEBUG_PASSWORD`（デバッグページ用パスワード）
- `CS_AIDR_BASE_URL_TEMPLATE`（例: `https://api.crowdstrike.com/aidr/{SERVICE_NAME}`）
- `CS_AIDR_TOKEN`（AIDR 認証トークン）

> Falcon APIキー・CIDはRenderには不要です。センサーはGitHub ActionsのビルドステップでイメージにPatchされます。

## デバッグページ（EDR デモ用）

`/debug` にアクセスするとパスワード保護されたコマンド実行ページが表示されます。

- 実行可能コマンドは `id`, `whoami`, `uname -a`, `ps aux`, `ls /`, `cat /etc/os-release`, `chgrp 0 /etc/ld.so.preload` のみ
- `chgrp 0 /etc/ld.so.preload` は Falcon EDR アラート発報用のデモコマンド
- Falcon Sensor がコマンドラインを記録するため、Falcon Console の Process Timeline / AIDR でキャプチャを確認できます

## AIDR 連携

チャット画面右上の AIDR トグルで ON/OFF を切り替えられます。ON 時はユーザー入力（input）と AI レスポンス（output）を CrowdStrike AIDR に送信します。

## ローカル開発

```bash
# CA証明書が必要な環境（Zscaler等）では事前に設定
export EXTRA_CA_CERT="$(cat ~/.config/crowdstrike-ROOT-CA.crt)"

# 起動（初回はイメージのビルドが行われます）
EXTRA_CA_CERT="$EXTRA_CA_CERT" docker compose up --build -d
```

アクセス: <http://localhost:5000>（ログインパスワード: `LOGIN_PASSWORD` 環境変数で指定、デフォルト `demo`）

```bash
# 停止
docker compose down
```

### 環境変数（ローカル）

| 変数 | デフォルト | 用途 |
|---|---|---|
| `LOGIN_PASSWORD` | `demo` | チャット画面のログインパスワード |
| `DEBUG_PASSWORD` | `debug` | デバッグページのパスワード |
| `CS_AIDR_BASE_URL_TEMPLATE` | （なし） | AIDR エンドポイント（未設定時は無効） |
| `CS_AIDR_TOKEN` | （なし） | AIDR 認証トークン |

## 技術スタック

- **Frontend**: Python / Flask, HTML + Tailwind CSS
- **Mock API**: Python / FastAPI
- **Container Registry**: GitHub Container Registry (ghcr.io)
- **CI/CD**: GitHub Actions + CrowdStrike FCS Action
- **Hosting**: Render (無料枠)
- **Security**: CrowdStrike Falcon Container Sensor (falconutil patch-image), CrowdStrike AIDR
