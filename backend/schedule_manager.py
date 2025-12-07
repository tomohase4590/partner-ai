"""
schedule_manager.py
統合スケジュール管理・タスク・習慣サポートシステム
AIが秘書のように働く
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import ollama
import re


class ScheduleManager:
    """スケジュール・タスク・習慣統合管理システム"""
    
    def __init__(self, db_connection, model: str = "gemma3:4b"):
        self.conn = db_connection
        self.model = model
        if self.conn is not None: # ← この行を追加
            self._init_tables()
    
    def _init_tables(self):
        """テーブル初期化"""
        c = self.conn.cursor()
        
        # 1. スケジュールテーブル
        c.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                location TEXT,
                attendees TEXT,
                reminder_minutes INTEGER DEFAULT 15,
                status TEXT DEFAULT 'scheduled',
                created_at TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # 2. タスクテーブル（統合）
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                estimated_minutes INTEGER,
                actual_minutes INTEGER,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                parent_task_id INTEGER,
                metadata TEXT
            )
        """)
        
        # 3. サブタスク（追加）
        c.execute("""
            CREATE TABLE IF NOT EXISTS subtasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # 4. 習慣トラッカー（追加）
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
        
        # 5. タスク進捗ログ
        c.execute("""
            CREATE TABLE IF NOT EXISTS task_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                progress_percentage INTEGER,
                notes TEXT,
                mood TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # 6. 作業セッション
        c.execute("""
            CREATE TABLE IF NOT EXISTS work_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                task_id INTEGER,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_minutes INTEGER,
                session_type TEXT DEFAULT 'focus',
                notes TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        self.conn.commit()
    
    # ==================== スケジュール管理 ====================
    
    def extract_schedule_from_text(self, user_message: str) -> Optional[Dict]:
        """自然言語からスケジュール情報を抽出（改善版）"""
        
        # より詳細なプロンプト
        prompt = f"""以下のメッセージからスケジュール情報を抽出してください。

    メッセージ: {user_message}

    重要な判定基準:
    - 「〇〇をする」だけの場合はスケジュールではなくタスク
    - 「明日14時に」「来週の月曜に」など時刻や日時が明確な場合のみスケジュール
    - 「いつか」「そのうち」「〇〇したい」はタスクか目標

    以下のJSON形式で返してください（JSONのみ、他の文字は含めない）:
    {{
    "has_schedule": true/false,
    "title": "予定のタイトル",
    "description": "詳細説明",
    "start_time": "YYYY-MM-DD HH:MM形式（必須）",
    "end_time": "YYYY-MM-DD HH:MM形式（あれば）",
    "location": "場所（あれば）",
    "attendees": ["参加者リスト"]
    }}

    判定ルール:
    - start_timeが特定できない場合は has_schedule: false にする
    - 時刻が不明な場合は has_schedule: false にする
    - 「〇〇する」だけの文はスケジュールではない

    現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    今日の日付: {datetime.now().strftime('%Y-%m-%d')}
    明日の日付: {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}
    """
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.2}  # より確実な判定のため低めに
            )
            
            content = response['message']['content']
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # start_timeの検証
                if result.get("has_schedule"):
                    start_time = result.get("start_time", "")
                    
                    # 時刻が含まれているか確認（HH:MMフォーマット）
                    if not re.search(r'\d{2}:\d{2}', start_time):
                        print(f"⚠️ スケジュール判定: 時刻が不明確なため除外 - {result.get('title')}")
                        return None
                    
                    # 日付の妥当性確認
                    try:
                        datetime.fromisoformat(start_time)
                    except:
                        print(f"⚠️ スケジュール判定: 日時形式が不正 - {start_time}")
                        return None
                
                return result if result.get("has_schedule") else None
            
        except Exception as e:
            print(f"⚠️ スケジュール抽出エラー: {e}")
        
        return None
    
    def create_schedule(
        self,
        user_id: str,
        title: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: str = "",
        location: str = "",
        attendees: List[str] = None,
        reminder_minutes: int = 15
    ) -> int:
        """スケジュール作成"""
        c = self.conn.cursor()
        
        metadata = {
            "attendees": attendees or []
        }
        
        c.execute("""
            INSERT INTO schedules 
            (user_id, title, description, start_time, end_time, location, 
             attendees, reminder_minutes, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, title, description, start_time, end_time, location,
            json.dumps(attendees or []), reminder_minutes,
            datetime.now().isoformat(), json.dumps(metadata)
        ))
        
        schedule_id = c.lastrowid
        self.conn.commit()
        
        return schedule_id
    
    def get_today_schedule(self, user_id: str) -> List[Dict]:
        """今日のスケジュール取得"""
        c = self.conn.cursor()
        
        today = datetime.now().date().isoformat()
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        
        c.execute("""
            SELECT id, title, description, start_time, end_time, location, status
            FROM schedules
            WHERE user_id = ? 
              AND start_time >= ?
              AND start_time < ?
              AND status != 'cancelled'
            ORDER BY start_time ASC
        """, (user_id, today, tomorrow))
        
        schedules = []
        for row in c.fetchall():
            schedules.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "start_time": row[3],
                "end_time": row[4],
                "location": row[5],
                "status": row[6]
            })
        
        return schedules
    
    def get_upcoming_schedules(self, user_id: str, days: int = 7) -> List[Dict]:
        """今後の予定取得"""
        c = self.conn.cursor()
        
        today = datetime.now().date().isoformat()
        future = (datetime.now().date() + timedelta(days=days)).isoformat()
        
        c.execute("""
            SELECT id, title, start_time, end_time, location
            FROM schedules
            WHERE user_id = ?
              AND start_time >= ?
              AND start_time < ?
              AND status = 'scheduled'
            ORDER BY start_time ASC
        """, (user_id, today, future))
        
        return [
            {
                "id": r[0], "title": r[1], "start_time": r[2],
                "end_time": r[3], "location": r[4]
            }
            for r in c.fetchall()
        ]
    
    def check_schedule_conflicts(
        self, 
        user_id: str, 
        start_time: str, 
        end_time: str
    ) -> List[Dict]:
        """スケジュール競合チェック"""
        c = self.conn.cursor()
        
        c.execute("""
            SELECT id, title, start_time, end_time
            FROM schedules
            WHERE user_id = ?
              AND status = 'scheduled'
              AND (
                  (start_time < ? AND end_time > ?)
                  OR (start_time < ? AND end_time > ?)
                  OR (start_time >= ? AND end_time <= ?)
              )
        """, (user_id, end_time, start_time, end_time, start_time, start_time, end_time))
        
        conflicts = []
        for row in c.fetchall():
            conflicts.append({
                "id": row[0],
                "title": row[1],
                "start_time": row[2],
                "end_time": row[3]
            })
        
        return conflicts
    
    # ==================== タスク管理 ====================
    
    def extract_task_from_text(self, user_message: str) -> Optional[Dict]:
        """自然言語からタスク情報を抽出（改善版）"""
        
        prompt = f"""以下のメッセージからタスク情報を抽出してください。

    メッセージ: {user_message}

    タスクの判定基準:
    - 「〇〇する」「〇〇しないと」「〇〇したい」→ タスク
    - 期限が明示されている、または期限が推測できる
    - 「いつか」「そのうち」は期限なしタスク
    - 「来週まで」「明日まで」など期限がある

    以下のJSON形式で返してください（JSONのみ）:
    {{
    "has_task": true/false,
    "title": "タスクのタイトル",
    "description": "詳細説明",
    "due_date": "YYYY-MM-DD形式（期限があれば）",
    "priority": "high/medium/low",
    "estimated_minutes": 60,
    "subtasks": ["サブタスク1", "サブタスク2"]
    }}

    優先度の判定:
    - 「急ぎ」「すぐに」「今日中」→ high
    - 「来週まで」「そのうち」→ medium
    - 「いつか」「できれば」→ low

    現在日時: {datetime.now().strftime('%Y-%m-%d')}
    今日: {datetime.now().strftime('%Y-%m-%d')}
    明日: {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}
    来週: {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}
    """
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3}
            )
            
            content = response['message']['content']
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # due_dateの妥当性確認
                if result.get("has_task") and result.get("due_date"):
                    try:
                        due_date = datetime.fromisoformat(result["due_date"])
                        # 過去の日付は今日に修正
                        if due_date.date() < datetime.now().date():
                            result["due_date"] = datetime.now().date().isoformat()
                            print(f"⚠️ タスク期限を今日に修正: {result['title']}")
                    except:
                        # 日付が不正な場合は削除
                        result["due_date"] = None
                        print(f"⚠️ タスク期限が不正なため削除: {result.get('title')}")
                
                return result if result.get("has_task") else None
            
        except Exception as e:
            print(f"⚠️ タスク抽出エラー: {e}")
        
        return None
    
    def create_task(
        self,
        user_id: str,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        priority: str = "medium",
        estimated_minutes: Optional[int] = None,
        parent_task_id: Optional[int] = None
    ) -> int:
        """タスク作成"""
        c = self.conn.cursor()
        
        c.execute("""
            INSERT INTO tasks
            (user_id, title, description, due_date, priority, 
             estimated_minutes, parent_task_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, title, description, due_date, priority,
            estimated_minutes, parent_task_id, datetime.now().isoformat()
        ))
        
        task_id = c.lastrowid
        self.conn.commit()
        
        return task_id
    
    def get_pending_tasks(self, user_id: str) -> List[Dict]:
        """未完了タスク一覧"""
        c = self.conn.cursor()
        
        c.execute("""
            SELECT id, title, description, due_date, priority, 
                   estimated_minutes, created_at, parent_task_id
            FROM tasks
            WHERE user_id = ? AND status = 'pending'
            ORDER BY 
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                due_date ASC NULLS LAST
        """, (user_id,))
        
        tasks = []
        for row in c.fetchall():
            tasks.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "due_date": row[3],
                "priority": row[4],
                "estimated_minutes": row[5],
                "created_at": row[6],
                "parent_task_id": row[7]
            })
        
        return tasks
    
    def check_overdue_tasks(self, user_id: str) -> List[Dict]:
        """期限切れタスクをチェック"""
        c = self.conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        c.execute("""
            SELECT id, title, due_date, priority
            FROM tasks
            WHERE user_id = ? 
              AND status = 'pending'
              AND due_date < ?
        """, (user_id, today))
        
        return [
            {"id": r[0], "title": r[1], "due_date": r[2], "priority": r[3]} 
            for r in c.fetchall()
        ]
    
    def start_task(self, task_id: int) -> bool:
        """タスク開始"""
        c = self.conn.cursor()
        
        c.execute("""
            UPDATE tasks
            SET status = 'in_progress', started_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), task_id))
        
        self.conn.commit()
        return c.rowcount > 0
    
    def complete_task(self, task_id: int, actual_minutes: Optional[int] = None) -> bool:
        """タスク完了"""
        c = self.conn.cursor()
        
        c.execute("""
            UPDATE tasks
            SET status = 'completed', 
                completed_at = ?,
                actual_minutes = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), actual_minutes, task_id))
        
        self.conn.commit()
        return c.rowcount > 0
    
    def update_task_progress(
        self,
        task_id: int,
        progress_percentage: int,
        notes: str = "",
        mood: str = "neutral"
    ) -> int:
        """タスク進捗更新"""
        c = self.conn.cursor()
        
        c.execute("""
            INSERT INTO task_progress
            (task_id, timestamp, progress_percentage, notes, mood)
            VALUES (?, ?, ?, ?, ?)
        """, (task_id, datetime.now().isoformat(), progress_percentage, notes, mood))
        
        progress_id = c.lastrowid
        self.conn.commit()
        
        return progress_id
    
    # ==================== 習慣管理（追加機能） ====================
    
    def create_habit(self, user_id: str, title: str, frequency: str = "daily") -> int:
        """習慣を作成"""
        c = self.conn.cursor()
        
        c.execute("""
            INSERT INTO habits
            (user_id, title, frequency, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, title, frequency, datetime.now().isoformat()))
        
        habit_id = c.lastrowid
        self.conn.commit()
        
        return habit_id
    
    def get_habits(self, user_id: str) -> List[Dict]:
        """習慣一覧を取得"""
        c = self.conn.cursor()
        
        c.execute("""
            SELECT id, title, frequency, current_streak, last_completed
            FROM habits
            WHERE user_id = ?
        """, (user_id,))
        
        return [
            {
                "id": r[0], "title": r[1], "frequency": r[2],
                "current_streak": r[3], "last_completed": r[4]
            }
            for r in c.fetchall()
        ]
    
    def mark_habit_completed(self, habit_id: int) -> bool:
        """習慣を完了（ストリーク更新ロジック含む）"""
        c = self.conn.cursor()
        now = datetime.now()
        today_str = now.date().isoformat()
        
        # 現在の状態を取得
        c.execute("SELECT current_streak, last_completed FROM habits WHERE id = ?", (habit_id,))
        row = c.fetchone()
        
        if not row:
            return False
            
        current_streak, last_completed = row
        
        # 最後に完了したのが今日なら更新しない
        if last_completed and last_completed.startswith(today_str):
            return False
        
        # ストリーク計算（昨日完了していれば+1、そうでなければ1にリセット）
        yesterday_str = (now - timedelta(days=1)).date().isoformat()
        
        if last_completed and last_completed.startswith(yesterday_str):
            new_streak = current_streak + 1
        else:
            new_streak = 1
            
        c.execute("""
            UPDATE habits 
            SET current_streak = ?, best_streak = MAX(best_streak, ?), last_completed = ?
            WHERE id = ?
        """, (new_streak, new_streak, now.isoformat(), habit_id))
        
        self.conn.commit()
        return True
    
    # ==================== タスクサポート ====================
    
    def break_down_task(self, task_title: str, task_description: str) -> List[str]:
        """タスクを細かいステップに分解"""
        
        prompt = f"""以下のタスクを実行可能な小さなステップに分解してください。

タスク: {task_title}
詳細: {task_description}

以下のJSON形式で返してください（JSONのみ）:
{{
  "steps": [
    "ステップ1",
    "ステップ2",
    "ステップ3"
  ],
  "estimated_time_per_step": [30, 60, 45]
}}
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.5}
            )
            
            content = response['message']['content']
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result.get("steps", [])
            
        except Exception as e:
            print(f"⚠️ タスク分解エラー: {e}")
        
        return []
    
    def suggest_task_strategy(
        self,
        task_title: str,
        task_description: str,
        user_energy_level: str = "medium"
    ) -> str:
        """タスク遂行の戦略を提案"""
        
        prompt = f"""以下のタスクを効率的に遂行する戦略を提案してください。

