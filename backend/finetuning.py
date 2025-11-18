"""
finetuning.py
LoRAによる軽量ファインチューニングシステム
"""

import os
import json
import sqlite3
from typing import List, Dict
from datetime import datetime
import ollama

class FineTuningSystem:
    """ファインチューニングシステム"""
    
    def __init__(self, db_path: str = "partner_ai.db"):
        self.db_path = db_path
        self.modelfiles_dir = "./modelfiles"
        os.makedirs(self.modelfiles_dir, exist_ok=True)
    
    def prepare_training_data(self, user_id: str, min_conversations: int = 10) -> List[Dict]:
        """
        ユーザーの会話履歴からトレーニングデータを作成
        
        Args:
            user_id: ユーザーID
            min_conversations: 最低必要な会話数
        
        Returns:
            トレーニングデータのリスト
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 評価が高い会話のみを取得（質の高いデータ）
        c.execute("""
            SELECT user_message, ai_response, rating, metadata
            FROM conversations
            WHERE user_id = ? AND (rating >= 4 OR rating IS NULL)
            ORDER BY timestamp DESC
            LIMIT 100
        """, (user_id,))
        
        rows = c.fetchall()
        conn.close()
        
        if len(rows) < min_conversations:
            raise ValueError(
                f"ファインチューニングには最低{min_conversations}件の会話が必要です。"
                f"現在: {len(rows)}件"
            )
        
        training_data = []
        for row in rows:
            user_msg, ai_msg, rating, metadata_str = row
            
            # メタデータから追加情報を取得
            metadata = json.loads(metadata_str) if metadata_str else {}
            
            training_data.append({
                "user": user_msg,
                "assistant": ai_msg,
                "rating": rating,
                "tags": metadata.get("tags", [])
            })
        
        return training_data
    
    def create_modelfile(
        self,
        user_id: str,
        base_model: str = "gemma3:12b",
        temperature: float = 0.7
    ) -> str:
        """
        ユーザー専用のModelfileを作成
        
        Args:
            user_id: ユーザーID
            base_model: ベースモデル
            temperature: 温度パラメータ
        
        Returns:
            Modelfileのパス
        """
        
        # トレーニングデータを取得
        training_data = self.prepare_training_data(user_id)
        
        # ユーザープロファイルを取得
        profile = self._get_user_profile(user_id)
        
        # システムプロンプトを構築
        system_prompt = self._build_personalized_system_prompt(profile, training_data)
        
        # Modelfileの内容を生成
        modelfile_content = f"""FROM {base_model}

# ユーザー専用のパーソナライズされたモデル
# User ID: {user_id}
# Created: {datetime.now().isoformat()}
# Training samples: {len(training_data)}

PARAMETER temperature {temperature}
PARAMETER num_ctx 8192
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1

SYSTEM \"\"\"
{system_prompt}
\"\"\"

