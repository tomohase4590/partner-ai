"""
task_manager.py
AIがユーザーのタスクを管理・サポート
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

class TaskManager:
    """タスク管理システム"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
        self._init_task_tables()
    
    def _init_task_tables(self):
        """タスク関連テーブルの初期化"""
        c = self.conn.cursor()
        
        # タスクテーブル
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                reminder_sent INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        # サブタスク
        c.execute("""
            CREATE TABLE IF NOT EXISTS subtasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # 習慣トラッカー
        c.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                frequency TEXT NOT NULL,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                last_completed TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        self.conn.commit()
    
    def extract_task_from_conversation(self, user_message: str) -> Optional[Dict]:
        """
        会話からタスクを自動抽出
        「明日までにレポート書かないと」→ タスク化
        """
        
        # キーワード検出
        task_indicators = [
            "やらないと", "しなきゃ", "する必要がある",
            "締め切り", "期限", "までに",
            "忘れないように", "覚えておいて"
        ]
        
        has_task_indicator = any(kw in user_message for kw in task_indicators)
        
        if not has_task_indicator:
            return None
        
        # Ollamaでタスク詳細を抽出
        prompt = f"""以下のメッセージからタスク情報を抽出してください。

メッセージ: {user_message}

以下のJSON形式で返してください:
{{
  "has_task": true/false,
  "title": "タスクのタイトル",
  "description": "詳細説明",
  "due_date": "YYYY-MM-DD形式または相対日付",
  "priority": "high/medium/low"
}}
"""
        # 実装...
        
    def create_task(
        self,
        user_id: str,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        priority: str = "medium"
    ) -> int:
        """タスク作成"""
        c = self.conn.cursor()
        
        c.execute("""
            INSERT INTO tasks (user_id, title, description, due_date, priority, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, title, description, due_date, priority, datetime.now().isoformat()))
        
        task_id = c.lastrowid
        self.conn.commit()
        
        return task_id
    
    def get_pending_tasks(self, user_id: str) -> List[Dict]:
        """未完了タスク一覧"""
        c = self.conn.cursor()
        
        c.execute("""
            SELECT id, title, description, due_date, priority, created_at
            FROM tasks
            WHERE user_id = ? AND status = 'pending'
            ORDER BY 
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                due_date ASC
        """, (user_id,))
        
        tasks = []
        for row in c.fetchall():
            tasks.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "due_date": row[3],
                "priority": row[4],
                "created_at": row[5]
            })
        
        return tasks
    
    def check_overdue_tasks(self, user_id: str) -> List[Dict]:
        """期限切れタスクをチェック"""
        c = self.conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        c.execute("""
            SELECT id, title, due_date
            FROM tasks
            WHERE user_id = ? 
              AND status = 'pending'
              AND due_date < ?
        """, (user_id, today))
        
        return [{"id": r[0], "title": r[1], "due_date": r[2]} for r in c.fetchall()]
    
    def suggest_daily_focus(self, user_id: str) -> Dict:
        """今日集中すべきタスクを提案"""
        pending = self.get_pending_tasks(user_id)
        overdue = self.check_overdue_tasks(user_id)
        
        # 優先度の高いタスクと期限が近いタスクを抽出
        today = datetime.now().date()
        
        urgent_tasks = []
        for task in pending:
            if task["priority"] == "high":
                urgent_tasks.append(task)
            elif task["due_date"]:
                due = datetime.fromisoformat(task["due_date"]).date()
                days_left = (due - today).days
                if days_left <= 3:
                    urgent_tasks.append(task)
        
        return {
            "overdue_count": len(overdue),
            "urgent_tasks": urgent_tasks[:3],
            "total_pending": len(pending),
            "suggestion": self._generate_focus_suggestion(urgent_tasks, overdue)
        }
    
    def _generate_focus_suggestion(self, urgent: List[Dict], overdue: List[Dict]) -> str:
        """集中タスクの提案メッセージ生成"""
        if overdue:
            return f"まず期限切れの{len(overdue)}件のタスクから片付けましょう！"
        elif urgent:
            return f"今日は「{urgent[0]['title']}」に集中するのはいかがですか?"
        else:
            return "素晴らしい！緊急のタスクはありません。余裕をもって取り組めますね。"