# """
# パートナーAI - バックエンドコア
# FastAPI + Ollama + SQLite
# """

# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import List, Optional, Dict
# import ollama
# import sqlite3
# import json
# from datetime import datetime
# import os
# from analyzer import ConversationAnalyzer, ProfileManager
# from rag_system import RAGSystem, SelfImprovementSystem

# # FastAPIアプリ初期化
# app = FastAPI(title="パートナーAI API")

# # CORS設定（フロントエンドからのアクセス許可）
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # データベースファイル
# DB_PATH = "partner_ai.db"

# # ==================== データベース初期化 ====================

# def init_db():
#     """データベース初期化"""
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
    
#     # 会話テーブル
#     c.execute("""
#         CREATE TABLE IF NOT EXISTS conversations (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id TEXT NOT NULL,
#             timestamp TEXT NOT NULL,
#             user_message TEXT NOT NULL,
#             ai_response TEXT NOT NULL,
#             model_used TEXT,
#             rating INTEGER,
#             tags TEXT,
#             metadata TEXT
#         )
#     """)
    
#     # ユーザープロファイルテーブル
#     c.execute("""
#         CREATE TABLE IF NOT EXISTS user_profiles (
#             user_id TEXT PRIMARY KEY,
#             profile_data TEXT NOT NULL,
#             created_at TEXT NOT NULL,
#             updated_at TEXT NOT NULL
#         )
#     """)
    
#     conn.commit()
#     conn.close()
#     print("✅ データベース初期化完了")

# # アプリ起動時に実行
# init_db()

# # グローバルインスタンス
# analyzer = ConversationAnalyzer(model="gemma3:4b")
# rag_system = RAGSystem(persist_directory="./chroma_db")
# print(f"✅ RAGシステム初期化完了")

# # ==================== Pydanticモデル ====================

# class ChatRequest(BaseModel):
#     user_id: str
#     message: str
#     model: Optional[str] = "qwen2.5:32b"

# class ChatResponse(BaseModel):
#     conversation_id: int
#     response: str
#     model_used: str
#     timestamp: str
#     reason: Optional[str] = None
#     tags: Optional[List[str]] = None

# class FeedbackRequest(BaseModel):
#     conversation_id: int
#     rating: int
#     comment: Optional[str] = None

# class HistoryResponse(BaseModel):
#     conversations: List[Dict]
#     total: int

# # ==================== ヘルパー関数 ====================

# def get_user_profile(user_id: str) -> Dict:
#     """ユーザープロファイル取得"""
#     conn = sqlite3.connect(DB_PATH)
#     profile_manager = ProfileManager(conn)
#     profile = profile_manager.get_profile(user_id)
#     conn.close()
#     return profile

# def save_conversation(
#     user_id: str,
#     user_msg: str,
#     ai_msg: str,
#     model: str,
#     metadata: Dict = None
# ) -> int:
#     """会話を保存"""
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
    
#     timestamp = datetime.now().isoformat()
#     metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"
    
#     c.execute("""
#         INSERT INTO conversations 
#         (user_id, timestamp, user_message, ai_response, model_used, metadata)
#         VALUES (?, ?, ?, ?, ?, ?)
#     """, (user_id, timestamp, user_msg, ai_msg, model, metadata_json))
    
#     conv_id = c.lastrowid
#     conn.commit()
#     conn.close()
    
#     return conv_id

# def get_recent_history(user_id: str, limit: int = 5) -> List[Dict]:
#     """最近の会話履歴を取得"""
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
    
#     c.execute("""
#         SELECT user_message, ai_response, timestamp
#         FROM conversations
#         WHERE user_id = ?
#         ORDER BY timestamp DESC
#         LIMIT ?
#     """, (user_id, limit))
    
#     rows = c.fetchall()
#     conn.close()
    
