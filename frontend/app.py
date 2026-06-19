import os
import subprocess
import time

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32))

MOCK_API_URL = os.environ.get("MOCK_API_URL", "http://localhost:8000")
LOGIN_PASSWORD = os.environ.get("LOGIN_PASSWORD", "")
DEBUG_PASSWORD = os.environ.get("DEBUG_PASSWORD", "")
CS_APP_NAME = os.environ.get("CS_APP_NAME", "melos-frontend")

# AIDR クライアント初期化（環境変数未設定時は無効化）
_aidr_client = None
_aidr_base_url = os.environ.get("CS_AIDR_BASE_URL_TEMPLATE")
_aidr_token = os.environ.get("CS_AIDR_TOKEN")
if _aidr_base_url and _aidr_token:
    try:
        from crowdstrike_aidr import AIGuard
        _aidr_client = AIGuard(base_url_template=_aidr_base_url, token=_aidr_token)
    except Exception:
        pass

# ホワイトリスト: デバッグページで実行可能なコマンド
_ALLOWED_COMMANDS = {
    "id": ["id"],
    "whoami": ["whoami"],
    "uname": ["uname", "-a"],
    "ps": ["ps", "aux"],
    "ls /": ["ls", "/"],
    "os-release": ["cat", "/etc/os-release"],
    "chgrp 0 /etc/ld.so.preload": ["chgrp", "0", "/etc/ld.so.preload"],
}

# レートリミット: IPごとの最終アクセス時刻
_rate_limit: dict[str, float] = {}
_RATE_LIMIT_SECONDS = 5


def _login_required():
    """LOGIN_PASSWORD が設定されている場合、未ログインなら login ページへリダイレクト。"""
    if LOGIN_PASSWORD and not session.get("logged_in"):
        return redirect(url_for("login", next=request.path))
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password", "") == LOGIN_PASSWORD:
            session["logged_in"] = True
            session["username"] = request.form.get("username", "").strip() or "anonymous"
            next_url = request.args.get("next", "")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("index"))
        error = "パスワードが違います"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    if (redir := _login_required()):
        return redir
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    if (redir := _login_required()):
        return redir
    body = request.get_json(silent=True) or {}
    user_message = body.get("message", "")
    if not user_message:
        return jsonify({"error": "message is required"}), 400

    aidr_enabled = body.get("aidr_enabled", True)
    messages = [{"role": "user", "content": user_message}]
    source_ip = request.remote_addr
    user_id = session.get("username", source_ip)

    # AIDR: input ガード
    if _aidr_client and aidr_enabled:
        try:
            _aidr_client.guard_chat_completions(
                event_type="input",
                guard_input={"messages": messages},
                app_id=CS_APP_NAME,
                user_id=user_id,
                llm_provider="openai",
                model="gpt-3.5-turbo",
                source_ip=source_ip,
            )
        except Exception:
            pass

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
    }
    try:
        resp = requests.post(f"{MOCK_API_URL}/v1/chat/completions", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
    except Exception:
        reply = "エラーが発生しました"

    # AIDR: output ガード
    if _aidr_client and aidr_enabled:
        try:
            _aidr_client.guard_chat_completions(
                event_type="output",
                guard_input={"messages": messages + [{"role": "assistant", "content": reply}]},
                app_id=CS_APP_NAME,
                user_id=user_id,
                llm_provider="openai",
                model="gpt-3.5-turbo",
                source_ip=source_ip,
            )
        except Exception:
            pass

    return jsonify({"reply": reply})


@app.route("/debug", methods=["GET", "POST"])
def debug():
    if (redir := _login_required()):
        return redir
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
                                cmd, capture_output=True, text=True, timeout=10, shell=False
                            )
                            output = (result.stdout + result.stderr).strip() or f"(exit code: {result.returncode}, no output)"
                        except subprocess.TimeoutExpired:
                            error = "コマンドがタイムアウトしました"
                        except FileNotFoundError:
                            error = f"コマンドが見つかりません: {cmd[0]}"
                        except Exception as e:
                            error = f"実行エラー: {e}"

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