タスク: {task_title}
詳細: {task_description}
ユーザーの現在のエネルギーレベル: {user_energy_level}

以下の観点で提案してください:
1. 最適な取り組み方
2. 集中すべきポイント
3. 注意すべき落とし穴
4. モチベーション維持のコツ

簡潔に3-4文で回答してください。
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7}
            )
            
            return response['message']['content']
            
        except Exception as e:
            print(f"⚠️ 戦略提案エラー: {e}")
            return "タスクを小さなステップに分けて、一つずつ確実に進めていきましょう。"
    
    def analyze_task_difficulty(self, task_title: str, task_description: str) -> Dict:
        """タスクの難易度を分析"""
        
        prompt = f"""以下のタスクの難易度を分析してください。

タスク: {task_title}
詳細: {task_description}

以下のJSON形式で返してください（JSONのみ）:
{{
  "difficulty": "easy/medium/hard",
  "required_skills": ["スキル1", "スキル2"],
  "estimated_hours": 2.5,
  "complexity_factors": ["要因1", "要因2"]
}}
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3}
            )
            
            content = response['message']['content']
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            print(f"⚠️ 難易度分析エラー: {e}")
        
        return {"difficulty": "medium", "estimated_hours": 1}
    
    # ==================== 作業セッション ====================
    
    def start_work_session(
        self,
        user_id: str,
        task_id: Optional[int] = None,
        session_type: str = "focus"
    ) -> int:
        """作業セッション開始"""
        c = self.conn.cursor()
        
        c.execute("""
            INSERT INTO work_sessions
            (user_id, task_id, start_time, session_type)
            VALUES (?, ?, ?, ?)
        """, (user_id, task_id, datetime.now().isoformat(), session_type))
        
        session_id = c.lastrowid
        self.conn.commit()
        
        return session_id
    
    def end_work_session(self, session_id: int, notes: str = "") -> Dict:
        """作業セッション終了"""
        c = self.conn.cursor()
        
        # セッション情報取得
        c.execute("""
            SELECT start_time, task_id
            FROM work_sessions
            WHERE id = ?
        """, (session_id,))
        
        row = c.fetchone()
        if not row:
            return {"error": "Session not found"}
        
        start_time = datetime.fromisoformat(row[0])
        task_id = row[1]
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds() / 60)
        
        # セッション更新
        c.execute("""
            UPDATE work_sessions
            SET end_time = ?, duration_minutes = ?, notes = ?
            WHERE id = ?
        """, (end_time.isoformat(), duration, notes, session_id))
        
        self.conn.commit()
        
        return {
            "session_id": session_id,
            "task_id": task_id,
            "duration_minutes": duration,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    
    def get_work_statistics(self, user_id: str, days: int = 7) -> Dict:
        """作業統計"""
        c = self.conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # 総作業時間
        c.execute("""
            SELECT SUM(duration_minutes)
            FROM work_sessions
            WHERE user_id = ? AND start_time >= ?
        """, (user_id, start_date))
        
        total_minutes = c.fetchone()[0] or 0
        
        # 完了タスク数
        c.execute("""
            SELECT COUNT(*)
            FROM tasks
            WHERE user_id = ? 
              AND status = 'completed'
              AND completed_at >= ?
        """, (user_id, start_date))
        
        completed_tasks = c.fetchone()[0]
        
        return {
            "period_days": days,
            "total_work_minutes": total_minutes,
            "total_work_hours": round(total_minutes / 60, 1),
            "completed_tasks": completed_tasks,
            "average_daily_minutes": round(total_minutes / days, 1)
        }
    
    # ==================== インテリジェント提案 ====================
    
    def suggest_daily_plan(self, user_id: str) -> Dict:
        """今日の計画を提案"""
        
        # 今日のスケジュール
        schedules = self.get_today_schedule(user_id)
        
        # 未完了タスク
        tasks = self.get_pending_tasks(user_id)
        
        # 優先タスク抽出
        urgent_tasks = [t for t in tasks if t["priority"] == "high"]
        
        # 今日が期限のタスク
        today = datetime.now().date().isoformat()
        due_today = [t for t in tasks if t.get("due_date") == today]
        
        # 空き時間計算
        free_slots = self._calculate_free_time(schedules)
        
        suggestion = {
            "schedules": schedules,
            "urgent_tasks": urgent_tasks[:3],
            "due_today": due_today,
            "free_time_slots": free_slots,
            "recommendation": self._generate_plan_recommendation(
                schedules, urgent_tasks, due_today, free_slots
            )
        }
        
        return suggestion
    
    def _calculate_free_time(self, schedules: List[Dict]) -> List[Dict]:
        """空き時間を計算"""
        if not schedules:
            return [{"start": "09:00", "end": "18:00", "duration_minutes": 540}]
        
        free_slots = []
        work_start = datetime.now().replace(hour=9, minute=0, second=0)
        
        # 簡易実装
        if schedules:
            first_schedule = datetime.fromisoformat(schedules[0]["start_time"])
            if first_schedule > work_start:
                duration = int((first_schedule - work_start).total_seconds() / 60)
                if duration > 30:
                    free_slots.append({
                        "start": work_start.strftime("%H:%M"),
                        "end": first_schedule.strftime("%H:%M"),
                        "duration_minutes": duration
                    })
        
        return free_slots
    
    def _generate_plan_recommendation(
        self,
        schedules: List[Dict],
        urgent_tasks: List[Dict],
        due_today: List[Dict],
        free_slots: List[Dict]
    ) -> str:
        """計画の推奨メッセージ生成"""
        
        messages = []
        
        if schedules:
            messages.append(f"今日は{len(schedules)}件の予定があります。")
        
        if due_today:
            task_titles = ", ".join([t["title"] for t in due_today[:2]])
            messages.append(f"期限が今日のタスク: {task_titles}")
        
        if urgent_tasks:
            messages.append(f"優先度の高いタスクが{len(urgent_tasks)}件あります。")
        
        if free_slots and free_slots[0]["duration_minutes"] > 60:
            slot = free_slots[0]
            messages.append(
                f"{slot['start']}〜{slot['end']}に{slot['duration_minutes']}分の空き時間があります。"
                "集中作業に使いましょう。"
            )
        
        return " ".join(messages) if messages else "今日は余裕のあるスケジュールです。"