#     history = []
#     for row in reversed(rows):  # 古い順に並べ替え
#         history.append({
#             "user": row[0],
#             "ai": row[1],
#             "timestamp": row[2]
#         })
    
#     return history

# def build_system_prompt(profile: Dict) -> str:
#     """ユーザープロファイルからシステムプロンプト生成"""
#     conn = sqlite3.connect(DB_PATH)
#     profile_manager = ProfileManager(conn)
#     # プロファイルからパーソナライズされたプロンプトを生成
#     # user_idは不要なのでダミーを使用（既にprofileがある）
#     prompt = profile_manager.get_personalized_system_prompt("dummy")
#     conn.close()
    
#     # profileの内容を直接使用するように修正
#     base = "あなたは親しみやすく、有能なAIアシスタントです。\n"
    
#     if profile.get("interests"):
#         interests = ", ".join(profile["interests"])
#         base += f"\nユーザーは以下のトピックに興味があります: {interests}\n"
    
#     if profile.get("memories"):
#         base += "\nユーザーについて学習した情報:\n"
#         for mem in profile["memories"][-3:]:
#             base += f"- {mem}\n"
    
#     return base

# # ==================== APIエンドポイント ====================

# @app.get("/")
# async def root():
#     """ヘルスチェック"""
#     return {
#         "status": "ok",
#         "message": "パートナーAI バックエンドが稼働中",
#         "version": "1.0.0"
#     }

# @app.post("/api/chat", response_model=ChatResponse)
# async def chat(req: ChatRequest):
#     """チャットAPI"""
#     try:
#         # プロファイル取得
#         profile = get_user_profile(req.user_id)
        
#         # 履歴取得
#         history = get_recent_history(req.user_id, limit=5)
        
#         # RAGで関連する記憶を検索
#         relevant_memories = rag_system.search_relevant_memories(
#             user_id=req.user_id,
#             query=req.message,
#             n_results=3
#         )
        
#         # システムプロンプト構築
#         system_prompt = build_system_prompt(profile)
        
#         # 関連する記憶を追加
#         if relevant_memories:
#             system_prompt += "\n\n過去の関連する会話:\n"
#             for mem in relevant_memories:
#                 system_prompt += f"- {mem['user_message'][:100]}...\n"
        
#         # メッセージ構築
#         messages = [
#             {"role": "system", "content": system_prompt}
#         ]
        
#         # 履歴追加
#         for h in history:
#             messages.append({"role": "user", "content": h["user"]})
#             messages.append({"role": "assistant", "content": h["ai"]})
        
#         # 現在のメッセージ
#         messages.append({"role": "user", "content": req.message})
        
#         # Ollama呼び出し
#         print(f"🤖 モデル {req.model} で推論中...")
#         response = ollama.chat(
#             model=req.model,
#             messages=messages,
#             options={
#                 "temperature": 0.7,
#                 "num_ctx": 8192,
#             }
#         )
        
#         ai_response = response['message']['content']
        
#         # 応答理由を生成
#         reason = generate_response_reason(req.message, ai_response, profile, relevant_memories)
        
#         # タグを自動生成
#         tags = analyzer.extract_topics_simple(f"{req.message} {ai_response}")
        
#         # メタデータ作成
#         metadata = {
#             "reason": reason,
#             "tags": tags,
#             "relevant_memories_count": len(relevant_memories),
#             "model_params": {
#                 "temperature": 0.7,
#                 "context_length": 8192
#             }
#         }
        
#         # 会話を保存
#         conv_id = save_conversation(
#             user_id=req.user_id,
#             user_msg=req.message,
#             ai_msg=ai_response,
#             model=req.model,
#             metadata=metadata
#         )
        
#         # RAGに記憶を追加
#         rag_system.add_memory(
#             user_id=req.user_id,
#             conversation_id=conv_id,
#             user_message=req.message,
#             ai_response=ai_response,
#             metadata={"tags": tags}
#         )
        