# ユーザーの好みに基づくメッセージテンプレート
"""
        
        # 代表的な会話例を追加（Few-shot learning）
        examples = self._select_representative_examples(training_data, n=3)
        for i, example in enumerate(examples, 1):
            modelfile_content += f"\nMESSAGE user \"\"\"{example['user']}\"\"\"\n"
            modelfile_content += f"MESSAGE assistant \"\"\"{example['assistant']}\"\"\"\n"
        
        # Modelfileを保存
        modelfile_path = os.path.join(
            self.modelfiles_dir,
            f"{user_id}_tuned.Modelfile"
        )
        
        with open(modelfile_path, 'w', encoding='utf-8') as f:
            f.write(modelfile_content)
        
        print(f"✅ Modelfile作成完了: {modelfile_path}")
        return modelfile_path
    
    def fine_tune(
        self,
        user_id: str,
        base_model: str = "gemma3:12b"
    ) -> str:
        """
        ファインチューニングを実行
        
        Args:
            user_id: ユーザーID
            base_model: ベースモデル
        
        Returns:
            チューニング済みモデル名
        """
        
        print(f"🎓 {user_id} のファインチューニングを開始...")
        
        # Modelfileを作成
        modelfile_path = self.create_modelfile(user_id, base_model)
        
        # カスタムモデル名
        custom_model_name = f"{user_id}_tuned"
        
        # Ollamaでモデルを作成
        print(f"📦 Ollamaモデルを作成中... (数分かかります)")
        
        try:
            # Modelfileからモデルを作成
            with open(modelfile_path, 'r', encoding='utf-8') as f:
                modelfile_content = f.read()
            
            # ollama create コマンドを実行
            result = ollama.create(
                model=custom_model_name,
                modelfile=modelfile_content
            )
            
            print(f"✅ ファインチューニング完了: {custom_model_name}")
            
            # チューニング情報をDBに保存
            self._save_tuning_info(user_id, custom_model_name, base_model)
            
            return custom_model_name
            
        except Exception as e:
            print(f"❌ ファインチューニングエラー: {e}")
            raise
    
    def _build_personalized_system_prompt(
        self,
        profile: Dict,
        training_data: List[Dict]
    ) -> str:
        """パーソナライズされたシステムプロンプトを構築"""
        
        prompt = "あなたは高度にパーソナライズされたAIアシスタントです。\n"
        prompt += "このモデルは特定のユーザー専用にファインチューニングされています。\n\n"
        
        # 興味・関心
        if profile.get("interests"):
            interests = ", ".join(profile["interests"])
            prompt += f"ユーザーの主な興味: {interests}\n"
        
        # よく使われるタグ
        tag_counts = {}
        for data in training_data:
            for tag in data.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        if tag_counts:
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            tags_str = ", ".join([tag for tag, _ in top_tags])
            prompt += f"よく話すトピック: {tags_str}\n"
        
        # 応答スタイルの分析
        avg_length = sum(len(d["assistant"]) for d in training_data) / len(training_data)
        
        if avg_length > 300:
            prompt += "\n応答スタイル: 詳細で丁寧な説明を好みます。\n"
        elif avg_length < 150:
            prompt += "\n応答スタイル: 簡潔で要点を押さえた説明を好みます。\n"
        else:
            prompt += "\n応答スタイル: バランスの取れた適度な長さの説明を好みます。\n"
        
        # 学習した記憶
        if profile.get("memories"):
            prompt += "\nユーザーについて学習した重要な情報:\n"
            for mem in profile["memories"][-3:]:
                prompt += f"- {mem}\n"
        
        prompt += "\nこれらの情報を考慮して、ユーザーに最適な応答を生成してください。"
        
        return prompt
    
    def _select_representative_examples(
        self,
        training_data: List[Dict],
        n: int = 3
    ) -> List[Dict]:
        """代表的な会話例を選択（Few-shot learning用）"""
        
        # 評価が高く、長さが適度な会話を選択
        scored = []
        for data in training_data:
            score = 0
            
            # 評価が高い
            if data.get("rating") == 5:
                score += 3
            elif data.get("rating") == 4:
                score += 1
            
            # 適度な長さ
            length = len(data["assistant"])
            if 100 < length < 500:
                score += 2
            
            # タグが付いている
            if data.get("tags"):
                score += 1
            
            scored.append((score, data))
        
        # スコアの高い順にソート
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [data for _, data in scored[:n]]
    
    def _get_user_profile(self, user_id: str) -> Dict:
        """ユーザープロファイルを取得"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute(
            "SELECT profile_data FROM user_profiles WHERE user_id = ?",
            (user_id,)
        )
        row = c.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        else:
            return {}
    
    def _save_tuning_info(self, user_id: str, model_name: str, base_model: str):
        """チューニング情報をプロファイルに保存"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        profile = self._get_user_profile(user_id)
        
        if "tuning_history" not in profile:
            profile["tuning_history"] = []
        
        profile["tuning_history"].append({
            "model_name": model_name,
            "base_model": base_model,
            "timestamp": datetime.now().isoformat()
        })
        
        # 最新のチューニング済みモデルを記録
        profile["tuned_model"] = model_name
        
        # 保存
        profile_json = json.dumps(profile, ensure_ascii=False)
        now = datetime.now().isoformat()
        
        c.execute("""
            UPDATE user_profiles
            SET profile_data = ?, updated_at = ?
            WHERE user_id = ?
        """, (profile_json, now, user_id))
        
        if c.rowcount == 0:
            c.execute("""
                INSERT INTO user_profiles (user_id, profile_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, profile_json, now, now))
        
        conn.commit()
        conn.close()
    
    def get_tuned_model(self, user_id: str) -> str | None:
        """ユーザーのチューニング済みモデルを取得"""
        profile = self._get_user_profile(user_id)
        return profile.get("tuned_model")
    
    def list_available_models(self, user_id: str) -> List[Dict]:
        """利用可能なモデル一覧（標準+チューニング済み）"""
        models = []
        
        # 標準モデル
        try:
            result = ollama.list()
            model_list = result.models if hasattr(result, 'models') else []
            
            for m in model_list:
                name = m.model if hasattr(m, 'model') else str(m)
                models.append({
                    "name": name,
                    "type": "standard",
                    "tuned": False
                })
        except:
            pass
        
        # チューニング済みモデル
        tuned_model = self.get_tuned_model(user_id)
        if tuned_model:
            models.append({
                "name": tuned_model,
                "type": "tuned",
                "tuned": True,
                "user_specific": True
            })
        
        return models