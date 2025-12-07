"""
パートナーAI - バックエンドコア (修正版)
FastAPI + Ollama + SQLite
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import ollama
import sqlite3
import json
from datetime import datetime
import os
import asyncio

# 全てのインポート
from analyzer import ConversationAnalyzer, ProfileManager
from rag_system import RAGSystem, SelfImprovementSystem
from finetuning import FineTuningSystem
from schedule_manager import ScheduleManager
from assistant_brain import AssistantBrain
from goal_journal_system import GoalManager, JournalSystem
from active_partner_system import ConversationInitiator, MessagePriority

# FastAPIアプリ初期化
app = FastAPI(title="パートナーAI API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベースファイル
DB_PATH = "partner_ai.db"

# グローバル変数（起動時に初期化）
analyzer = None
rag_system = None
schedule_manager = None
assistant_brain = None
goal_manager = None
journal_system = None
conversation_initiator = None

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
    model: Optional[str] = "qwen2.5:7b"

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

class FineTuneRequest(BaseModel):
    base_model: str = "qwen2.5:7b"

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
    base = "あなたは親しみやすく、有能なAIアシスタントです。\n"
    
    if profile.get("interests"):
        interests = ", ".join(profile["interests"])
        base += f"\nユーザーは以下のトピックに興味があります: {interests}\n"
    
    if profile.get("memories"):
        base += "\nユーザーについて学習した情報:\n"
        for mem in profile["memories"][-3:]:
            base += f"- {mem}\n"
    
    return base

def generate_response_reason(
    user_message: str,
    ai_response: str,
    profile: Dict,
    memories: List[Dict]
) -> str:
    """応答理由を生成"""
    reasons = []
    
    if profile.get("interests"):
        interests = ", ".join(profile["interests"][:2])
        reasons.append(f"あなたの興味({interests})を考慮しました")
    
    if memories:
        reasons.append(f"過去の{len(memories)}件の関連会話を参照しました")
    
    if "?" in user_message or "?" in user_message:
        reasons.append("質問に対する回答を生成しました")
    elif len(user_message) > 100:
        reasons.append("詳細な質問に対して丁寧に回答しました")
    else:
        reasons.append("簡潔な応答を心がけました")
    
    return "、".join(reasons) if reasons else "一般的な知識に基づいて回答しました"

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
    """
    チャットAPI - 高性能版
    スケジュール・タスク・目標を自動抽出して登録
    """
    try:
        profile = get_user_profile(req.user_id)
        history = get_recent_history(req.user_id, limit=5)
        
        relevant_memories = rag_system.search_relevant_memories(
            user_id=req.user_id,
            query=req.message,
            n_results=3
        )
        
        system_prompt = build_system_prompt(profile)
        
        if relevant_memories:
            system_prompt += "\n\n過去の関連する会話:\n"
            for mem in relevant_memories:
                system_prompt += f"- {mem['user_message'][:100]}...\n"
        
        messages = [{"role": "system", "content": system_prompt}]
        
        for h in history:
            messages.append({"role": "user", "content": h["user"]})
            messages.append({"role": "assistant", "content": h["ai"]})
        
        messages.append({"role": "user", "content": req.message})
        
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
        tags = analyzer.extract_topics_simple(f"{req.message} {ai_response}")
        
        metadata = {
            "tags": tags,
            "relevant_memories_count": len(relevant_memories),
            "auto_extractions": []  # 自動抽出した項目を記録
        }
        
        # ==================== 自動抽出処理 ====================
        
        conn = sqlite3.connect(DB_PATH)
        schedule_manager.conn = conn
        goal_manager.conn = conn
        
        extraction_messages = []  # 追加メッセージを格納
        
        # 🔍 1. スケジュール抽出
        try:
            schedule_data = schedule_manager.extract_schedule_from_text(req.message)
            
            if schedule_data and schedule_data.get("has_schedule"):
                print(f"📅 スケジュール検出: {schedule_data['title']}")
                
                schedule_id = schedule_manager.create_schedule(
                    user_id=req.user_id,
                    title=schedule_data['title'],
                    start_time=schedule_data['start_time'],
                    end_time=schedule_data.get('end_time'),
                    description=schedule_data.get('description', ''),
                    location=schedule_data.get('location', ''),
                    attendees=schedule_data.get('attendees', [])
                )
                
                metadata["auto_extractions"].append({
                    "type": "schedule",
                    "id": schedule_id,
                    "title": schedule_data['title']
                })
                
                extraction_messages.append(
                    f"📅 予定「{schedule_data['title']}」をスケジュールに追加しました"
                )
        except Exception as e:
            print(f"⚠️ スケジュール抽出エラー: {e}")
        
        # 🔍 2. タスク抽出
        try:
            task_data = schedule_manager.extract_task_from_text(req.message)
            
            if task_data and task_data.get("has_task"):
                print(f"✅ タスク検出: {task_data['title']}")
                
                task_id = schedule_manager.create_task(
                    user_id=req.user_id,
                    title=task_data['title'],
                    description=task_data.get('description', ''),
                    due_date=task_data.get('due_date'),
                    priority=task_data.get('priority', 'medium'),
                    estimated_minutes=task_data.get('estimated_minutes')
                )
                
                # サブタスクがあれば追加
                if task_data.get('subtasks'):
                    c = conn.cursor()
                    for subtask_title in task_data['subtasks']:
                        c.execute("""
                            INSERT INTO subtasks (task_id, title)
                            VALUES (?, ?)
                        """, (task_id, subtask_title))
                    conn.commit()
                
                metadata["auto_extractions"].append({
                    "type": "task",
                    "id": task_id,
                    "title": task_data['title'],
                    "priority": task_data.get('priority', 'medium')
                })
                
                priority_emoji = {
                    "high": "🔥", 
                    "medium": "📌", 
                    "low": "💡"
                }.get(task_data.get('priority', 'medium'), "📌")
                
                extraction_messages.append(
                    f"{priority_emoji} タスク「{task_data['title']}」を追加しました"
                )
        except Exception as e:
            print(f"⚠️ タスク抽出エラー: {e}")
        
        # 🔍 3. 目標抽出
        try:
            goal_data = goal_manager.extract_goal_from_text(req.message)
            
            if goal_data and goal_data.get("has_goal"):
                print(f"🎯 目標検出: {goal_data['title']}")
                
                goal_id = goal_manager.create_goal(
                    user_id=req.user_id,
                    title=goal_data['title'],
                    description=goal_data.get('description', ''),
                    category=goal_data.get('category', 'personal'),
                    target_date=goal_data.get('target_date')
                )
                
                # マイルストーンがあれば追加
                if goal_data.get('key_milestones'):
                    for milestone_title in goal_data['key_milestones']:
                        goal_manager.add_milestone(
                            goal_id=goal_id,
                            title=milestone_title
                        )
                
                metadata["auto_extractions"].append({
                    "type": "goal",
                    "id": goal_id,
                    "title": goal_data['title']
                })
                
                extraction_messages.append(
                    f"🎯 目標「{goal_data['title']}」を設定しました"
                )
        except Exception as e:
            print(f"⚠️ 目標抽出エラー: {e}")
        
        # 接続をクリア
        conn.close()
        schedule_manager.conn = None
        goal_manager.conn = None
        
        # AI応答に抽出結果を追記
        if extraction_messages:
            ai_response += "\n\n" + "\n".join(extraction_messages)
        
        # ==================== 会話保存 ====================
        
        conv_id = save_conversation(
            user_id=req.user_id,
            user_msg=req.message,
            ai_msg=ai_response,
            model=req.model,
            metadata=metadata
        )
        
        # RAGに追加
        rag_system.add_memory(
            user_id=req.user_id,
            conversation_id=conv_id,
            user_message=req.message,
            ai_response=ai_response,
            metadata={"tags": tags}
        )
        
        # プロファイル更新
        try:
            analysis = analyzer.analyze_conversation(req.message, ai_response)
            conn = sqlite3.connect(DB_PATH)
            profile_manager = ProfileManager(conn)
            profile_manager.update_profile(req.user_id, analysis)
            conn.close()
        except Exception as e:
            print(f"⚠️ プロファイル更新エラー: {e}")
        
        return ChatResponse(
            conversation_id=conv_id,
            response=ai_response,
            model_used=req.model,
            timestamp=datetime.now().isoformat(),
            tags=tags
        )
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
        
        c.execute("SELECT metadata FROM conversations WHERE id = ?", (req.conversation_id,))
        row = c.fetchone()
        
        metadata = json.loads(row[0]) if row and row[0] else {}
        
        metadata["feedback_rating"] = req.rating
        if req.comment:
            metadata["feedback_comment"] = req.comment
        metadata["feedback_timestamp"] = datetime.now().isoformat()
        
        c.execute("""
            UPDATE conversations
            SET rating = ?, metadata = ?
            WHERE id = ?
        """, (req.rating, json.dumps(metadata, ensure_ascii=False), req.conversation_id))
        
        conn.commit()
        
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
        
        c.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
        total_conversations = c.fetchone()[0]
        
        c.execute("""
            SELECT AVG(rating) 
            FROM conversations 
            WHERE user_id = ? AND rating IS NOT NULL
        """, (user_id,))
        avg_rating = c.fetchone()[0] or 0
        
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

@app.get("/api/profile/{user_id}")
async def get_profile_endpoint(user_id: str):
    """ユーザープロファイル取得"""
    try:
        profile = get_user_profile(user_id)
        memory_count = rag_system.get_memory_count(user_id)
        profile["rag_memories"] = memory_count
        
        return {"profile": profile}
    except Exception as e:
        print(f"❌ プロファイル取得エラー: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversation/{conversation_id}/tags")
async def update_conversation_tags(conversation_id: int, tags: List[str]):
    """会話のタグを更新"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT metadata FROM conversations WHERE id = ?", (conversation_id,))
        row = c.fetchone()
        
        if row:
            metadata = json.loads(row[0]) if row[0] else {}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        metadata["tags"] = tags
        
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

