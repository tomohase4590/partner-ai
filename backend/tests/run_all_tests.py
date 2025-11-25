"""
全テスト実行スクリプト（Python版）
"""

import os
import sys
import json
from datetime import datetime

# テストモジュールをインポート
from baseline_system import run_baseline_tests
from test_system import TestSystem


def print_header(text: str):
    """ヘッダー表示"""
    print("\n" + "="*70)
    print(text)
    print("="*70 + "\n")


def main():
    print_header("🧪 パートナーAI 統合テスト")
    
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }
    
    # 1. ベースラインテスト
    print_header("1️⃣  ベースラインテスト（標準Ollama）")
    print("RAG・プロファイル学習なしの標準的なチャットをテストします")
    print()
    
    try:
        baseline_report = run_baseline_tests()
        all_results["tests"].append({
            "name": "baseline",
            "status": "success",
            "report": baseline_report
        })
        print("\n✅ ベースラインテスト完了")
    except Exception as e:
        print(f"\n❌ ベースラインテストエラー: {e}")
        all_results["tests"].append({
            "name": "baseline",
            "status": "error",
            "error": str(e)
        })
        return
    
    input("\n⏸️  Enterキーを押して次のテストへ...")
    
    # 2. 統合テスト（RAG + プロファイル + ファインチューニング）
    print_header("2️⃣  統合テスト（RAG + プロファイル + ファインチューニング）")
    print("拡張機能の効果を検証します")
    print()
    
    test_system = TestSystem()
    
    # テストクエリ
    test_queries = [
        "機械学習の勉強方法でおすすめを教えて",
        "私の趣味に合ったプロジェクトのアイデアある？",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"テストケース {i}/{len(test_queries)}: {query}")
        print(f"{'='*70}\n")
        
        try:
            report = test_system.run_comparison_test(query)
            all_results["tests"].append({
                "name": f"enhanced_test_{i}",
                "query": query,
                "status": "success",
                "report": report
            })
        except Exception as e:
            print(f"\n❌ テストエラー: {e}")
            import traceback
            traceback.print_exc()
            all_results["tests"].append({
                "name": f"enhanced_test_{i}",
                "query": query,
                "status": "error",
                "error": str(e)
            })
        
        if i < len(test_queries):
            input("\n⏸️  Enterキーを押して次のテストへ...")
    
    # 総合レポート保存
    print_header("📊 総合レポート生成")
    
    summary_path = f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"💾 総合レポート保存: {summary_path}")
    
    # サマリー表示
    print("\n" + "="*70)
    print("📋 テストサマリー")
    print("="*70 + "\n")
    
    success_count = sum(1 for t in all_results["tests"] if t["status"] == "success")
    total_count = len(all_results["tests"])
    
    print(f"実行テスト数: {total_count}")
    print(f"成功: {success_count}")
    print(f"失敗: {total_count - success_count}")
    
    for test in all_results["tests"]:
        status_emoji = "✅" if test["status"] == "success" else "❌"
        print(f"\n{status_emoji} {test['name']}")
        if test["status"] == "error":
            print(f"   エラー: {test.get('error', 'Unknown')}")
    
    print_header("🎉 全テスト完了")
    
    # レポートファイル一覧
    print("生成されたレポートファイル:")
    for file in sorted(os.listdir('.')):
        if file.endswith('_report_' + datetime.now().strftime('%Y%m%d') + '.json') or \
           file.endswith('_summary_' + datetime.now().strftime('%Y%m%d') + '.json'):
            file_size = os.path.getsize(file)
            print(f"  - {file} ({file_size:,} bytes)")
    
    return all_results


if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0 if all(t["status"] == "success" for t in results["tests"]) else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ テストが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)