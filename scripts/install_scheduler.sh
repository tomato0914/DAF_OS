#!/bin/bash
# DAF OS v0.9 — launchd スケジューラ インストーラ
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCHD_DIR="$SCRIPT_DIR/launchd"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
MODE="${1:-test}"   # 引数: test (デフォルト) | daily | uninstall

# ───────────────────────────────
# ヘルパー
# ───────────────────────────────
banner() { echo ""; echo "== $1 =="; echo ""; }
check_loaded() { launchctl list | grep -q "$1" && echo "loaded" || echo "not loaded"; }

# plistのプレースホルダを実際のパスに置換して ~/Library/LaunchAgents へ配置
install_plist() {
    local label="$1"
    local src="$LAUNCHD_DIR/${label}.plist"
    local dst="$LAUNCH_AGENTS/${label}.plist"

    if [ ! -f "$src" ]; then
        echo "[エラー] $src が見つかりません"
        exit 1
    fi

    mkdir -p "$LAUNCH_AGENTS"

    sed \
        -e "s|DAF_OS_DIR|$SCRIPT_DIR|g" \
        -e "s|HOME_DIR|$HOME|g" \
        "$src" > "$dst"

    echo "  ✓ plist を配置: $dst"
}

unload_if_loaded() {
    local label="$1"
    local dst="$LAUNCH_AGENTS/${label}.plist"
    if launchctl list | grep -q "$label"; then
        launchctl unload "$dst" 2>/dev/null && echo "  ✓ アンロード: $label"
    fi
}

# ───────────────────────────────
# ログフォルダを確保
# ───────────────────────────────
mkdir -p "$SCRIPT_DIR/logs"
touch "$SCRIPT_DIR/logs/daf_stdout.log"
touch "$SCRIPT_DIR/logs/daf_stderr.log"
echo "  ✓ logs/ フォルダを確認"

# ───────────────────────────────
# モード処理
# ───────────────────────────────
case "$MODE" in

  test)
    banner "DAF OS — テストスケジューラ インストール（5分後に1回実行）"

    # daily が残っていたら先にアンロード
    unload_if_loaded "com.daf.daily"

    install_plist "com.daf.test"
    launchctl unload "$LAUNCH_AGENTS/com.daf.test.plist" 2>/dev/null || true
    launchctl load "$LAUNCH_AGENTS/com.daf.test.plist"
    echo "  ✓ com.daf.test をロード"

    echo ""
    echo "5分後に run_daf.sh が自動実行されます。"
    echo ""
    echo "確認コマンド："
    echo "  launchctl list | grep com.daf"
    echo "  tail -f $SCRIPT_DIR/logs/daf_stdout.log"
    ;;

  daily)
    banner "DAF OS — 毎朝8:00 スケジューラ インストール"

    # test が残っていたら先にアンロード
    unload_if_loaded "com.daf.test"
    rm -f "$LAUNCH_AGENTS/com.daf.test.plist"

    install_plist "com.daf.daily"
    launchctl unload "$LAUNCH_AGENTS/com.daf.daily.plist" 2>/dev/null || true
    launchctl load "$LAUNCH_AGENTS/com.daf.daily.plist"
    echo "  ✓ com.daf.daily をロード（毎朝8:00）"

    echo ""
    echo "毎朝8:00に run_daf.sh が自動実行されます。"
    echo ""
    echo "確認コマンド："
    echo "  launchctl list | grep com.daf"
    ;;

  uninstall)
    banner "DAF OS — スケジューラ アンインストール"

    for label in com.daf.test com.daf.daily; do
        unload_if_loaded "$label"
        dst="$LAUNCH_AGENTS/${label}.plist"
        [ -f "$dst" ] && rm "$dst" && echo "  ✓ 削除: $dst"
    done

    echo ""
    echo "スケジューラをアンインストールしました。"
    ;;

  *)
    echo "使い方: $0 [test|daily|uninstall]"
    echo "  test      — 5分後に1回だけ実行（動作確認用）"
    echo "  daily     — 毎朝8:00に実行（本番用）"
    echo "  uninstall — スケジューラを削除"
    exit 1
    ;;
esac

echo ""
echo "ログ確認："
echo "  tail -f $SCRIPT_DIR/logs/daf_stdout.log"
echo "  tail -f $SCRIPT_DIR/logs/daf_stderr.log"
echo ""