# ==================== ファインチューニングAPI ====================

@app.get("/api/finetune/available-models")
async def get_available_base_models():
    """ファインチューニング用の利用可能なベースモデル一覧"""
    try:
        result = ollama.list()
        model_list = result.models if hasattr(result, 'models') else []
        
        recommended_models = [
            {
                "value": "gemma2:2b",
                "label": "Gemma 2 2B",
                "category": "軽量",
                "ram_required": "2GB",
                "description": "超軽量・最速、日常会話に最適"
            },
            {
                "value": "gemma3:4b",
                "label": "Gemma 3 4B",
                "category": "軽量",
                "ram_required": "4GB",
                "description": "軽量でバランスの良いモデル"
            },
            {
                "value": "qwen2.5:7b",
                "label": "Qwen 2.5 7B",
                "category": "推奨",
                "ram_required": "8GB",
                "description": "高品質でバランスに優れたモデル",
                "recommended": True
            },
            {
                "value": "gemma3:12b",
                "label": "Gemma 3 12B",
                "category": "高性能",
                "ram_required": "12GB",
                "description": "より高度な理解が可能"
            },
            {
                "value": "qwen2.5:14b",
                "label": "Qwen 2.5 14B",
                "category": "高性能",
                "ram_required": "16GB",
                "description": "高品質な応答を生成"
            },
            {
                "value": "qwen2.5:32b",
                "label": "Qwen 2.5 32B",
                "category": "最高性能",
                "ram_required": "32GB",
                "description": "最高品質、専門的なタスク向け"
            },
            {
                "value": "llama3.1:8b",
                "label": "Llama 3.1 8B",
                "category": "推奨",
                "ram_required": "8GB",
                "description": "Meta製、汎用性が高い"
            },
            {
                "value": "phi3:14b",
                "label": "Phi-3 14B",
                "category": "高性能",
                "ram_required": "16GB",
                "description": "Microsoft製、推論に強い"
            },
        ]
        
        installed_model_names = [m.model if hasattr(m, 'model') else str(m) for m in model_list]
        
        for model in recommended_models:
            model["installed"] = model["value"] in installed_model_names
        
        return {
            "models": recommended_models,
            "installed_count": sum(1 for m in recommended_models if m.get("installed", False))
        }
        
    except Exception as e:
        return {
            "models": [
                {"value": "qwen2.5:7b", "label": "Qwen 2.5 7B", "category": "推奨", "installed": True, "recommended": True}
            ],
            "installed_count": 1
        }

