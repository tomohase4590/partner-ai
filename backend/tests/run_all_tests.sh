#!/bin/bash

# 全テスト実行スクリプト

echo "=================================="
echo "🧪 パートナーAI 統合テスト"
echo "=================================="
echo ""

# カレントディレクトリを保存
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Pythonの確認
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3が見つかりません"
    exit 1
fi

echo "✅ Python3: $(python3 --version)"
echo ""

# 1. ベースラインテスト
echo "=================================="
echo "1️⃣  ベースラインテスト実行"
echo "=================================="
echo ""

python3 baseline_system.py

if [ $? -ne 0 ]; then
    echo "❌ ベースラインテスト失敗"
    exit 1
fi

echo ""
echo "✅ ベースラインテスト完了"
echo ""
echo "⏸️  次のテストに進みますか？ (Enter キーを押してください)"
read

# 2. 統合テスト
echo ""
echo "=================================="
echo "2️⃣  統合テスト実行"
echo "=================================="
echo ""

python3 test_system.py

if [ $? -ne 0 ]; then
    echo "❌ 統合テスト失敗"
    exit 1
fi

echo ""
echo "=================================="
echo "✅ 全テスト完了"
echo "=================================="
echo ""

# レポート一覧
echo "📊 生成されたレポート:"
ls -lh *_report_*.json 2>/dev/null || echo "  レポートファイルなし"

echo ""
echo "🎉 テストが正常に完了しました"