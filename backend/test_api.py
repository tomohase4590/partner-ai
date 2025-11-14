"""
API動作確認スクリプト
バックエンドが正しく動作しているかテスト
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    """セクションタイトル表示"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_health_check():
    """ヘルスチェック"""
    print_section("1. ヘルスチェック")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ ステータス: {response.status_code}")
        print(f"📄 レスポンス: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def test_models_list():
    """モデル一覧取得"""
    print_section("2. モデル一覧取得")
    
    try:
        response = requests.get(f"{BASE_URL}/api/models")
        data = response.json()
        print(f"✅ 利用可能なモデル数: {len(data['models'])}")
        for model in data['models']:
            size_gb = model['size'] / (1024**3)
            print(f"  - {model['name']}: {size_gb:.1f} GB")
        return True
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def test_chat():
    """チャット機能テスト"""
    print_section("3. チャット機能テスト")
    
    try:
        # リクエスト送信
        print("📤 リクエスト送信中...")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "user_id": "test_user",
                "message": "こんにちは！あなたの名前は？",
                "model": "gemma3:4b"  # 高速モデルでテスト
            }
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 応答成功 ({elapsed:.2f}秒)")
            print(f"🤖 AI: {data['response']}")
            print(f"📊 使用モデル: {data['model_used']}")
            print(f"🆔 会話ID: {data['conversation_id']}")
            return data['conversation_id']
        else:
            print(f"❌ エラー: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

def test_feedback(conversation_id):
    """フィードバック機能テスト"""
    print_section("4. フィードバック保存テスト")
    
    if not conversation_id:
        print("⚠️ スキップ（会話IDなし）")
        return False
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/feedback",
            json={
                "conversation_id": conversation_id,
                "rating": 5,
                "comment": "テストコメント"
            }
        )
        
        if response.status_code == 200:
            print(f"✅ フィードバック保存成功")
            print(f"📄 レスポンス: {response.json()}")
            return True
        else:
            print(f"❌ エラー: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def test_history():
    """履歴取得テスト"""
    print_section("5. 履歴取得テスト")
    
    try:
        response = requests.get(f"{BASE_URL}/api/history/test_user")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 履歴取得成功")
            print(f"📊 総会話数: {data['total']}")
            
            if data['conversations']:
                latest = data['conversations'][0]
                print(f"\n最新の会話:")
                print(f"  ユーザー: {latest['user_message'][:50]}...")
                print(f"  AI: {latest['ai_response'][:50]}...")
            
            return True
        else:
            print(f"❌ エラー: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def test_stats():
    """統計取得テスト"""
    print_section("6. 統計取得テスト")
    
    try:
        response = requests.get(f"{BASE_URL}/api/stats/test_user")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 統計取得成功")
            print(f"📊 総会話数: {data['total_conversations']}")
            print(f"⭐ 平均評価: {data['average_rating']}")
            print(f"🤖 最も使用: {data['most_used_model']}")
            return True
        else:
            print(f"❌ エラー: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("\n" + "🚀" * 30)
    print("  パートナーAI - API動作確認")
    print("🚀" * 30)
    
    # テスト実行
    results = []
    
    # 1. ヘルスチェック
    results.append(("ヘルスチェック", test_health_check()))
    
    # 2. モデル一覧
    results.append(("モデル一覧", test_models_list()))
    
    # 3. チャット
    conv_id = test_chat()
    results.append(("チャット", conv_id is not None))
    
    # 4. フィードバック
    results.append(("フィードバック", test_feedback(conv_id)))
    
    # 5. 履歴
    results.append(("履歴取得", test_history()))
    
    # 6. 統計
    results.append(("統計取得", test_stats()))
    
    # 結果サマリー
    print_section("テスト結果サマリー")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n合計: {passed}/{total} テスト成功")
    
    if passed == total:
        print("\n🎉 全てのテストが成功しました！")
        print("👉 次のステップ: フロントエンド実装")
    else:
        print("\n⚠️ 一部のテストが失敗しました")
        print("👉 エラーメッセージを確認してください")

if __name__ == "__main__":
    main()