#         # 会話を分析してプロファイルを更新
#         try:
#             analysis = analyzer.analyze_conversation(req.message, ai_response)
            
#             conn = sqlite3.connect(DB_PATH)
#             profile_manager = ProfileManager(conn)
#             updated_profile = profile_manager.update_profile(req.user_id, analysis)
#             conn.close()
            
#             print(f"✅ プロファイル更新完了: {updated_profile.get('interests', [])}")
#         except Exception as e:
#             print(f"⚠️ プロファイル更新エラー: {e}")
        
#         print(f"✅ 応答完了 (ID: {conv_id})")
        
#         return ChatResponse(
#             conversation_id=conv_id,
#             response=ai_response,
#             model_used=req.model,
#             timestamp=datetime.now().isoformat(),
#             reason=reason,
#             tags=tags
#         )
        
#     except Exception as e:
#         print(f"❌ エラー: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# def generate_response_reason(
#     user_message: str,
#     ai_response: str,
#     profile: Dict,
#     memories: List[Dict]
# ) -> str:
#     """応答理由を生成"""
    
#     reasons = []
    
#     # プロファイルに基づく理由
#     if profile.get("interests"):
#         interests = ", ".join(profile["interests"][:2])
#         reasons.append(f"あなたの興味({interests})を考慮しました")
    
#     # 記憶に基づく理由
#     if memories:
#         reasons.append(f"過去の{len(memories)}件の関連会話を参照しました")
    
#     # メッセージの特性
#     if "?" in user_message or "？" in user_message:
#         reasons.append("質問に対する回答を生成しました")
#     elif len(user_message) > 100:
#         reasons.append("詳細な質問に対して丁寧に回答しました")
#     else:
#         reasons.append("簡潔な応答を心がけました")
    
#     return "、".join(reasons) if reasons else "一般的な知識に基づいて回答しました"

# @app.get("/api/history/{user_id}", response_model=HistoryResponse)
# async def get_history(user_id: str, limit: int = 50):
#     """会話履歴取得"""
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         c = conn.cursor()
        
#         c.execute("""
#             SELECT id, timestamp, user_message, ai_response, model_used, rating, metadata
#             FROM conversations
#             WHERE user_id = ?
#             ORDER BY timestamp DESC
#             LIMIT ?
#         """, (user_id, limit))
        
#         rows = c.fetchall()
#         conn.close()
        
#         conversations = []
#         for row in rows:
#             metadata = json.loads(row[6]) if row[6] else {}
            
#             conversations.append({
#                 "id": row[0],
#                 "timestamp": row[1],
#                 "user_message": row[2],
#                 "ai_response": row[3],
#                 "model_used": row[4],
#                 "rating": row[5],
#                 "tags": metadata.get("tags", []),
#                 "reason": metadata.get("reason", "")
#             })
        
#         return HistoryResponse(
#             conversations=conversations,
#             total=len(conversations)
#         )
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/api/feedback")
# async def submit_feedback(req: FeedbackRequest):
#     """フィードバック保存"""
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         c = conn.cursor()
        
#         # 現在のメタデータを取得
#         c.execute("SELECT metadata FROM conversations WHERE id = ?", (req.conversation_id,))
#         row = c.fetchone()
        
#         if row:
#             metadata = json.loads(row[0]) if row[0] else {}
#         else:
#             metadata = {}
        
#         # フィードバックを追加
#         metadata["feedback_rating"] = req.rating
#         if req.comment:
#             metadata["feedback_comment"] = req.comment
#         metadata["feedback_timestamp"] = datetime.now().isoformat()
        
#         # 更新
#         c.execute("""
#             UPDATE conversations
#             SET rating = ?, metadata = ?
#             WHERE id = ?
#         """, (req.rating, json.dumps(metadata, ensure_ascii=False), req.conversation_id))
        
#         conn.commit()
        
