"""
ベースライン比較システム
標準的なOllamaチャットとの比較用
"""

import ollama
import json
from datetime import datetime
from typing import List, Dict


class BaselineChat:
    """標準的なチャットシステム（機能なし）"""
    
    def __init__(self, model: str = "gemma3:4b"):
        self.model = model
        self.conversation_history: List[Dict] = []
    
    def chat(self, user_message: str) -> str:
        """標準的なチャット"""
        messages = [
            {"role": "system", "content": "あなたは親しみやすく、有能なAIアシスタントです。"},
        ]
        
        # 履歴を追加（直近5件のみ）
        for conv in self.conversation_history[-5:]:
            messages.append({"role": "user", "content": conv['user']})
            messages.append({"role": "assistant", "content": conv['assistant']})
        
        # 現在のメッセージ
        messages.append({"role": "user", "content": user_message})
        
        # 応答生成
        response = ollama.chat(model=self.model, messages=messages)
        ai_response = response['message']['content']
        
        # 履歴に保存
        self.conversation_history.append({
            'user': user_message,
            'assistant': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
        return ai_response
    
    def get_stats(self) -> Dict:
        """統計情報"""
        if not self.conversation_history:
            return {
                "total_conversations": 0,
                "avg_response_length": 0,
                "total_tokens": 0
            }
        
        total_length = sum(len(c['assistant']) for c in self.conversation_history)
        avg_length = total_length / len(self.conversation_history)
        
        return {
            "total_conversations": len(self.conversation_history),
            "avg_response_length": round(avg_length, 1),
            "total_characters": total_length
        }


class ComparisonRunner:
    """比較テスト実行"""
    
    def __init__(self, model: str = "gemma3:4b"):
        self.baseline = BaselineChat(model)
    
    def run_conversation_set(self, conversations: List[str]) -> Dict:
        """会話セットを実行"""
        print(f"\n{'='*60}")
        print(f"💬 ベースライン会話開始（{len(conversations)}件）")
        print(f"{'='*60}\n")
        
        results = []
        
        for i, user_msg in enumerate(conversations, 1):
            print(f"[{i}/{len(conversations)}] ユーザー: {user_msg}")
            
            response = self.baseline.chat(user_msg)
            
            print(f"            AI応答: {response[:100]}...")
            print()
            
            results.append({
                "user": user_msg,
                "response": response,
                "length": len(response)
            })
        
        stats = self.baseline.get_stats()
        
        print(f"\n{'='*60}")
        print(f"📊 ベースライン統計")
        print(f"{'='*60}")
        print(f"総会話数: {stats['total_conversations']}")
        print(f"平均応答長: {stats['avg_response_length']}文字")
        print(f"総文字数: {stats['total_characters']}")
        
        return {
            "results": results,
            "stats": stats
        }
    
    def compare_with_context(self, test_query: str, context_info: str = None) -> Dict:
        """コンテキストありなしの比較"""
        print(f"\n{'='*60}")
        print(f"🔬 コンテキスト比較テスト")
        print(f"{'='*60}\n")
        
        # 1. コンテキストなし
        print("1️⃣  コンテキストなし:")
        print(f"   クエリ: {test_query}")
        response_no_context = self.baseline.chat(test_query)
        print(f"   応答: {response_no_context[:150]}...\n")
        
        # 2. コンテキストあり（新しいインスタンス）
        baseline_with_context = BaselineChat(self.baseline.model)
        
        if context_info:
            # コンテキスト情報を先に入力
            print("2️⃣  コンテキストあり:")
            print(f"   コンテキスト: {context_info}")
            baseline_with_context.chat(context_info)
        
        print(f"   クエリ: {test_query}")
        response_with_context = baseline_with_context.chat(test_query)
        print(f"   応答: {response_with_context[:150]}...\n")
        
        return {
            "no_context": {
                "response": response_no_context,
                "length": len(response_no_context)
            },
            "with_context": {
                "response": response_with_context,
                "length": len(response_with_context),
                "context": context_info
            }
        }


def run_baseline_tests():
    """ベースラインテストを実行"""
    
    runner = ComparisonRunner()
    
    # テスト会話セット
    test_conversations = [
        "こんにちは",
        "機械学習について教えて",
        "Pythonでコードを書くのが好きなんだ",
        "ディープラーニングのフレームワークでおすすめは？",
        "東京で働いているエンジニアです",
        "週末はカフェでコーディングします",
        "NeuralNetworkの実装方法を知りたい",
        "TransformerとBERTの違いは？",
    ]
    
    # 会話セット実行
    result = runner.run_conversation_set(test_conversations)
    
    # コンテキスト比較
    comparison = runner.compare_with_context(
        test_query="私に合った勉強方法を教えて",
        context_info="機械学習の勉強をしていて、Pythonが好きで、東京のカフェでコーディングするのが趣味です"
    )
    
    # レポート生成
    report = {
        "timestamp": datetime.now().isoformat(),
        "model": runner.baseline.model,
        "conversation_results": result,
        "context_comparison": comparison
    }
    
    # 保存
    report_path = f"baseline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 レポート保存: {report_path}")
    
    return report


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎯 ベースライン比較システム")
    print("="*70)
    print("\n標準的なOllamaチャット（RAG・プロファイル学習なし）")
    print("拡張機能との比較用データを収集します\n")
    
    report = run_baseline_tests()
    
    print("\n" + "="*70)
    print("✅ ベースラインテスト完了")
    print("="*70)