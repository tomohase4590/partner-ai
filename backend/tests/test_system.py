"""
統合テストシステム
RAG、プロファイル学習、ファインチューニングの効果を検証
"""

import os
import sys
import sqlite3
import json
import shutil
from datetime import datetime
from typing import List, Dict
import ollama

# パスを追加（backend/ディレクトリを参照）
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from analyzer import ConversationAnalyzer, ProfileManager
from rag_system import RAGSystem
from finetuning import FineTuningSystem


class TestSystem:
    """テストシステム"""
    
    def __init__(self, test_db: str = "test_partner_ai.db"):
        self.test_db = test_db
        self.chroma_test_dir = "./test_chroma_db"
        self.user_id = "test_user_001"
        self.base_model = "gemma3:4b"  # テスト用に軽量モデル
        
    def reset_database(self):
        """データベースを完全リセット"""
        print("\n" + "="*60)
        print("🗑️  データベースリセット")
        print("="*60)
        
        # DBファイル削除
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            print(f"✅ {self.test_db} を削除")
        
        # ChromaDB削除
        if os.path.exists(self.chroma_test_dir):
            shutil.rmtree(self.chroma_test_dir)
            print(f"✅ {self.chroma_test_dir} を削除")
        
        # 初期化
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        
        # テーブル作成
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                model_used TEXT,
                rating INTEGER,
                tags TEXT,
                metadata TEXT
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ 新しいデータベースを初期化")
    
    def generate_test_conversations(self) -> List[Dict]:
        """テスト用の会話データを生成"""
        conversations = [
            # 趣味・興味の学習
            {
                "user": "最近、機械学習の勉強を始めたんだ",
                "rating": 5,
                "category": "interest"
            },
            {
                "user": "PythonでNeuralNetworkを実装したいんだけど",
                "rating": 4,
                "category": "interest"
            },
            {
                "user": "ディープラーニングの本でおすすめある？",
                "rating": 5,
                "category": "interest"
            },
            
            # 個人情報の学習
            {
                "user": "東京で働いているエンジニアなんだ",
                "rating": 5,
                "category": "personal"
            },
            {
                "user": "週末はカフェでコーディングするのが好き",
                "rating": 4,
                "category": "personal"
            },
            
            # 技術的な質問
            {
                "user": "Transformerアーキテクチャについて教えて",
                "rating": 5,
                "category": "technical"
            },
            {
                "user": "AttentionメカニズムはどうやってSelf-attentionと違うの？",
                "rating": 4,
                "category": "technical"
            },
            {
                "user": "BERTとGPTの違いを簡単に説明して",
                "rating": 5,
                "category": "technical"
            },
            
            # 追加の会話（ファインチューニング用に10件以上必要）
            {
                "user": "PyTorchとTensorFlowどっちがいい？",
                "rating": 4,
                "category": "technical"
            },
            {
                "user": "機械学習のプロジェクトで詰まってるんだけど",
                "rating": 5,
                "category": "technical"
            },
            {
                "user": "データの前処理で気をつけることは？",
                "rating": 4,
                "category": "technical"
            },
            {
                "user": "過学習を防ぐ方法を教えて",
                "rating": 5,
                "category": "technical"
            },
            {
                "user": "ハイパーパラメータのチューニング方法は？",
                "rating": 4,
                "category": "technical"
            },
            {
                "user": "モデルの評価指標について詳しく知りたい",
                "rating": 5,
                "category": "technical"
            },
            {
                "user": "強化学習にも興味があるんだ",
                "rating": 4,
                "category": "interest"
            },
        ]
        
        return conversations
    
    def run_baseline_test(self, test_query: str) -> str:
        """ベースライン（機能なし）でのテスト"""
        print("\n" + "="*60)
        print("📊 ベースライン測定（RAG/プロファイルなし）")
        print("="*60)
        
        messages = [
            {"role": "system", "content": "あなたは親しみやすく、有能なAIアシスタントです。"},
            {"role": "user", "content": test_query}
        ]
        
        response = ollama.chat(
            model=self.base_model,
            messages=messages
        )
        
        result = response['message']['content']
        print(f"\nクエリ: {test_query}")
        print(f"\n応答:\n{result}\n")
        
        return result
    
    def run_enhanced_test(self, conversations: List[Dict], test_query: str) -> Dict:
        """拡張機能（RAG + プロファイル）でのテスト"""
        print("\n" + "="*60)
        print("🚀 拡張機能テスト（RAG + プロファイル学習）")
        print("="*60)
        
        # システム初期化
        analyzer = ConversationAnalyzer(model=self.base_model)
        rag_system = RAGSystem(persist_directory=self.chroma_test_dir)
        
        conn = sqlite3.connect(self.test_db)
        profile_manager = ProfileManager(conn)
        
        print(f"\n📝 {len(conversations)}件の会話を学習中...")
        
        # 会話を処理
        for i, conv in enumerate(conversations, 1):
            print(f"  処理中: {i}/{len(conversations)} - {conv['user'][:50]}...")
            
            # AI応答を生成
            messages = [
                {"role": "system", "content": "あなたは親しみやすく、有能なAIアシスタントです。"},
                {"role": "user", "content": conv['user']}
            ]
            
            response = ollama.chat(model=self.base_model, messages=messages)
            ai_response = response['message']['content']
            
            # 会話をDBに保存
            c = conn.cursor()
            timestamp = datetime.now().isoformat()
            metadata = {"category": conv.get("category", "general")}
            
            c.execute("""
                INSERT INTO conversations 
                (user_id, timestamp, user_message, ai_response, model_used, rating, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.user_id, timestamp, conv['user'], ai_response,
                self.base_model, conv.get('rating'), json.dumps(metadata)
            ))
            
            conv_id = c.lastrowid
            conn.commit()
            
            # RAGに追加
            rag_system.add_memory(
                user_id=self.user_id,
                conversation_id=conv_id,
                user_message=conv['user'],
                ai_response=ai_response,
                metadata=metadata
            )
            
            # プロファイル更新
            try:
                analysis = analyzer.analyze_conversation(conv['user'], ai_response)
                profile_manager.update_profile(self.user_id, analysis)
            except:
                pass
        
        print("✅ 学習完了")
        
        # プロファイル取得
        profile = profile_manager.get_profile(self.user_id)
        print(f"\n📊 学習したプロファイル:")
        print(f"  興味: {profile.get('interests', [])[:5]}")
        print(f"  記憶: {len(profile.get('memories', []))}件")
        
        # RAGで関連記憶を検索
        relevant_memories = rag_system.search_relevant_memories(
            user_id=self.user_id,
            query=test_query,
            n_results=3
        )
        
        print(f"\n🔍 関連する記憶: {len(relevant_memories)}件")
        for mem in relevant_memories:
            print(f"  - {mem['user_message'][:60]}...")
        
        # システムプロンプト構築
        system_prompt = "あなたは親しみやすく、有能なAIアシスタントです。\n"
        
        if profile.get('interests'):
            interests = ", ".join(profile['interests'][:3])
            system_prompt += f"\nユーザーの興味: {interests}\n"
        
        if relevant_memories:
            system_prompt += "\n過去の関連する会話:\n"
            for mem in relevant_memories:
                system_prompt += f"- {mem['user_message'][:80]}\n"
        
        # 応答生成
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": test_query}
        ]
        
        response = ollama.chat(model=self.base_model, messages=messages)
        result = response['message']['content']
        
        print(f"\nクエリ: {test_query}")
        print(f"\n応答:\n{result}\n")
        
        conn.close()
        
        return {
            "response": result,
            "profile": profile,
            "relevant_memories": relevant_memories,
            "system_prompt": system_prompt
        }
    
    def run_finetuning_test(self) -> Dict:
        """ファインチューニングのテスト"""
        print("\n" + "="*60)
        print("🎓 ファインチューニングテスト")
        print("="*60)
        
        tuning_system = FineTuningSystem(
            db_path=self.test_db,
            min_conversations=10
        )
        
        # 準備状況確認
        readiness = tuning_system.get_tuning_readiness(self.user_id)
        print(f"\n📊 準備状況:")
        print(f"  総会話数: {readiness['total_conversations']}")
        print(f"  高評価会話: {readiness['high_rated_conversations']}")
        print(f"  使用可能: {readiness['usable_for_training']}")
        print(f"  必要数: {readiness['required']}")
        print(f"  進捗: {readiness['progress_percentage']:.1f}%")
        
        if not readiness['ready']:
            print("\n⚠️ データ不足のためファインチューニングをスキップ")
            return {
                "status": "skipped",
                "reason": "insufficient_data",
                "readiness": readiness
            }
        
        # ファインチューニング実行
        print(f"\n🚀 ファインチューニング開始...")
        print(f"  ベースモデル: {self.base_model}")
        
        try:
            model_name = tuning_system.fine_tune(
                user_id=self.user_id,
                base_model=self.base_model
            )
            
            print(f"\n✅ カスタムモデル作成完了: {model_name}")
            
            # テスト評価
            test_prompts = [
                "機械学習について教えて",
                "Pythonのコードを書くのが好き？",
                "東京でおすすめのカフェは？"
            ]
            
            print(f"\n🧪 モデル評価中...")
            evaluation = tuning_system.evaluate_model(model_name, test_prompts)
            
            print(f"\n📊 評価結果:")
            print(f"  成功率: {evaluation['success_rate']*100:.1f}%")
            print(f"  成功: {evaluation['successful_tests']}/{evaluation['total_tests']}")
            
            for result in evaluation['results']:
                if result['success']:
                    print(f"\n  Q: {result['prompt']}")
                    print(f"  A: {result['response'][:100]}...")
            
            return {
                "status": "success",
                "model_name": model_name,
                "evaluation": evaluation,
                "readiness": readiness
            }
            
        except Exception as e:
            print(f"\n❌ ファインチューニングエラー: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "status": "error",
                "error": str(e),
                "readiness": readiness
            }
    
    def run_comparison_test(self, test_query: str):
        """比較テストの実行"""
        print("\n" + "="*70)
        print("🔬 比較テスト開始")
        print("="*70)
        print(f"\nテストクエリ: {test_query}")
        
        # データベースリセット
        self.reset_database()
        
        # テストデータ生成
        conversations = self.generate_test_conversations()
        
        # 1. ベースライン測定
        baseline_response = self.run_baseline_test(test_query)
        
        # 2. 拡張機能テスト
        enhanced_result = self.run_enhanced_test(conversations, test_query)
        
        # 3. ファインチューニングテスト
        finetuning_result = self.run_finetuning_test()
        
        # 結果まとめ
        print("\n" + "="*70)
        print("📋 テスト結果サマリー")
        print("="*70)
        
        print(f"\n1️⃣  ベースライン（標準モデル）")
        print(f"   応答長: {len(baseline_response)}文字")
        
        print(f"\n2️⃣  拡張機能（RAG + プロファイル）")
        print(f"   応答長: {len(enhanced_result['response'])}文字")
        print(f"   学習した興味: {len(enhanced_result['profile'].get('interests', []))}件")
        print(f"   参照した記憶: {len(enhanced_result['relevant_memories'])}件")
        
        print(f"\n3️⃣  ファインチューニング")
        if finetuning_result['status'] == 'success':
            print(f"   モデル名: {finetuning_result['model_name']}")
            print(f"   評価成功率: {finetuning_result['evaluation']['success_rate']*100:.1f}%")
        else:
            print(f"   ステータス: {finetuning_result['status']}")
            if finetuning_result.get('reason'):
                print(f"   理由: {finetuning_result['reason']}")
        
        # レポート保存
        report = {
            "test_query": test_query,
            "timestamp": datetime.now().isoformat(),
            "baseline": {
                "response": baseline_response,
                "length": len(baseline_response)
            },
            "enhanced": {
                "response": enhanced_result['response'],
                "length": len(enhanced_result['response']),
                "interests_learned": enhanced_result['profile'].get('interests', []),
                "memories_count": len(enhanced_result.get('relevant_memories', [])),
                "system_prompt": enhanced_result['system_prompt']
            },
            "finetuning": finetuning_result
        }
        
        report_path = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 詳細レポート保存: {report_path}")
        print("\n" + "="*70)
        print("✅ テスト完了")
        print("="*70)
        
        return report


# ==================== メイン実行 ====================

if __name__ == "__main__":
    test_system = TestSystem()
    
    # テストクエリ
    test_queries = [
        "機械学習の勉強方法でおすすめを教えて",
        "私の趣味に合ったプロジェクトのアイデアある？",
        "Python機械学習ライブラリについて教えて"
    ]
    
    # 各クエリでテスト実行
    for query in test_queries:
        print(f"\n\n{'='*70}")
        print(f"🎯 テストケース: {query}")
        print(f"{'='*70}")
        
        test_system.run_comparison_test(query)
        
        # 次のテストまで少し待機
        input("\n⏸️  Enterキーを押して次のテストへ...")