#         # 自己改良システムを実行（低評価の場合）
#         if req.rating <= 2:
#             c.execute("SELECT user_id FROM conversations WHERE id = ?", (req.conversation_id,))
#             user_row = c.fetchone()
            
#             if user_row:
#                 user_id = user_row[0]
#                 improvement_system = SelfImprovementSystem(conn)
#                 improvements = improvement_system.analyze_feedback(user_id)
                
#                 if improvements["suggestions"]:
#                     improvement_system.apply_improvements(user_id, improvements)
#                     print(f"✅ 自己改良実行: {improvements['suggestions']}")
        
#         conn.close()
        
#         print(f"✅ フィードバック保存 (ID: {req.conversation_id}, Rating: {req.rating})")
        
#         return {"status": "success", "message": "フィードバックを保存しました"}
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/api/models")
# async def list_models():
#     """利用可能なモデル一覧"""
#     try:
#         result = ollama.list()
#         models = []
#         # ListResponseオブジェクトから直接modelsを取得
#         model_list = result.models if hasattr(result, 'models') else []

#         for m in model_list:
#             # Modelオブジェクトから属性を取得
#             name = m.model if hasattr(m, 'model') else str(m)
#             size = m.size if hasattr(m, 'size') else 0

#             # 詳細情報を取得
#             details = m.details if hasattr(m, 'details') else None
#             param_size = details.parameter_size if details and hasattr(details, 'parameter_size') else ''
#             quant = details.quantization_level if details and hasattr(details, 'quantization_level') else ''
            
#             models.append({
#                 "name": name,
#                 "size": size,
#                 "size_gb": round(size / (1024**3), 1),
#                 "parameter_size": param_size,
#                 "quantization": quant
#             })
        
#         return {"models": models}

#     except Exception as e:
#         print(f"❌ エラー: {e}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/api/stats/{user_id}")
# async def get_stats(user_id: str):
#     """ユーザー統計"""
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         c = conn.cursor()
        
#         # 総会話数
#         c.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
#         total_conversations = c.fetchone()[0]
        
#         # 平均評価
#         c.execute("""
#             SELECT AVG(rating) 
#             FROM conversations 
#             WHERE user_id = ? AND rating IS NOT NULL
#         """, (user_id,))
#         avg_rating = c.fetchone()[0] or 0
        
#         # よく使うモデル
#         c.execute("""
#             SELECT model_used, COUNT(*) as count
#             FROM conversations
#             WHERE user_id = ?
#             GROUP BY model_used
#             ORDER BY count DESC
#             LIMIT 1
#         """, (user_id,))
#         most_used_model = c.fetchone()
        
#         conn.close()
        
#         return {
#             "total_conversations": total_conversations,
#             "average_rating": round(avg_rating, 2),
#             "most_used_model": most_used_model[0] if most_used_model else None
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    

# @app.get("/api/profile/{user_id}")
# async def get_profile_endpoint(user_id: str):
#     """ユーザープロファイル取得"""
#     try:
#         profile = get_user_profile(user_id)
        
#         # RAGの記憶数を追加
#         memory_count = rag_system.get_memory_count(user_id)
#         profile["rag_memories"] = memory_count
        
#         return {"profile": profile}
#     except Exception as e:
#         print(f"❌ プロファイル取得エラー: {e}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/api/improve/{user_id}")
# async def trigger_improvement(user_id: str):
#     """手動で自己改良を実行"""
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         improvement_system = SelfImprovementSystem(conn)
        
#         improvements = improvement_system.analyze_feedback(user_id)
#         updated_profile = improvement_system.apply_improvements(user_id, improvements)
        
#         conn.close()
        
#         return {
#             "status": "success",
#             "improvements": improvements,
#             "updated_profile": updated_profile
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/api/conversation/{conversation_id}/tags")
# async def update_conversation_tags(conversation_id: int, tags: List[str]):
#     """会話のタグを更新"""
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         c = conn.cursor()
        
