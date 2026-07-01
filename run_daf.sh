#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================"
echo "  Starting DAF OS v0.8  "
echo "========================"
echo ""

cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "[エラー] .venv が見つかりません。"
    echo "  セットアップ手順:"
    echo "    python3.12 -m venv .venv"
    echo "    source .venv/bin/activate"
    echo "    pip install -r requirements.txt"
    echo '    pip install "setuptools<70"'
    exit 1
fi

source .venv/bin/activate

python main.py

echo ""
echo "========================"
echo "  DAF OS 完了"
echo "========================"
echo ""
echo "📋 ダッシュボード: $SCRIPT_DIR/outputs/dashboard.md"
echo ""
echo "ファイルを開くには:"
echo "  open $SCRIPT_DIR/outputs/dashboard.md"
