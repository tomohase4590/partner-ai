"""
finetuning.py
統合版ファインチューニングシステム
OllamaのModelfileを使ったパーソナライズモデル作成
"""

import os
import json
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import ollama


class FineTuningSystem:
    """ファインチューニングシステム"""
    
    def __init__(self, db_path: str = "partner_ai.db", min_conversations: int = 10):
        self.db_path = db_path
        self.min_conversations = min_conversations
        self.modelfiles_dir = "./modelfiles"
        os.makedirs(self.modelfiles_dir, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # カスタムモデルテーブル
        c.execute("""
            CREATE TABLE IF NOT EXISTS custom_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                base_model TEXT NOT NULL,
                training_size INTEGER,
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                UNIQUE(user_id, model_name)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def collect_training_data(self, user_id: str) -> List[Dict[str, str]]:
        """
        ユーザーの会話履歴を収集
        
        評価が高い（3以上）または未評価の会話を使用
        
        Returns:
            [{"user": "...", "assistant": "...", "rating": ..., "tags": [...]}, ...]
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 高評価または未評価の会話を取得
        c.execute("""
            SELECT user_message, ai_response, rating, metadata
            FROM conversations
            WHERE user_id = ? AND (rating >= 3 OR rating IS NULL)
            ORDER BY timestamp DESC
            LIMIT 100
        """, (user_id,))
        
        rows = c.fetchall()
        conn.close()
        
        training_data = []
        for row in rows:
            user_msg, ai_msg, rating, metadata_json = row
            
            # メタデータから追加情報を取得
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            training_data.append({
                "user": user_msg,
                "assistant": ai_msg,
                "rating": rating,
                "tags": metadata.get("tags", [])
            })
        
        return training_data
    
    def get_user_profile_summary(self, user_id: str) -> Dict:
        """ユーザープロファイルを取得"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT profile_data
            FROM user_profiles
            WHERE user_id = ?
        """, (user_id,))
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            return {}
        
        return json.loads(row[0])
    
    def _build_personalized_system_prompt(
        self,
        user_id: str,
        profile: Dict,
        training_data: List[Dict]
    ) -> str:
        """パーソナライズされたシステムプロンプトを構築"""
        
        prompt = f"あなたは{user_id}さん専用にカスタマイズされたAIアシスタントです。\n\n"
        
        # ユーザープロファイル情報
        prompt += "【ユーザープロファイル】\n"
        
        # 興味・関心
        if profile.get("interests"):
            interests = ", ".join(profile["interests"][:5])
            prompt += f"主な興味: {interests}\n"
        
        # 好みのトーン
        if profile.get("preferred_tone"):
            prompt += f"好みのトーン: {profile['preferred_tone']}\n"
        
        # よく話すトピック（タグから分析）
        tag_counts = {}
        for data in training_data:
            for tag in data.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        if tag_counts:
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            tags_str = ", ".join([tag for tag, _ in top_tags])
            prompt += f"よく話すトピック: {tags_str}\n"
        
        # 応答スタイルの分析
        if training_data:
            avg_length = sum(len(d["assistant"]) for d in training_data) / len(training_data)
            
            if avg_length > 300:
                prompt += "好みの応答スタイル: 詳細で丁寧な説明\n"
            elif avg_length < 150:
                prompt += "好みの応答スタイル: 簡潔で要点を押さえた説明\n"
            else:
                prompt += "好みの応答スタイル: バランスの取れた適度な長さ\n"
        
        # 学習した記憶
        if profile.get("memories"):
            prompt += "\n学習した重要な情報:\n"
            for mem in profile["memories"][-5:]:
                prompt += f"- {mem}\n"
        
        # 会話例の追加
        prompt += "\n\n【高評価だった会話例】\n"
        prompt += "以下のような会話スタイルを参考にしてください:\n\n"
        
        # 代表的な会話例を選択
        examples = self._select_representative_examples(training_data, n=5)
        for i, ex in enumerate(examples, 1):
            prompt += f"例{i}:\n"
            prompt += f"ユーザー: {ex['user'][:100]}{'...' if len(ex['user']) > 100 else ''}\n"
            prompt += f"あなた: {ex['assistant'][:150]}{'...' if len(ex['assistant']) > 150 else ''}\n\n"
        
        # 応答の指針
        prompt += """
【応答の指針】
- 上記の会話例のトーンとスタイルを参考にする
- ユーザーの興味や好みを常に考慮する
- 学習した情報を自然に活用する
- 簡潔さと詳しさのバランスを保つ
- 必要に応じて具体例や説明を追加する
"""
        
        return prompt
    
    def _select_representative_examples(
        self,
        training_data: List[Dict],
        n: int = 5
    ) -> List[Dict]:
        """代表的な会話例を選択（Few-shot learning用）"""
        
        # 評価が高く、長さが適度な会話を選択
        scored = []
        for data in training_data:
            score = 0
            
            # 評価が高い
            rating = data.get("rating")
            if rating == 5:
                score += 3
            elif rating == 4:
                score += 2
            elif rating == 3:
                score += 1
            
            # 適度な長さ（100〜500文字）
            length = len(data["assistant"])
            if 100 < length < 500:
                score += 2
            elif 50 < length <= 100 or 500 <= length < 800:
                score += 1
            
            # タグが付いている
            if data.get("tags"):
                score += 1
            
            # 質問形式の会話を優先
            if "?" in data["user"] or "？" in data["user"]:
                score += 1
            
            scored.append((score, data))
        
        # スコアの高い順にソート
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [data for _, data in scored[:n]]
    
    def create_modelfile(
        self,
        user_id: str,
        base_model: str = "qwen2.5:32b",
        training_data: Optional[List[Dict]] = None
    ) -> str:
        """
        Modelfileを生成
        
        Args:
            user_id: ユーザーID
            base_model: ベースモデル
            training_data: トレーニングデータ（Noneの場合は自動取得）
        
        Returns:
            Modelfileの内容（文字列）
        """
        
        # トレーニングデータ取得
        if training_data is None:
            training_data = self.collect_training_data(user_id)
        
        # プロファイル取得
        profile = self.get_user_profile_summary(user_id)
        
        # システムプロンプト構築
        system_prompt = self._build_personalized_system_prompt(
            user_id, profile, training_data
        )
        
        # システムプロンプトのエスケープ処理
        system_prompt_escaped = system_prompt.replace('"""', r'\"\"\"')
        
        # Modelfileの内容を生成
        modelfile_content = f"""FROM {base_model}

# ユーザー専用カスタムモデル
# User: {user_id}
# Created: {datetime.now().isoformat()}
# Training samples: {len(training_data)}
# Base model: {base_model}

SYSTEM \"\"\"{system_prompt_escaped}\"\"\"

PARAMETER temperature 0.8
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 8192
PARAMETER repeat_penalty 1.1

PARAMETER stop "<|im_end|>"
PARAMETER stop "</s>"
"""
        
        # Few-shot examplesを追加
        examples = self._select_representative_examples(training_data, n=3)
        if examples:
            modelfile_content += "\n# Few-shot examples\n"
            for example in examples:
                # エスケープ処理
                user_text = example['user'].replace('"""', r'\"\"\"').replace('\n', ' ')
                assistant_text = example['assistant'].replace('"""', r'\"\"\"').replace('\n', ' ')
                
                # 長さ制限
                user_text = user_text[:200]
                assistant_text = assistant_text[:300]
                
                modelfile_content += f'MESSAGE user \"\"\"{user_text}\"\"\"\n'
                modelfile_content += f'MESSAGE assistant \"\"\"{assistant_text}\"\"\"\n'
        
        return modelfile_content
    
    def fine_tune(
        self,
        user_id: str,
        base_model: str = "qwen2.5:32b"
    ) -> str:
        """
        ファインチューニングを実行
        
        Args:
            user_id: ユーザーID
            base_model: ベースモデル
        
        Returns:
            作成されたモデル名
        """
        
        print(f"🔧 ファインチューニング開始: {user_id}")
        
        # 1. トレーニングデータ収集
        training_data = self.collect_training_data(user_id)
        
        if len(training_data) < self.min_conversations:
            raise ValueError(
                f"会話データが不足しています。"
                f"最低{self.min_conversations}件必要ですが、{len(training_data)}件しかありません。"
            )
        
        print(f"✅ トレーニングデータ: {len(training_data)}件")
        
        # 2. Modelfile作成
        modelfile_content = self.create_modelfile(user_id, base_model, training_data)
        
        # Modelfileを保存（デバッグ用 + コマンド実行用）
        modelfile_path = os.path.join(
            self.modelfiles_dir,
            f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.Modelfile"
        )
        with open(modelfile_path, 'w', encoding='utf-8') as f:
            f.write(modelfile_content)
        print(f"✅ Modelfile保存: {modelfile_path}")
        
        # 3. カスタムモデル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"{user_id}_custom_{timestamp}"
        
        try:
            # 4. Ollamaでモデル作成
            print(f"🚀 モデル作成中: {model_name}")
            print("   (数分かかる場合があります...)")
            
            # デバッグ: Modelfileの内容を確認
            print(f"   Modelfile先頭200文字: {modelfile_content[:200]}")
            
            # ollama.create()を使用（path指定で読み込み）
            # 一時ファイルから読み込ませる方法に変更
            import subprocess
            
            result = subprocess.run(
                ["ollama", "create", model_name, "-f", modelfile_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"モデル作成失敗: {result.stderr}")
            
            # 結果を確認
            print(f"   作成結果: {result.stdout}")
            print(f"✅ モデル作成完了: {model_name}")
            
            # 5. メタデータを保存
            self._save_model_metadata(
                user_id, model_name, base_model, len(training_data)
            )
            
            return model_name
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("モデル作成がタイムアウトしました")
        except Exception as e:
            print(f"❌ モデル作成エラー: {e}")
            print(f"デバッグ情報: Modelfile内容の最初の200文字:")
            print(modelfile_content[:200])
            raise RuntimeError(f"モデル作成エラー: {str(e)}")
    
    def _save_model_metadata(
        self,
        user_id: str,
        model_name: str,
        base_model: str,
        training_size: int
    ):
        """カスタムモデルのメタデータを保存"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 既存のモデルを非アクティブに
        c.execute("""
            UPDATE custom_models
            SET is_active = 0
            WHERE user_id = ? AND is_active = 1
        """, (user_id,))
        
        # 新しいモデルを保存
        c.execute("""
            INSERT OR REPLACE INTO custom_models
            (user_id, model_name, base_model, training_size, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            user_id,
            model_name,
            base_model,
            training_size,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ メタデータ保存完了")
    
    def get_active_model(self, user_id: str) -> Optional[str]:
        """ユーザーのアクティブなカスタムモデルを取得"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT model_name
            FROM custom_models
            WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        row = c.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    def list_user_models(self, user_id: str) -> List[Dict]:
        """ユーザーが作成したモデル一覧"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT model_name, base_model, training_size, created_at, is_active
            FROM custom_models
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        
        rows = c.fetchall()
        conn.close()
        
        models = []
        for row in rows:
            models.append({
                "model_name": row[0],
                "base_model": row[1],
                "training_size": row[2],
                "created_at": row[3],
                "is_active": bool(row[4])
            })
        
        return models
    
    def delete_model(self, user_id: str, model_name: str):
        """カスタムモデルを削除"""
        try:
            # Ollamaからモデル削除
            print(f"🗑️ Ollamaからモデル削除中: {model_name}")
            ollama.delete(model_name)
            
            # データベースから削除
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute("""
                DELETE FROM custom_models
                WHERE user_id = ? AND model_name = ?
            """, (user_id, model_name))
            
            conn.commit()
            conn.close()
            
            print(f"✅ モデル削除完了: {model_name}")
            
        except Exception as e:
            print(f"❌ モデル削除エラー: {e}")
            raise RuntimeError(f"モデル削除エラー: {str(e)}")
    
    def evaluate_model(
        self,
        model_name: str,
        test_prompts: Optional[List[str]] = None
    ) -> Dict:
        """
        カスタムモデルを評価
        
        Args:
            model_name: 評価するモデル名
            test_prompts: テスト用のプロンプト
        
        Returns:
            評価結果
        """
        
        if test_prompts is None:
            test_prompts = [
                "こんにちは",
                "今日の調子はどう？",
                "何か面白い話ある？",
                "おすすめの本を教えて"
            ]
        
        results = []
        
        for prompt in test_prompts:
            try:
                response = ollama.chat(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                results.append({
                    "prompt": prompt,
                    "response": response['message']['content'],
                    "success": True
                })
                
            except Exception as e:
                results.append({
                    "prompt": prompt,
                    "error": str(e),
                    "success": False
                })
        
        success_count = sum(1 for r in results if r["success"])
        success_rate = success_count / len(results) if results else 0
        
        return {
            "model_name": model_name,
            "success_rate": success_rate,
            "total_tests": len(results),
            "successful_tests": success_count,
            "results": results
        }
    
    def get_tuning_readiness(self, user_id: str) -> Dict:
        """
        ファインチューニングの準備状況をチェック
        
        Returns:
            準備状況の詳細情報
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 総会話数
        c.execute("""
            SELECT COUNT(*) FROM conversations WHERE user_id = ?
        """, (user_id,))
        total_count = c.fetchone()[0]
        
        # 高評価数
        c.execute("""
            SELECT COUNT(*) FROM conversations
            WHERE user_id = ? AND rating >= 3
        """, (user_id,))
        high_rated_count = c.fetchone()[0]
        
        conn.close()
        
        # 使用可能なデータ数
        training_data = self.collect_training_data(user_id)
        usable_count = len(training_data)
        
        ready = usable_count >= self.min_conversations
        progress = min(100, (usable_count / self.min_conversations) * 100)
        
        return {
            "ready": ready,
            "total_conversations": total_count,
            "high_rated_conversations": high_rated_count,
            "usable_for_training": usable_count,
            "required": self.min_conversations,
            "progress_percentage": round(progress, 1)
        }


# ==================== 使用例 ====================

if __name__ == "__main__":
    # システム初期化
    tuning_system = FineTuningSystem(min_conversations=10)
    
    # ファインチューニング実行
    user_id = "test_user"
    
    try:
        # 準備状況チェック
        readiness = tuning_system.get_tuning_readiness(user_id)
        print(f"\n📊 準備状況:")
        print(f"   使用可能データ: {readiness['usable_for_training']} / {readiness['required']}")
        print(f"   進捗: {readiness['progress_percentage']}%")
        
        if not readiness['ready']:
            print(f"\n⚠️ データ不足: あと{readiness['required'] - readiness['usable_for_training']}件必要")
        else:
            # ファインチューニング実行
            model_name = tuning_system.fine_tune(
                user_id=user_id,
                base_model="gemma3:4b"  # 軽量モデルで試す
            )
            
            print(f"\n✅ カスタムモデル作成完了: {model_name}")
            
            # テスト評価
            evaluation = tuning_system.evaluate_model(model_name)
            print(f"\n📊 評価結果:")
            print(f"   成功率: {evaluation['success_rate']*100:.1f}%")
            print(f"   成功: {evaluation['successful_tests']}/{evaluation['total_tests']}")
            
            # 結果表示
            for result in evaluation['results']:
                if result['success']:
                    print(f"\nQ: {result['prompt']}")
                    print(f"A: {result['response'][:100]}...")
        
    except ValueError as e:
        print(f"\n❌ エラー: {e}")
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()