#         # 現在のメタデータを取得
#         c.execute("SELECT metadata FROM conversations WHERE id = ?", (conversation_id,))
#         row = c.fetchone()
        
#         if row:
#             metadata = json.loads(row[0]) if row[0] else {}
#         else:
#             raise HTTPException(status_code=404, detail="Conversation not found")
        
#         # タグを更新
#         metadata["tags"] = tags
        
#         # 保存
#         c.execute("""
#             UPDATE conversations
#             SET metadata = ?
#             WHERE id = ?
#         """, (json.dumps(metadata, ensure_ascii=False), conversation_id))
        
#         conn.commit()
#         conn.close()
        
#         return {"status": "success", "tags": tags}
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # ==================== 起動 ====================

# if __name__ == "__main__":
#     import uvicorn
    
#     print("=" * 50)
#     print("🚀 パートナーAI バックエンド起動中...")
#     print("=" * 50)
#     print(f"📊 データベース: {DB_PATH}")
#     print(f"🌐 API: http://localhost:8000")
#     print(f"📖 ドキュメント: http://localhost:8000/docs")
#     print("=" * 50)
    
#     uvicorn.run(app, host="0.0.0.0", port=8000)






"""
パートナーAI - バックエンドコア
FastAPI + Ollama + SQLite
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import ollama
import sqlite3
import json
from datetime import datetime
import os
from analyzer import ConversationAnalyzer, ProfileManager
from rag_system import RAGSystem, SelfImprovementSystem
from finetuning import FineTuningSystem

# FastAPIアプリ初期化
app = FastAPI(title="パートナーAI API")

# CORS設定（フロントエンドからのアクセス許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベースファイル
DB_PATH = "partner_ai.db"

# ==================== データベース初期化 ====================

def init_db():
    """データベース初期化"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 会話テーブル
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
    
    # ユーザープロファイルテーブル
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
    print("✅ データベース初期化完了")

# アプリ起動時に実行
init_db()

# グローバルインスタンス
analyzer = ConversationAnalyzer(model="gemma3:4b")
rag_system = RAGSystem(persist_directory="./chroma_db")
print(f"✅ RAGシステム初期化完了")

# ==================== Pydanticモデル ====================

class ChatRequest(BaseModel):
    user_id: str
    message: str
    model: Optional[str] = "qwen2.5:32b"

class ChatResponse(BaseModel):
    conversation_id: int
    response: str
    model_used: str
    timestamp: str
    reason: Optional[str] = None
    tags: Optional[List[str]] = None

class FeedbackRequest(BaseModel):
    conversation_id: int
    rating: int
    comment: Optional[str] = None

class HistoryResponse(BaseModel):
    conversations: List[Dict]
    total: int

# ==================== ヘルパー関数 ====================

def get_user_profile(user_id: str) -> Dict:
    """ユーザープロファイル取得"""
    conn = sqlite3.connect(DB_PATH)
    profile_manager = ProfileManager(conn)
    profile = profile_manager.get_profile(user_id)
    conn.close()
    return profile

def save_conversation(
    user_id: str,
    user_msg: str,
    ai_msg: str,
    model: str,
    metadata: Dict = None
) -> int:
    """会話を保存"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"
    
    c.execute("""
        INSERT INTO conversations 
        (user_id, timestamp, user_message, ai_response, model_used, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, timestamp, user_msg, ai_msg, model, metadata_json))
    
    conv_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return conv_id

