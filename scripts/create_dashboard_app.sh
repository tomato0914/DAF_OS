#!/bin/bash
# DAF Dashboard.app を作成するスクリプト。
# 生成された .app をダブルクリックすると、DAF_OS/open_dashboard.sh を実行し、
# Webダッシュボード（http://localhost:8000）を開く。
#
# 使い方:
#   ./scripts/create_dashboard_app.sh
#
set -e

# DAF_OS のルートディレクトリ（scripts/ の一つ上）を絶対パスで解決する
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OPEN_SCRIPT="${SCRIPT_DIR}/open_dashboard.sh"
APP_NAME="DAF Dashboard.app"

echo "=================================="
echo "  DAF Dashboard.app を作成します  "
echo "=================================="
echo ""
echo "対象ディレクトリ: ${SCRIPT_DIR}"

if [ ! -f "${OPEN_SCRIPT}" ]; then
    echo "[エラー] open_dashboard.sh が見つかりません: ${OPEN_SCRIPT}"
    exit 1
fi

# 出力先を決定する。/Applications に書き込めればそこに、
# 書き込めなければ DAF_OS フォルダ内に作成する。
if [ -w "/Applications" ]; then
    OUTPUT_DIR="/Applications"
else
    OUTPUT_DIR="${SCRIPT_DIR}"
    echo "[情報] /Applications に書き込めないため、DAF_OSフォルダ内に作成します。"
fi

OUTPUT_PATH="${OUTPUT_DIR}/${APP_NAME}"

# アプリ起動時に実行するAppleScriptを生成する。
# open_dashboard.sh の絶対パスを埋め込むことで、
# Dockやどこから起動しても正しいディレクトリで実行される。
TMP_BASE="$(mktemp -t daf_dashboard_app)"
TMP_SCRIPT="${TMP_BASE}.applescript"
mv "${TMP_BASE}" "${TMP_SCRIPT}"
cat > "${TMP_SCRIPT}" <<EOF
do shell script "cd " & quoted form of "${SCRIPT_DIR}" & " && ./open_dashboard.sh > /dev/null 2>&1 &"
EOF

# 既存の .app があれば一度削除してから作り直す
if [ -e "${OUTPUT_PATH}" ]; then
    echo "[情報] 既存の ${OUTPUT_PATH} を置き換えます。"
    rm -rf "${OUTPUT_PATH}"
fi

osacompile -o "${OUTPUT_PATH}" "${TMP_SCRIPT}"
rm -f "${TMP_SCRIPT}"

echo ""
echo "[完了] ${OUTPUT_PATH} を作成しました。"
echo ""
echo "次の手順："
echo "  1. Finderで ${OUTPUT_PATH} を開く"
echo "  2. Dockに追加する場合は、アイコンをDockにドラッグ＆ドロップする"
echo "  3. ダブルクリック（またはDockのアイコンをクリック）すると"
echo "     http://localhost:8000 がブラウザで開きます"
echo ""
echo "※ 既にダッシュボードサーバーが起動中の場合は、二重起動せずブラウザだけが開きます。"
