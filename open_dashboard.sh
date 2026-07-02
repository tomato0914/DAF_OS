#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT=8000
URL="http://localhost:${PORT}"
DASHBOARD_MD="outputs/dashboard.md"
REFRESH_LOG="logs/auto_refresh.log"
STALE_MINUTES=30

mkdir -p logs

# ── 引数解析（--refresh / --no-refresh）──
FORCE_REFRESH=false
NO_REFRESH=false
for arg in "$@"; do
    case "$arg" in
        --refresh)    FORCE_REFRESH=true ;;
        --no-refresh) NO_REFRESH=true ;;
    esac
done

_log_refresh() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${REFRESH_LOG}"
}

# run_daf.sh が既に実行中かどうかを確認する（二重実行防止）
_is_run_daf_running() {
    pgrep -f "run_daf\.sh" >/dev/null 2>&1
}

# outputs/dashboard.md の経過分数を返す。存在しなければ -1 を返す。
_dashboard_age_minutes() {
    if [ ! -f "${DASHBOARD_MD}" ]; then
        echo "-1"
        return
    fi
    local mtime now
    # macOS(BSD stat) を優先し、無ければ GNU stat にフォールバック
    mtime=$(stat -f %m "${DASHBOARD_MD}" 2>/dev/null || stat -c %Y "${DASHBOARD_MD}" 2>/dev/null)
    if [ -z "${mtime}" ]; then
        echo "-1"
        return
    fi
    now=$(date +%s)
    echo $(( (now - mtime) / 60 ))
}

echo "=============================="
echo "  DAF OS Webダッシュボードを開く  "
echo "=============================="
echo ""

# ── 2〜5. 自動リフレッシュ判定（v2.6 Quest46）──
# エラーが発生してもこのブロック全体は失敗を握りつぶし、
# 必ず後続のサーバー起動・ブラウザオープンに進む（安全要件）。
if [ "${NO_REFRESH}" = true ]; then
    echo "[自動リフレッシュ] --no-refresh が指定されたためスキップします。"
    _log_refresh "スキップ（--no-refresh指定）"
elif _is_run_daf_running; then
    echo "[自動リフレッシュ] run_daf.sh が既に実行中のため、二重実行を避けてスキップします。"
    _log_refresh "スキップ（run_daf.sh実行中のため二重実行を回避）"
else
    age_minutes="$(_dashboard_age_minutes)"
    should_refresh=false
    reason=""

    if [ "${FORCE_REFRESH}" = true ]; then
        should_refresh=true
        reason="--refresh が指定されました"
    elif [ "${age_minutes}" = "-1" ]; then
        should_refresh=true
        reason="outputs/dashboard.md が存在しません"
    elif [ "${age_minutes}" -ge "${STALE_MINUTES}" ] 2>/dev/null; then
        should_refresh=true
        reason="outputs/dashboard.md が${age_minutes}分前の生成で古いため（${STALE_MINUTES}分以上）"
    else
        reason="outputs/dashboard.md は${age_minutes}分前に更新済みのため（${STALE_MINUTES}分以内）"
    fi

    if [ "${should_refresh}" = true ]; then
        echo "[自動リフレッシュ] ${reason}"
        echo "[自動リフレッシュ] ./run_daf.sh を実行します..."
        _log_refresh "run_daf.sh 実行開始（理由: ${reason}）"

        # run_daf.sh が失敗しても open_dashboard.sh 自体は止めない
        if ./run_daf.sh >> "${REFRESH_LOG}" 2>&1; then
            _log_refresh "run_daf.sh 実行完了"
            echo "[自動リフレッシュ] 完了しました。"
        else
            _log_refresh "run_daf.sh 実行失敗（詳細は ${REFRESH_LOG} を確認）"
            echo "[警告] run_daf.sh の実行に失敗しました。詳細: ${REFRESH_LOG}"
            echo "        既存のダッシュボードのまま表示を続行します。"
        fi
    else
        echo "[自動リフレッシュ] ${reason} → 再実行しません。"
        _log_refresh "スキップ（${reason}）"
    fi
fi

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
