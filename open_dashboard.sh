#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT=8000
URL="http://localhost:${PORT}"

echo "=============================="
echo "  DAF OS Webダッシュボードを開く  "
echo "=============================="
echo ""

# 1. ポート8000でdashboard_web/app.pyが起動中か確認する
if lsof -i tcp:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[確認] 既にポート${PORT}でサーバーが起動しています。"
else
    echo "[起動] サーバーが起動していないため、バックグラウンドで起動します..."

    if [ ! -d ".venv" ]; then
        echo "[エラー] .venv が見つかりません。"
        echo "  セットアップ手順:"
        echo "    python3.12 -m venv .venv"
        echo "    source .venv/bin/activate"
        echo "    pip install -r requirements.txt"
        echo '    pip install "setuptools<70"'
        exit 1
    fi

    mkdir -p logs

    # .venv を有効化して dashboard_web/app.py をバックグラウンド起動する
    source .venv/bin/activate
    nohup python dashboard_web/app.py \
        >> logs/dashboard_stdout.log \
        2>> logs/dashboard_stderr.log &

    echo "[起動] サーバーを起動しました（PID: $!）"
    echo "  ログ: logs/dashboard_stdout.log / logs/dashboard_stderr.log"

    # サーバーが応答するまで少し待つ
    for i in $(seq 1 20); do
        if lsof -i tcp:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done
fi

echo ""
echo "[オープン] ブラウザで ${URL} を開きます..."
open "${URL}"

echo ""
echo "完了。ブラウザでダッシュボードを確認してください。"
