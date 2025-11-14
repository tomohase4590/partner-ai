"""
rag_system.py
RAG（Retrieval-Augmented Generation）システム
ベクトル検索による長期記憶
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import json
from datetime import datetime

class RAGSystem:
    """RAGシステム - ベクトル検索による長期記憶"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        # ChromaDB初期化
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # コレクション作成（既存の場合は取得）
        try:
            self.collection = self.client.get_collection("user_memories")
        except:
            self.collection = self.client.create_collection(
                name="user_memories",
                metadata={"description": "User conversation memories"}
            )
        
        # 埋め込みモデル（軽量で高性能な日本語対応モデル）
        print("📦 埋め込みモデルをロード中...")
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print("✅ 埋め込みモデルロード完了")
    
    def add_memory(
        self,
        user_id: str,
        conversation_id: int,
        user_message: str,
        ai_response: str,
        metadata: Dict = None
    ):
        """会話を記憶に追加"""
        
        # 埋め込みベクトル生成
        combined_text = f"User: {user_message}\nAI: {ai_response}"
        embedding = self.embedding_model.encode(combined_text).tolist()
        
        # メタデータ準備
        meta = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message[:500],  # 長すぎる場合は切り詰め
            "ai_response": ai_response[:500]
        }
        
        if metadata:
            # リスト型のメタデータをJSON文字列に変換
            for key, value in metadata.items():
                if isinstance(value, list):
                    meta[key] = json.dumps(value, ensure_ascii=False)
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    meta[key] = value
                # その他の型は無視（辞書など）
        
        # ChromaDBに追加
        doc_id = f"{user_id}_{conversation_id}"
        
        try:
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[combined_text],
                metadatas=[meta]
            )
            print(f"✅ 記憶追加: {doc_id}")
        except Exception as e:
            print(f"⚠️ 記憶追加エラー: {e}")
            import traceback
            traceback.print_exc()
    
    def search_relevant_memories(
        self,
        user_id: str,
        query: str,
        n_results: int = 5
    ) -> List[Dict]:
        """関連する記憶を検索"""
        
        # クエリの埋め込み
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # 検索実行
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"user_id": user_id}
            )
            
            # 結果を整形
            memories = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    meta = results['metadatas'][0][i]
                    memories.append({
                        "content": doc,
                        "user_message": meta.get("user_message", ""),
                        "ai_response": meta.get("ai_response", ""),
                        "timestamp": meta.get("timestamp", ""),
                        "conversation_id": meta.get("conversation_id", 0),
                        "distance": results['distances'][0][i] if 'distances' in results else 0
                    })
            
            return memories
            
        except Exception as e:
            print(f"⚠️ 記憶検索エラー: {e}")
            return []
    
    def get_memory_count(self, user_id: str) -> int:
        """ユーザーの記憶数を取得"""
        try:
            results = self.collection.get(
                where={"user_id": user_id}
            )
            return len(results['ids']) if results['ids'] else 0
        except:
            return 0


class SelfImprovementSystem:
    """自己改良システム"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def analyze_feedback(self, user_id: str) -> Dict:
        """フィードバックを分析して改善点を抽出"""
        
        c = self.conn.cursor()
        
        # 低評価の会話を取得
        c.execute("""
            SELECT id, user_message, ai_response, metadata
            FROM conversations
            WHERE user_id = ? AND rating = 1
            ORDER BY timestamp DESC
            LIMIT 10
        """, (user_id,))
        
        bad_conversations = c.fetchall()
        
        # 高評価の会話を取得
        c.execute("""
            SELECT id, user_message, ai_response, metadata
            FROM conversations
            WHERE user_id = ? AND rating = 5
            ORDER BY timestamp DESC
            LIMIT 10
        """, (user_id,))
        
        good_conversations = c.fetchall()
        
        # パターン分析
        improvements = {
            "bad_patterns": [],
            "good_patterns": [],
            "suggestions": []
        }
        
        # 低評価のパターン抽出
        for conv in bad_conversations:
            metadata = json.loads(conv[3]) if conv[3] else {}
            comment = metadata.get("feedback_comment", "")
            
            if comment:
                improvements["bad_patterns"].append({
                    "conversation_id": conv[0],
                    "issue": comment,
                    "user_message": conv[1][:100]
                })
        
        # 改善提案生成
        if len(bad_conversations) > 0:
            improvements["suggestions"].append("低評価の会話が増えています。応答スタイルを見直しましょう。")
        
        if len(good_conversations) > len(bad_conversations) * 2:
            improvements["suggestions"].append("高評価が多く、良いパフォーマンスです！")
        
        return improvements
    
    def apply_improvements(self, user_id: str, improvements: Dict):
        """改善を適用（プロファイルに記録）"""
        
        c = self.conn.cursor()
        
        # 現在のプロファイル取得
        c.execute("SELECT profile_data FROM user_profiles WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        
        if row:
            profile = json.loads(row[0])
        else:
            profile = {
                "tone": "friendly",
                "interests": [],
                "preferences": [],
                "memories": [],
                "improvements": []
            }
        
        # 改善履歴を追加
        if "improvements" not in profile:
            profile["improvements"] = []
        
        improvement_entry = {
            "timestamp": datetime.now().isoformat(),
            "suggestions": improvements.get("suggestions", []),
            "bad_patterns_count": len(improvements.get("bad_patterns", [])),
            "good_patterns_count": len(improvements.get("good_patterns", []))
        }
        
        profile["improvements"].append(improvement_entry)
        profile["improvements"] = profile["improvements"][-5:]  # 最新5件
        
        # 好みを更新
        if improvements.get("suggestions"):
            for suggestion in improvements["suggestions"]:
                if "詳しく" in suggestion or "具体的" in suggestion:
                    if "詳細な説明を好む" not in profile["preferences"]:
                        profile["preferences"].append("詳細な説明を好む")
        
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
        
        self.conn.commit()
        
        return profile