def get_recent_history(user_id: str, limit: int = 5) -> List[Dict]:
    """最近の会話履歴を取得"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT user_message, ai_response, timestamp
        FROM conversations
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (user_id, limit))
    
    rows = c.fetchall()
    conn.close()
    
    history = []
    for row in reversed(rows):  # 古い順に並べ替え
        history.append({
            "user": row[0],
            "ai": row[1],
            "timestamp": row[2]
        })
    
    return history

def build_system_prompt(profile: Dict) -> str:
    """ユーザープロファイルからシステムプロンプト生成"""
    conn = sqlite3.connect(DB_PATH)
    profile_manager = ProfileManager(conn)
    # プロファイルからパーソナライズされたプロンプトを生成
    # user_idは不要なのでダミーを使用（既にprofileがある）
    prompt = profile_manager.get_personalized_system_prompt("dummy")
    conn.close()
    
    # profileの内容を直接使用するように修正
    base = "あなたは親しみやすく、有能なAIアシスタントです。\n"
    
    if profile.get("interests"):
        interests = ", ".join(profile["interests"])
        base += f"\nユーザーは以下のトピックに興味があります: {interests}\n"
    
    if profile.get("memories"):
        base += "\nユーザーについて学習した情報:\n"
        for mem in profile["memories"][-3:]:
            base += f"- {mem}\n"
    
    return base

# ==================== APIエンドポイント ====================

@app.get("/")
async def root():
    """ヘルスチェック"""
    return {
        "status": "ok",
        "message": "パートナーAI バックエンドが稼働中",
        "version": "1.0.0"
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """チャットAPI"""
    try:
        # プロファイル取得
        profile = get_user_profile(req.user_id)
        
        # 履歴取得
        history = get_recent_history(req.user_id, limit=5)
        
        # RAGで関連する記憶を検索
        relevant_memories = rag_system.search_relevant_memories(
            user_id=req.user_id,
            query=req.message,
            n_results=3
        )
        
        # システムプロンプト構築
        system_prompt = build_system_prompt(profile)
        
        # 関連する記憶を追加
        if relevant_memories:
            system_prompt += "\n\n過去の関連する会話:\n"
            for mem in relevant_memories:
                system_prompt += f"- {mem['user_message'][:100]}...\n"
        
        # メッセージ構築
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 履歴追加
        for h in history:
            messages.append({"role": "user", "content": h["user"]})
            messages.append({"role": "assistant", "content": h["ai"]})
        
        # 現在のメッセージ
        messages.append({"role": "user", "content": req.message})
        
        # Ollama呼び出し
        print(f"🤖 モデル {req.model} で推論中...")
        response = ollama.chat(
            model=req.model,
            messages=messages,
            options={
                "temperature": 0.7,
                "num_ctx": 8192,
            }
        )
        
        ai_response = response['message']['content']
        
        # 応答理由を生成
        reason = generate_response_reason(req.message, ai_response, profile, relevant_memories)
        
        # タグを自動生成
        tags = analyzer.extract_topics_simple(f"{req.message} {ai_response}")
        
        # メタデータ作成
        metadata = {
            "reason": reason,
            "tags": tags,
            "relevant_memories_count": len(relevant_memories),
            "model_params": {
                "temperature": 0.7,
                "context_length": 8192
            }
        }
        
        # 会話を保存
        conv_id = save_conversation(
            user_id=req.user_id,
            user_msg=req.message,
            ai_msg=ai_response,
            model=req.model,
            metadata=metadata
        )
        
        # RAGに記憶を追加
        rag_system.add_memory(
            user_id=req.user_id,
            conversation_id=conv_id,
            user_message=req.message,
            ai_response=ai_response,
            metadata={"tags": tags}
        )
        
        # 会話を分析してプロファイルを更新
        try:
            analysis = analyzer.analyze_conversation(req.message, ai_response)
            
            conn = sqlite3.connect(DB_PATH)
            profile_manager = ProfileManager(conn)
            updated_profile = profile_manager.update_profile(req.user_id, analysis)
            conn.close()
            
            print(f"✅ プロファイル更新完了: {updated_profile.get('interests', [])}")
        except Exception as e:
            print(f"⚠️ プロファイル更新エラー: {e}")
        
        print(f"✅ 応答完了 (ID: {conv_id})")
        
        return ChatResponse(
            conversation_id=conv_id,
            response=ai_response,
            model_used=req.model,
            timestamp=datetime.now().isoformat(),
            reason=reason,
            tags=tags
        )
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_response_reason(
    user_message: str,
    ai_response: str,
    profile: Dict,
    memories: List[Dict]
) -> str:
    """応答理由を生成"""
    
    reasons = []
    
    # プロファイルに基づく理由
    if profile.get("interests"):
        interests = ", ".join(profile["interests"][:2])
        reasons.append(f"あなたの興味({interests})を考慮しました")
    
    # 記憶に基づく理由
    if memories:
        reasons.append(f"過去の{len(memories)}件の関連会話を参照しました")
    
    # メッセージの特性
    if "?" in user_message or "？" in user_message:
        reasons.append("質問に対する回答を生成しました")
    elif len(user_message) > 100:
        reasons.append("詳細な質問に対して丁寧に回答しました")
    else:
        reasons.append("簡潔な応答を心がけました")
    
    return "、".join(reasons) if reasons else "一般的な知識に基づいて回答しました"

@app.get("/api/history/{user_id}", response_model=HistoryResponse)
async def get_history(user_id: str, limit: int = 50):
    """会話履歴取得"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT id, timestamp, user_message, ai_response, model_used, rating, metadata
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = c.fetchall()
        conn.close()
        
        conversations = []
        for row in rows:
            metadata = json.loads(row[6]) if row[6] else {}
            
            conversations.append({
                "id": row[0],
                "timestamp": row[1],
                "user_message": row[2],
                "ai_response": row[3],
                "model_used": row[4],
                "rating": row[5],
                "tags": metadata.get("tags", []),
                "reason": metadata.get("reason", "")
            })
        
        return HistoryResponse(
            conversations=conversations,
            total=len(conversations)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    """フィードバック保存"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 現在のメタデータを取得
        c.execute("SELECT metadata FROM conversations WHERE id = ?", (req.conversation_id,))
        row = c.fetchone()
        
        if row:
            metadata = json.loads(row[0]) if row[0] else {}
        else:
            metadata = {}
        
        # フィードバックを追加
        metadata["feedback_rating"] = req.rating
        if req.comment:
            metadata["feedback_comment"] = req.comment
        metadata["feedback_timestamp"] = datetime.now().isoformat()
        
        # 更新
        c.execute("""
            UPDATE conversations
            SET rating = ?, metadata = ?
            WHERE id = ?
        """, (req.rating, json.dumps(metadata, ensure_ascii=False), req.conversation_id))
        
        conn.commit()
        
        # 自己改良システムを実行（低評価の場合）
        if req.rating <= 2:
            c.execute("SELECT user_id FROM conversations WHERE id = ?", (req.conversation_id,))
            user_row = c.fetchone()
            
            if user_row:
                user_id = user_row[0]
                improvement_system = SelfImprovementSystem(conn)
                improvements = improvement_system.analyze_feedback(user_id)
                
                if improvements["suggestions"]:
                    improvement_system.apply_improvements(user_id, improvements)
                    print(f"✅ 自己改良実行: {improvements['suggestions']}")
        
        conn.close()
        
        print(f"✅ フィードバック保存 (ID: {req.conversation_id}, Rating: {req.rating})")
        
        return {"status": "success", "message": "フィードバックを保存しました"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def list_models():
    """利用可能なモデル一覧"""
    try:
        result = ollama.list()
        models = []
        # ListResponseオブジェクトから直接modelsを取得
        model_list = result.models if hasattr(result, 'models') else []

        for m in model_list:
            # Modelオブジェクトから属性を取得
            name = m.model if hasattr(m, 'model') else str(m)
            size = m.size if hasattr(m, 'size') else 0

            # 詳細情報を取得
            details = m.details if hasattr(m, 'details') else None
            param_size = details.parameter_size if details and hasattr(details, 'parameter_size') else ''
            quant = details.quantization_level if details and hasattr(details, 'quantization_level') else ''
            
            models.append({
                "name": name,
                "size": size,
                "size_gb": round(size / (1024**3), 1),
                "parameter_size": param_size,
                "quantization": quant
            })
        
        return {"models": models}

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/{user_id}")
async def get_stats(user_id: str):
    """ユーザー統計"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 総会話数
        c.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
        total_conversations = c.fetchone()[0]
        
        # 平均評価
        c.execute("""
            SELECT AVG(rating) 
            FROM conversations 
            WHERE user_id = ? AND rating IS NOT NULL
        """, (user_id,))
        avg_rating = c.fetchone()[0] or 0
        
        # よく使うモデル
        c.execute("""
            SELECT model_used, COUNT(*) as count
            FROM conversations
            WHERE user_id = ?
            GROUP BY model_used
            ORDER BY count DESC
            LIMIT 1
        """, (user_id,))
        most_used_model = c.fetchone()
        
        conn.close()
        
        return {
            "total_conversations": total_conversations,
            "average_rating": round(avg_rating, 2),
            "most_used_model": most_used_model[0] if most_used_model else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def list_models():
    """利用可能なモデル一覧"""
    try:
        result = ollama.list()
        models = []
        # ListResponseオブジェクトから直接modelsを取得
        model_list = result.models if hasattr(result, 'models') else []

        for m in model_list:
            # Modelオブジェクトから属性を取得
            name = m.model if hasattr(m, 'model') else str(m)
            size = m.size if hasattr(m, 'size') else 0

            # 詳細情報を取得
            details = m.details if hasattr(m, 'details') else None
            param_size = details.parameter_size if details and hasattr(details, 'parameter_size') else ''
            quant = details.quantization_level if details and hasattr(details, 'quantization_level') else ''
            
            models.append({
                "name": name,
                "size": size,
                "size_gb": round(size / (1024**3), 1),
                "parameter_size": param_size,
                "quantization": quant
            })
        
        return {"models": models}

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/profile/{user_id}")
async def get_profile_endpoint(user_id: str):
    """ユーザープロファイル取得"""
    try:
        profile = get_user_profile(user_id)
        
        # RAGの記憶数を追加
        memory_count = rag_system.get_memory_count(user_id)
        profile["rag_memories"] = memory_count
        
        return {"profile": profile}
    except Exception as e:
        print(f"❌ プロファイル取得エラー: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/improve/{user_id}")
async def trigger_improvement(user_id: str):
    """手動で自己改良を実行"""
    try:
        conn = sqlite3.connect(DB_PATH)
        improvement_system = SelfImprovementSystem(conn)
        
        improvements = improvement_system.analyze_feedback(user_id)
        updated_profile = improvement_system.apply_improvements(user_id, improvements)
        
        conn.close()
        
        return {
            "status": "success",
            "improvements": improvements,
            "updated_profile": updated_profile
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversation/{conversation_id}/tags")
async def update_conversation_tags(conversation_id: int, tags: List[str]):
    """会話のタグを更新"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 現在のメタデータを取得
        c.execute("SELECT metadata FROM conversations WHERE id = ?", (conversation_id,))
        row = c.fetchone()
        
        if row:
            metadata = json.loads(row[0]) if row[0] else {}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # タグを更新
        metadata["tags"] = tags
        
        # 保存
        c.execute("""
            UPDATE conversations
            SET metadata = ?
            WHERE id = ?
        """, (json.dumps(metadata, ensure_ascii=False), conversation_id))
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "tags": tags}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ==================== 起動 ====================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("🚀 パートナーAI バックエンド起動中...")
    print("=" * 50)
    print(f"📊 データベース: {DB_PATH}")
    print(f"🌐 API: http://localhost:8000")
    print(f"📖 ドキュメント: http://localhost:8000/docs")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)