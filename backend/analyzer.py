"""
analyzer.py
会話を分析してユーザープロファイルを更新
"""

import ollama
import json
import re
from typing import Dict, List

class ConversationAnalyzer:
    """会話分析クラス"""
    
    def __init__(self, model: str = "gemma3:4b"):
        self.model = model
    
    def analyze_conversation(
        self, 
        user_message: str, 
        ai_response: str
    ) -> Dict:
        """
        会話を分析して構造化データを返す
        
        Returns:
            {
                "topics": ["Python", "AI"],
                "emotion": "curious",
                "intent": "question",
                "key_info": "ユーザーはPythonに興味がある"
            }
        """
        
        prompt = f"""以下の会話を分析してください。

ユーザー: {user_message}
AI: {ai_response}

以下のJSON形式で返してください（JSONのみ、他の文字は含めない）:
{{
  "topics": ["トピック1", "トピック2"],
  "emotion": "happy/curious/neutral/frustrated",
  "intent": "question/chat/request/feedback",
  "key_info": "ユーザーについて学習した重要な情報（1文で）"
}}
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3}
            )
            
            content = response['message']['content']
            
            # JSONを抽出（```json ... ``` で囲まれている場合に対応）
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                return result
            else:
                return self._get_default_analysis()
                
        except Exception as e:
            print(f"⚠️ 分析エラー: {e}")
            return self._get_default_analysis()
    
    def _get_default_analysis(self) -> Dict:
        """デフォルト分析結果"""
        return {
            "topics": [],
            "emotion": "neutral",
            "intent": "chat",
            "key_info": ""
        }
    
    def extract_topics_simple(self, text: str) -> List[str]:
        """簡易的なトピック抽出（キーワードマッチング）"""
        keywords = [
            'Python', 'JavaScript', 'Java', 'C++', 'Go', 'Rust',
            'React', 'Vue', 'Angular', 'Next.js',
            'AI', '機械学習', 'ディープラーニング', 'ChatGPT',
            'Web開発', 'アプリ開発', 'ゲーム開発',
            'データベース', 'SQL', 'NoSQL',
            'Docker', 'Kubernetes', 'AWS', 'Azure',
            'アルゴリズム', 'データ構造',
            'プログラミング', '開発', 'エンジニアリング'
        ]
        
        found_topics = []
        text_lower = text.lower()
        
        for keyword in keywords:
            if keyword.lower() in text_lower or keyword in text:
                found_topics.append(keyword)
        
        return found_topics[:5]  # 最大5個まで


class ProfileManager:
    """ユーザープロファイル管理"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def get_profile(self, user_id: str) -> Dict:
        """プロファイル取得"""
        c = self.conn.cursor()
        c.execute(
            "SELECT profile_data FROM user_profiles WHERE user_id = ?",
            (user_id,)
        )
        row = c.fetchone()
        
        if row:
            return json.loads(row[0])
        else:
            return self._create_default_profile()
    
    def _create_default_profile(self) -> Dict:
        """デフォルトプロファイル"""
        return {
            "tone": "friendly",
            "interests": [],
            "preferences": [],
            "memories": [],
            "topic_counts": {},
            "total_conversations": 0
        }
    
    def update_profile(self, user_id: str, analysis: Dict):
        """
        分析結果に基づいてプロファイルを更新
        
        Args:
            user_id: ユーザーID
            analysis: 会話分析結果
        """
        profile = self.get_profile(user_id)
        
        # トピックカウントを更新
        for topic in analysis.get("topics", []):
            if topic:
                profile["topic_counts"][topic] = profile["topic_counts"].get(topic, 0) + 1
        
        # 上位3つを interests に設定
        if profile["topic_counts"]:
            sorted_topics = sorted(
                profile["topic_counts"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            profile["interests"] = [t[0] for t in sorted_topics[:3]]
        
        # 重要な情報を memories に追加
        key_info = analysis.get("key_info", "").strip()
        if key_info and len(key_info) > 10:
            # 重複チェック
            if key_info not in profile["memories"]:
                profile["memories"].append(key_info)
                # 最新10件まで保持
                profile["memories"] = profile["memories"][-10:]
        
        # 会話数をインクリメント
        profile["total_conversations"] = profile.get("total_conversations", 0) + 1
        
        # DBに保存
        self._save_profile(user_id, profile)
        
        return profile
    
    def _save_profile(self, user_id: str, profile: Dict):
        """プロファイルをDBに保存"""
        from datetime import datetime
        
        c = self.conn.cursor()
        
        # 既存チェック
        c.execute(
            "SELECT user_id FROM user_profiles WHERE user_id = ?",
            (user_id,)
        )
        exists = c.fetchone()
        
        profile_json = json.dumps(profile, ensure_ascii=False)
        now = datetime.now().isoformat()
        
        if exists:
            c.execute("""
                UPDATE user_profiles
                SET profile_data = ?, updated_at = ?
                WHERE user_id = ?
            """, (profile_json, now, user_id))
        else:
            c.execute("""
                INSERT INTO user_profiles (user_id, profile_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, profile_json, now, now))
        
        self.conn.commit()
    
    def get_personalized_system_prompt(self, user_id: str) -> str:
        """パーソナライズされたシステムプロンプトを生成"""
        profile = self.get_profile(user_id)
        
        prompt = "あなたは親しみやすく、有能なAIアシスタントです。\n"
        
        # 興味・関心を追加
        if profile.get("interests"):
            interests = ", ".join(profile["interests"])
            prompt += f"\nユーザーは以下のトピックに興味があります: {interests}\n"
        
        # 学習した記憶を追加
        if profile.get("memories"):
            prompt += "\nユーザーについて学習した情報:\n"
            for mem in profile["memories"][-3:]:  # 最新3件
                prompt += f"- {mem}\n"
        
        # 好みを追加
        if profile.get("preferences"):
            prompt += "\nユーザーの好み:\n"
            for pref in profile["preferences"]:
                prompt += f"- {pref}\n"
        
        return prompt
    
class EmotionDetector:
    """感情・心理状態の検出"""
    
    def detect_emotion_details(self, user_message: str, conversation_history: List[Dict]) -> Dict:
        """
        深い感情分析
        - 表面的な感情(happy/sad)だけでなく
        - 期待、不安、疲労、興奮などの微細な感情
        - 会話の文脈から推測される心理状態
        """
        
        prompt = f"""以下のユーザーメッセージと会話履歴から、ユーザーの感情と心理状態を分析してください。

現在のメッセージ: {user_message}

最近の会話履歴:
{self._format_history(conversation_history)}

以下のJSON形式で返してください:
{{
  "primary_emotion": "happy/sad/anxious/excited/tired/frustrated/curious/neutral",
  "emotion_intensity": 1-10,
  "underlying_needs": ["承認", "サポート", "情報", "共感"],
  "preferred_response_style": "励まし/具体的アドバイス/共感/簡潔な回答",
  "energy_level": "high/medium/low",
  "conversation_goal": "雑談/問題解決/学習/愚痴"
}}
"""