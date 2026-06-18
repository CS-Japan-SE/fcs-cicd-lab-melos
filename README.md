# メロスに聞け！

> 問え。メロスが答える。

CrowdStrike Falcon CI/CD デモ環境です。GitHub Actions と Render を使い、コンテナイメージのビルド・スキャン・デプロイを自動化します。

## アーキテクチャ

```
GitHub (push) → GitHub Actions (CI: FCS Scan) → Render (CD: デプロイ)
                                                      │
                                               ┌──────┴──────┐
                                         frontend        mock-api
                                       (Flask + Sensor)  (FastAPI)
```

| サービス | 役割 | Falcon Sensor |
|---|---|---|
| **frontend** | チャットUI・AIプロキシ | falconutil でインストール |
| **mock-api** | OpenAI互換モックAPI（走れメロス返答） | なし（内部通信のみ） |

## CI/CDパイプライン

| ステップ | 内容 |
|---|---|
| Docker Build | frontend / mock-api をビルド |
| IaC Scan | Dockerfile・render.yaml の設定ミスを検出 |
| Image Scan | コンテナイメージの脆弱性スキャン |
| SBOM Generation | ソフトウェア部品表を生成 |
| Deploy | Render Deploy Hook でデプロイをトリガー |

## セットアップ

### 1. GitHub Secrets の設定

| Secret名 | 用途 |
|---|---|
| `FALCON_CLIENT_ID` | Falcon API 認証 |
| `FALCON_CLIENT_SECRET` | Falcon API 認証 |
| `FALCON_CID` | Falcon Container Sensor インストール用 CID |
| `RENDER_DEPLOY_HOOK_FRONTEND` | Render frontend デプロイフック URL |
| `RENDER_DEPLOY_HOOK_MOCK_API` | Render mock-api デプロイフック URL |

### 2. Render の設定

Render Dashboard で render.yaml をインポート後、以下を手動設定：

- `FALCON_CLIENT_ID`
- `FALCON_CLIENT_SECRET`
- `FALCON_CID`
- `DEBUG_PASSWORD`（デバッグページ用パスワード）

## デバッグページ（EDR デモ用）

`/debug` にアクセスするとパスワード保護されたコマンド実行ページが表示されます。

- 実行可能コマンドは `id`, `whoami`, `uname -a`, `ps aux`, `ls /`, `cat /etc/os-release` のみ
- Falcon Sensor がコマンドラインを記録するため、Falcon Console の Process Timeline / AIDR でキャプチャを確認できます

## ローカル開発

```bash
# mock-api 起動
cd mock-api
pip install -r requirements.txt
uvicorn app:app --port 8000

# frontend 起動（別ターミナル）
cd frontend
pip install -r requirements.txt
MOCK_API_URL=http://localhost:8000 flask run --port 5000
```

## 技術スタック

- **Frontend**: Python / Flask, HTML + Tailwind CSS
- **Mock API**: Python / FastAPI
- **CI/CD**: GitHub Actions + CrowdStrike FCS Action
- **Hosting**: Render (無料枠)
- **Security**: CrowdStrike Falcon Container Sensor (falconutil)