@app.get("/api/finetune/{user_id}/readiness")
async def check_finetuning_readiness(user_id: str):
    """ファインチューニングの準備状況をチェック"""
    try:
        tuning_system = FineTuningSystem()
        readiness = tuning_system.get_tuning_readiness(user_id)
        return readiness
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/finetune/{user_id}")
async def trigger_finetuning(user_id: str, req: FineTuneRequest):
    """ユーザー専用モデルを作成"""
    try:
        tuning_system = FineTuningSystem()
        training_data = tuning_system.collect_training_data(user_id)
        
        if len(training_data) < 10:
            return {
                "status": "insufficient_data",
                "message": f"データが不足しています。現在{len(training_data)}件、最低10件必要です。",
                "current_count": len(training_data),
                "required_count": 10
            }
        
        model_name = tuning_system.fine_tune(user_id, req.base_model)
        
        return {
            "status": "success",
            "model_name": model_name,
            "message": f"ファインチューニング完了: {model_name}",
            "training_size": len(training_data)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ ファインチューニングエラー: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/finetune/{user_id}/models")
async def list_custom_models(user_id: str):
    """ユーザーが作成したカスタムモデル一覧"""
    try:
        tuning_system = FineTuningSystem()
        models = tuning_system.list_user_models(user_id)
        return {"models": models}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/finetune/{user_id}/active")
async def get_active_custom_model(user_id: str):
    """現在アクティブなカスタムモデルを取得"""
    try:
        tuning_system = FineTuningSystem()
        model_name = tuning_system.get_active_model(user_id)
        
        return {
            "has_custom_model": model_name is not None,
            "model_name": model_name
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/finetune/{user_id}/models/{model_name}")
async def delete_custom_model(user_id: str, model_name: str):
    """カスタムモデルを削除"""
    try:
        tuning_system = FineTuningSystem()
        tuning_system.delete_model(user_id, model_name)
        
        return {
            "status": "success",
            "message": f"モデル {model_name} を削除しました"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/finetune/{user_id}/evaluate")
async def evaluate_custom_model(
    user_id: str,
    model_name: str,
    test_prompts: List[str] = ["こんにちは", "調子はどう?", "何か面白い話ある?"]
):
    """カスタムモデルを評価"""
    try:
        tuning_system = FineTuningSystem()
        evaluation = tuning_system.evaluate_model(model_name, test_prompts)
        return evaluation
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== バックグラウンドタスク ====================

async def periodic_message_check():
    """
    定期的にメッセージをチェックして送信
    5分ごとに実行
    """
    while True:
        try:
            # 全ユーザーのメッセージをチェック
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # アクティブなユーザーを取得
            c.execute("""
                SELECT DISTINCT user_id
                FROM conversations
                WHERE timestamp >= datetime('now', '-30 days')
            """)
            
            users = [row[0] for row in c.fetchall()]
            conn.close()
            
            for user_id in users:
                # メッセージをキューに追加
                conversation_initiator.check_and_queue_daily_messages(user_id)
            
            print(f"✅ {len(users)}人のユーザーのメッセージをチェック")
            
        except Exception as e:
            print(f"⚠️ 定期チェックエラー: {e}")
        
        # 5分待機
        await asyncio.sleep(300)


# ==================== AIからのメッセージAPI ====================

@app.get("/api/messages/{user_id}/pending")
async def get_pending_messages_endpoint(user_id: str):
    """
    送信待ちのメッセージを取得
    フロントエンドがポーリングするか、WebSocketで使用
    """
    try:
        messages = conversation_initiator.get_pending_messages(user_id)
        
        # 送信可能なメッセージをフィルタ
        ready_messages = []
        for msg in messages:
            if conversation_initiator.should_send_message_now(
                user_id,
                msg['message_type'],
                msg['scheduled_time']
            ):
                ready_messages.append(msg)
                # 送信済みにマーク
                conversation_initiator.mark_message_sent(msg['id'])
        
        return {
            "has_messages": len(ready_messages) > 0,
            "messages": ready_messages,
            "count": len(ready_messages)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/messages/{user_id}/{message_id}/acknowledge")
async def acknowledge_message_endpoint(user_id: str, message_id: int):
    """ユーザーがメッセージを確認したことを記録"""
    try:
        success = conversation_initiator.mark_message_acknowledged(message_id)
        
        if success:
            # 会話開始履歴に記録
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # メッセージ情報を取得
            c.execute("""
                SELECT message_type, sent_at
                FROM ai_messages_queue
                WHERE id = ?
            """, (message_id,))
            
            row = c.fetchone()
            
            if row:
                message_type, sent_at = row
                
                c.execute("""
                    INSERT INTO conversation_initiations
                    (user_id, initiated_at, message_type, user_responded)
                    VALUES (?, ?, ?, 1)
                """, (user_id, sent_at, message_type))
                
                conn.commit()
            
            conn.close()
            
            return {"status": "success", "message": "確認しました"}
        
        return {"status": "failed", "message": "メッセージが見つかりません"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/messages/{user_id}/{message_id}/respond")
async def respond_to_ai_message_endpoint(
    user_id: str,
    message_id: int,
    response: Dict
):
    """
    AIからのメッセージに返信
    通常のチャットAPIに流すが、コンテキストを保持
    """
    try:
        # メッセージを取得
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT message_type, message_content, metadata
            FROM ai_messages_queue
            WHERE id = ?
        """, (message_id,))
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="メッセージが見つかりません")
        
        message_type, ai_message, metadata_json = row
        metadata = json.loads(metadata_json) if metadata_json else {}
        
        # ユーザーの返信を処理
        user_message = response.get("message", "")
        
        # コンテキストを含めてAIに送信
        context = f"[AIからの質問: {ai_message}]\n\nユーザーの返答: {user_message}"
        
        # 既存のチャットAPIを呼び出し（内部的に）
        # ここでは簡易版
        profile = get_user_profile(user_id)
        
        system_prompt = build_system_prompt(profile)
        system_prompt += f"\n\nあなたは先ほどユーザーに「{ai_message}」と聞きました。"
        
        ollama_response = ollama.chat(
            model="qwen2.5:7b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            options={"temperature": 0.7}
        )
        
        ai_response = ollama_response['message']['content']
        
        # 会話を保存
        conv_id = save_conversation(
            user_id=user_id,
            user_msg=user_message,
            ai_msg=ai_response,
            model="qwen2.5:7b",
            metadata={"triggered_by_ai": True, "message_type": message_type}
        )
        
        # メッセージを確認済みにマーク
        conversation_initiator.mark_message_acknowledged(message_id)
        
        # 応答時間を記録
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT sent_at FROM ai_messages_queue WHERE id = ?
        """, (message_id,))
        
        row = c.fetchone()
        if row:
            sent_at = datetime.fromisoformat(row[0])
            response_time = int((datetime.now() - sent_at).total_seconds())
            
            c.execute("""
                INSERT INTO conversation_initiations
                (user_id, initiated_at, message_type, user_responded, response_time_seconds)
                VALUES (?, ?, ?, 1, ?)
            """, (user_id, sent_at.isoformat(), message_type, response_time))
            
            conn.commit()
        
        conn.close()
        
        # 日記の自動生成判定
        if message_type == "evening_reflection":
            # 夜の振り返りなら日記を生成
            journal_data = {
                "content": user_message,
                "mood": "neutral",  # 後でAIに分析させる
                "energy_level": 5
            }
            
            entry_id = journal_system.create_journal_entry(
                user_id=user_id,
                content=user_message
            )
            
            ai_response += f"\n\n📝 今日の記録を保存しました。"
        
        return {
            "status": "success",
            "conversation_id": conv_id,
            "ai_response": ai_response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages/{user_id}/stats")
async def get_message_stats_endpoint(user_id: str):
    """AIからのメッセージ統計"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 総メッセージ数
        c.execute("""
            SELECT COUNT(*)
            FROM ai_messages_queue
            WHERE user_id = ? AND sent = 1
        """, (user_id,))
        
        total_sent = c.fetchone()[0]
        
        # 確認されたメッセージ数
        c.execute("""
            SELECT COUNT(*)
            FROM ai_messages_queue
            WHERE user_id = ? AND acknowledged = 1
        """, (user_id,))
        
        acknowledged = c.fetchone()[0]
        
        # 平均応答時間
        c.execute("""
            SELECT AVG(response_time_seconds)
            FROM conversation_initiations
            WHERE user_id = ? AND user_responded = 1
        """, (user_id,))
        
        avg_response_time = c.fetchone()[0] or 0
        
        # メッセージタイプ別の統計
        c.execute("""
            SELECT message_type, COUNT(*)
            FROM ai_messages_queue
            WHERE user_id = ? AND sent = 1
            GROUP BY message_type
        """, (user_id,))
        
        by_type = {row[0]: row[1] for row in c.fetchall()}
        
        conn.close()
        
        return {
            "total_sent": total_sent,
            "acknowledged": acknowledged,
            "acknowledgement_rate": round(acknowledged / total_sent * 100, 1) if total_sent > 0 else 0,
            "avg_response_time_seconds": round(avg_response_time, 1),
            "by_type": by_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ユーザーパターン管理API ====================

@app.get("/api/patterns/{user_id}")
async def get_user_patterns_endpoint(user_id: str):
    """ユーザーの活動パターンを取得"""
    try:
        patterns = conversation_initiator.get_user_patterns(user_id)
        return {"patterns": patterns}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/patterns/{user_id}/update")
async def update_user_patterns_endpoint(user_id: str, patterns: Dict):
    """ユーザーの好みを更新"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            INSERT OR REPLACE INTO user_activity_patterns
            (user_id, typical_morning_time, typical_evening_time,
             quiet_hours_start, quiet_hours_end, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            patterns.get('typical_morning_time', '08:00'),
            patterns.get('typical_evening_time', '20:00'),
            patterns.get('quiet_hours_start'),
            patterns.get('quiet_hours_end'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "パターンを更新しました"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/patterns/{user_id}/learn")
async def learn_user_patterns_endpoint(user_id: str):
    """会話履歴からパターンを学習"""
    try:
        patterns = conversation_initiator.learn_user_patterns(user_id)
        return {
            "status": "success",
            "patterns": patterns,
            "message": "活動パターンを学習しました"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 手動メッセージトリガーAPI ====================

@app.post("/api/messages/{user_id}/trigger")
async def trigger_manual_message_endpoint(user_id: str, trigger: Dict):
    """特定のメッセージを手動でトリガー"""
    try:
        message_type = trigger.get("type")
        
        # メッセージ生成
        if message_type == "morning_checkin":
            msg = conversation_initiator.generate_morning_checkin(user_id)
        elif message_type == "evening_reflection":
            msg = conversation_initiator.generate_evening_reflection(user_id)
        elif message_type == "weekly_review":
            msg = conversation_initiator.generate_weekly_review_prompt(user_id)
        elif message_type == "encouragement":
            context = trigger.get("context", "struggling")
            msg = conversation_initiator.generate_encouragement(user_id, context)
        else:
            raise HTTPException(status_code=400, detail="不明なメッセージタイプ")
        
        # キューに追加
        message_id = conversation_initiator.queue_message(
            user_id=user_id,
            message_type=msg['type'],
            priority=msg['priority'],
            content=msg['content'],
            scheduled_time=datetime.now().isoformat()
        )
        
        # 即座に送信
        conversation_initiator.mark_message_sent(message_id)
        
        return {
            "status": "success",
            "message_id": message_id,
            "content": msg['content']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ダッシュボードの拡張 ====================

# main.py に以下を追加

@app.get("/api/dashboard/{user_id}")
async def get_daily_dashboard(user_id: str):
    """ダッシュボード用データ取得"""
    try:
        # DB接続を作成
        conn = sqlite3.connect(DB_PATH)
        
        # schedule_managerに一時的に接続を渡す
        schedule_manager.conn = conn
        
        # データ取得
        plan = schedule_manager.suggest_daily_plan(user_id)
        
        # 接続をクローズ
        conn.close()
        schedule_manager.conn = None
        
        return plan
        
    except Exception as e:
        print(f"❌ ダッシュボードエラー: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/habits/{user_id}")
async def get_habits(user_id: str):
    """習慣一覧取得"""
    try:
        # DB接続を作成
        conn = sqlite3.connect(DB_PATH)
        
        # schedule_managerに一時的に接続を渡す
        schedule_manager.conn = conn
        
        # データ取得
        habits = schedule_manager.get_habits(user_id)
        
        # 接続をクローズ
        conn.close()
        schedule_manager.conn = None
        
        return {"habits": habits}
        
    except Exception as e:
        print(f"❌ 習慣取得エラー: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/habits/{user_id}/{habit_id}/complete")
async def complete_habit(user_id: str, habit_id: int):
    """習慣完了チェック"""
    try:
        # DB接続を作成
        conn = sqlite3.connect(DB_PATH)
        
        # schedule_managerに一時的に接続を渡す
        schedule_manager.conn = conn
        
        # 習慣完了処理
        success = schedule_manager.mark_habit_completed(habit_id)
        
        # 接続をクローズ
        conn.close()
        schedule_manager.conn = None
        
        return {"status": "success", "updated": success}
        
    except Exception as e:
        print(f"❌ 習慣更新エラー: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の初期化 - 全て統合"""
    global analyzer, rag_system, schedule_manager, assistant_brain
    global goal_manager, journal_system, conversation_initiator
    
    print("=" * 50)
    print("🚀 パートナーAI システム起動中...")
    print("=" * 50)
    
    # 1. 基本システム（DB不要）
    analyzer = ConversationAnalyzer(model="gemma3:4b")
    print("✅ 会話分析システム初期化完了")
    
    rag_system = RAGSystem(persist_directory="./chroma_db")
    print("✅ RAGシステム初期化完了")
    
    # 2. DB必要なシステム（Noneで初期化）
    schedule_manager = ScheduleManager(None)
    print("✅ スケジュール管理システム初期化完了")
    
    assistant_brain = AssistantBrain(schedule_manager)
    print("✅ AIアシスタント脳初期化完了")
    
    goal_manager = GoalManager(None)
    print("✅ 目標管理システム初期化完了")
    
    journal_system = JournalSystem(None)
    print("✅ 日記システム初期化完了")
    
    conversation_initiator = ConversationInitiator(
        None, goal_manager, journal_system, schedule_manager
    )
    print("✅ 能動的会話システム初期化完了")
    
    # 3. データベーステーブル初期化（1回だけ実行）
    print("📊 データベーステーブル初期化中...")
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # 各システムに一時的に接続を渡してテーブル作成
        schedule_manager.conn = conn
        schedule_manager._init_tables()
        
        goal_manager.conn = conn
        goal_manager._init_tables()
        
        journal_system.conn = conn
        journal_system._init_tables()
        
        conversation_initiator.conn = conn
        conversation_initiator._init_tables()
        
        conn.close()
        print("✅ データベーステーブル初期化完了")
        
    except Exception as e:
        print(f"⚠️ データベース初期化エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 接続をNoneに戻す（各APIで必要時に再接続）
        schedule_manager.conn = None
        goal_manager.conn = None
        journal_system.conn = None
        conversation_initiator.conn = None
    
    # 4. バックグラウンドタスク開始
    asyncio.create_task(periodic_message_check())
    print("✅ バックグラウンドタスク開始")
    
    print("=" * 50)
    print("🎉 全システム初期化完了！")
    print("=" * 50)


# ==================== スケジュール管理API ====================

@app.post("/api/schedules/{user_id}")
async def create_schedule_endpoint(user_id: str, schedule: Dict):
    """スケジュール作成"""
    try:
        # 競合チェック
        conflicts = schedule_manager.check_schedule_conflicts(
            user_id,
            schedule["start_time"],
            schedule.get("end_time", schedule["start_time"])
        )
        
        if conflicts:
            return {
                "status": "warning",
                "conflicts": conflicts,
                "message": "他の予定と重複しています。それでも作成しますか？"
            }
        
        schedule_id = schedule_manager.create_schedule(
            user_id=user_id,
            title=schedule["title"],
            start_time=schedule["start_time"],
            end_time=schedule.get("end_time"),
            description=schedule.get("description", ""),
            location=schedule.get("location", ""),
            attendees=schedule.get("attendees", []),
            reminder_minutes=schedule.get("reminder_minutes", 15)
        )
        
        return {
            "status": "success",
            "schedule_id": schedule_id,
            "message": f"スケジュール「{schedule['title']}」を作成しました"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# main.py に以下のエンドポイントを追加

# ==================== スケジュール管理API ====================

@app.get("/api/schedules/{user_id}")
async def get_schedules(user_id: str, days: int = 7):
    """スケジュール一覧取得"""
    try:
        conn = sqlite3.connect(DB_PATH)
        schedule_manager.conn = conn
        
        schedules = schedule_manager.get_upcoming_schedules(user_id, days=days)
        
        conn.close()
        schedule_manager.conn = None
        
        return {"schedules": schedules, "total": len(schedules)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/schedules/{schedule_id}")
async def update_schedule(schedule_id: int, data: Dict):
    """スケジュール更新"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 更新可能なフィールド
        allowed_fields = ['title', 'description', 'start_time', 'end_time', 'location']
        
        updates = []
        values = []
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                values.append(data[field])
        
        if updates:
            values.append(schedule_id)
            c.execute(f"""
                UPDATE schedules
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            conn.commit()
        
        conn.close()
        
        return {"status": "success", "message": "スケジュールを更新しました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int):
    """スケジュール削除"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "スケジュールを削除しました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== タスク管理API ====================

@app.get("/api/tasks/{user_id}")
async def get_tasks(user_id: str):
    """タスク一覧取得"""
    try:
        conn = sqlite3.connect(DB_PATH)
        schedule_manager.conn = conn
        
        tasks = schedule_manager.get_pending_tasks(user_id)
        
        conn.close()
        schedule_manager.conn = None
        
        return {"tasks": tasks, "total": len(tasks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: int, data: Dict):
    """タスク更新"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 更新可能なフィールド
        allowed_fields = ['title', 'description', 'due_date', 'priority', 'status']
        
        updates = []
        values = []
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                values.append(data[field])
        
        if updates:
            values.append(task_id)
            c.execute(f"""
                UPDATE tasks
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            conn.commit()
        
        conn.close()
        
        return {"status": "success", "message": "タスクを更新しました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/complete")
async def complete_task_endpoint(task_id: int):
    """タスク完了"""
    try:
        conn = sqlite3.connect(DB_PATH)
        schedule_manager.conn = conn
        
        success = schedule_manager.complete_task(task_id)
        
        conn.close()
        schedule_manager.conn = None
        
        return {"status": "success", "completed": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    """タスク削除"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "タスクを削除しました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 目標管理API ====================

@app.get("/api/goals/{user_id}")
async def get_goals(user_id: str):
    """目標一覧取得"""
    try:
        conn = sqlite3.connect(DB_PATH)
        goal_manager.conn = conn
        
        goals = goal_manager.get_active_goals(user_id)
        
        conn.close()
        goal_manager.conn = None
        
        return {"goals": goals, "total": len(goals)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/goals/{goal_id}")
async def update_goal(goal_id: int, data: Dict):
    """目標更新"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        allowed_fields = ['title', 'description', 'target_date', 'status', 'progress_percentage']
        
        updates = []
        values = []
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                values.append(data[field])
        
        if updates:
            values.append(goal_id)
            c.execute(f"""
                UPDATE goals
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            conn.commit()
        
        conn.close()
        
        return {"status": "success", "message": "目標を更新しました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/goals/{goal_id}")
async def delete_goal(goal_id: int):
    """目標削除"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "目標を削除しました"}
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