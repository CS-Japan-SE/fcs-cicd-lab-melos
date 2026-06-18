import os
import subprocess
import time

import requests
from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32))

MOCK_API_URL = os.environ.get("MOCK_API_URL", "http://localhost:8000")
DEBUG_PASSWORD = os.environ.get("DEBUG_PASSWORD", "")

# ホワイトリスト: デバッグページで実行可能なコマンド
_ALLOWED_COMMANDS = {
    "id": ["id"],
    "whoami": ["whoami"],
    "uname": ["uname", "-a"],
    "ps": ["ps", "aux"],
    "ls /": ["ls", "/"],
    "os-release": ["cat", "/etc/os-release"],
    "falconctl (aid/cid/version)": [
        "/opt/CrowdStrike/rootfs/bin/falconctl", "-g", "--aid", "--cid", "--version"
    ],
}

# レートリミット: IPごとの最終アクセス時刻
_rate_limit: dict[str, float] = {}
_RATE_LIMIT_SECONDS = 5


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True) or {}
    user_message = body.get("message", "")
    if not user_message:
        return jsonify({"error": "message is required"}), 400

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": user_message}],
    }
    try:
        resp = requests.post(f"{MOCK_API_URL}/v1/chat/completions", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
    except Exception as e:
        reply = f"エラーが発生しました: {e}"

    return jsonify({"reply": reply})


@app.route("/debug", methods=["GET", "POST"])
def debug():
    error = None
    output = None
    authenticated = session.get("debug_authenticated", False)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "login":
            password = request.form.get("password", "")
            if DEBUG_PASSWORD and password == DEBUG_PASSWORD:
                session["debug_authenticated"] = True
                authenticated = True
            else:
                error = "パスワードが違います"

        elif action == "logout":
            session.pop("debug_authenticated", None)
            authenticated = False

        elif action == "execute":
            if not authenticated:
                error = "認証エラー"
            else:
                # レートリミットチェック
                client_ip = request.remote_addr
                now = time.time()
                if now - _rate_limit.get(client_ip, 0) < _RATE_LIMIT_SECONDS:
                    error = f"連続実行を制限しています。{_RATE_LIMIT_SECONDS}秒後に再試行してください。"
                else:
                    _rate_limit[client_ip] = now
                    cmd_key = request.form.get("command", "")
                    cmd = _ALLOWED_COMMANDS.get(cmd_key)
                    if cmd is None:
                        error = "許可されていないコマンドです"
                    else:
                        try:
                            result = subprocess.run(
                                cmd, capture_output=True, text=True, timeout=5, shell=False
                            )
                            output = result.stdout or result.stderr
                        except subprocess.TimeoutExpired:
                            error = "コマンドがタイムアウトしました"

    return render_template(
        "debug.html",
        authenticated=authenticated,
        allowed_commands=list(_ALLOWED_COMMANDS.keys()),
        output=output,
        error=error,
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
