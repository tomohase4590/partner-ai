"""
goal_journal_system.py
長期目標管理・日記・振り返りシステム
AIが人生のパートナーとして目標達成をサポート
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import ollama


class GoalManager:
    """長期目標管理システム"""
    
    def __init__(self, db_connection, model: str = "qwen2.5:7b"):
        self.conn = db_connection
        self.model = model
        if self.conn is not None: # ← この行を追加
            self._init_tables()
    
    def _init_tables(self):
        """テーブル初期化"""
        c = self.conn.cursor()
        
        # 目標テーブル
        c.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                target_date TEXT,
                status TEXT DEFAULT 'active',
                progress_percentage INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                metadata TEXT
            )
        """)
        
        # マイルストーン（中間目標）
        c.execute("""
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                target_date TEXT,
                completed INTEGER DEFAULT 0,
                completed_at TEXT,
                FOREIGN KEY (goal_id) REFERENCES goals(id)
            )
        """)
        
        # 目標進捗ログ
        c.execute("""
            CREATE TABLE IF NOT EXISTS goal_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                progress_percentage INTEGER,
                notes TEXT,
                achievements TEXT,
                challenges TEXT,
                FOREIGN KEY (goal_id) REFERENCES goals(id)
            )
        """)
        
        # 振り返りメモ
        c.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER,
                timestamp TEXT NOT NULL,
                reflection_type TEXT DEFAULT 'weekly',
                content TEXT NOT NULL,
                insights TEXT,
                action_items TEXT,
                FOREIGN KEY (goal_id) REFERENCES goals(id)
            )
        """)
        
        self.conn.commit()
    
    # ==================== 目標作成・管理 ====================
    
    def create_goal(
        self,
        user_id: str,
        title: str,
        description: str = "",
        category: str = "personal",
        target_date: Optional[str] = None
    ) -> int:
        """目標作成"""
        c = self.conn.cursor()
        
        c.execute("""
            INSERT INTO goals
            (user_id, title, description, category, target_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id, title, description, category, target_date,
            datetime.now().isoformat()
        ))
        
        goal_id = c.lastrowid
        self.conn.commit()
        
        return goal_id
    
    def extract_goal_from_text(self, user_message: str) -> Optional[Dict]:
        """
        会話から目標を抽出
        「3ヶ月後までに英語でプレゼンできるようになりたい」→ 目標化
        """
        
        goal_keywords = [
            "なりたい", "達成したい", "目指す", "目標",
            "できるようになりたい", "マスターしたい"
        ]
        
        has_goal = any(kw in user_message for kw in goal_keywords)
        
        if not has_goal:
            return None
        
        prompt = f"""以下のメッセージから目標情報を抽出してください。

メッセージ: {user_message}

以下のJSON形式で返してください（JSONのみ）:
{{
  "has_goal": true/false,
  "title": "目標のタイトル",
  "description": "詳細説明",
  "category": "skill/health/career/finance/hobby/personal",
  "target_date": "YYYY-MM-DD形式または相対期間",
  "estimated_months": 3,
  "key_milestones": ["マイルストーン1", "マイルストーン2"]
}}

現在日付: {datetime.now().strftime('%Y-%m-%d')}
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3}
            )
            
            content = response['message']['content']
            
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result if result.get("has_goal") else None
            
        except Exception as e:
            print(f"⚠️ 目標抽出エラー: {e}")
        
        return None
    
    def create_goal_plan(self, goal_title: str, goal_description: str, months: int) -> Dict:
        """
        目標達成のための計画を生成
        - マイルストーン設定
        - 必要なアクション
        """
        
        prompt = f"""以下の目標を{months}ヶ月で達成するための計画を立ててください。

目標: {goal_title}
詳細: {goal_description}
期間: {months}ヶ月

以下のJSON形式で返してください（JSONのみ）:
{{
  "milestones": [
    {{"month": 1, "title": "マイルストーン1", "description": "詳細"}},
    {{"month": 2, "title": "マイルストーン2", "description": "詳細"}}
  ],
  "weekly_actions": [
    "週次アクション1",
    "週次アクション2"
  ],
  "key_habits": [
    "習慣1",
    "習慣2"
  ],
  "success_metrics": [
    "成功指標1",
    "成功指標2"
  ],
  "potential_challenges": [
    "課題1",
    "課題2"
  ]
}}
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.6}
            )
            
            content = response['message']['content']
            
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            print(f"⚠️ 計画生成エラー: {e}")
        
        return {"milestones": [], "weekly_actions": []}
    
    def add_milestone(
        self,
        goal_id: int,
        title: str,
        description: str = "",
        target_date: Optional[str] = None
    ) -> int:
        """マイルストーン追加"""
        c = self.conn.cursor()
        
        c.execute("""
            INSERT INTO milestones
            (goal_id, title, description, target_date)
            VALUES (?, ?, ?, ?)
        """, (goal_id, title, description, target_date))
        
        milestone_id = c.lastrowid
        self.conn.commit()
        
        return milestone_id
    
    def complete_milestone(self, milestone_id: int) -> bool:
        """マイルストーン達成"""
        c = self.conn.cursor()
        
        c.execute("""
            UPDATE milestones
            SET completed = 1, completed_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), milestone_id))
        
        self.conn.commit()
        
        # 目標の進捗率を更新
        c.execute("SELECT goal_id FROM milestones WHERE id = ?", (milestone_id,))
        row = c.fetchone()
        if row:
            self._update_goal_progress_from_milestones(row[0])
        
        return c.rowcount > 0
    
    def _update_goal_progress_from_milestones(self, goal_id: int):
        """マイルストーンの達成状況から目標の進捗率を計算"""
        c = self.conn.cursor()
        
        c.execute("""
            SELECT COUNT(*), SUM(completed)
            FROM milestones
            WHERE goal_id = ?
        """, (goal_id,))
        
        total, completed = c.fetchone()
        
        if total > 0:
            progress = int((completed / total) * 100)
            
            c.execute("""
                UPDATE goals
                SET progress_percentage = ?
                WHERE id = ?
            """, (progress, goal_id))
            
            self.conn.commit()
    
    def update_goal_progress(
        self,
        goal_id: int,
        progress_percentage: int,
        notes: str = "",
        achievements: List[str] = None,
        challenges: List[str] = None
    ) -> int:
        """目標の進捗を記録"""
        c = self.conn.cursor()
        
        # 進捗ログ追加
        c.execute("""
            INSERT INTO goal_progress
            (goal_id, timestamp, progress_percentage, notes, achievements, challenges)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            goal_id,
            datetime.now().isoformat(),
            progress_percentage,
            notes,
            json.dumps(achievements or []),
            json.dumps(challenges or [])
        ))
        
        progress_id = c.lastrowid
        
        # 目標の進捗率を更新
        c.execute("""
            UPDATE goals
            SET progress_percentage = ?
            WHERE id = ?
        """, (progress_percentage, goal_id))
        
        # 100%達成したら完了にする
        if progress_percentage >= 100:
            c.execute("""
                UPDATE goals
                SET status = 'completed', completed_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), goal_id))
        
        self.conn.commit()
        
        return progress_id
    
    def get_active_goals(self, user_id: str) -> List[Dict]:
        """アクティブな目標一覧"""
        c = self.conn.cursor()
        
        c.execute("""
            SELECT id, title, description, category, target_date, 
                   progress_percentage, created_at
            FROM goals
            WHERE user_id = ? AND status = 'active'
            ORDER BY created_at DESC
        """, (user_id,))
        
        goals = []
        for row in c.fetchall():
            goal_id = row[0]
            
            # マイルストーン取得
            c.execute("""
                SELECT id, title, completed, target_date
                FROM milestones
                WHERE goal_id = ?
                ORDER BY target_date ASC
            """, (goal_id,))
            
            milestones = [
                {
                    "id": m[0], "title": m[1], 
                    "completed": bool(m[2]), "target_date": m[3]
                }
                for m in c.fetchall()
            ]
            
            goals.append({
                "id": goal_id,
                "title": row[1],
                "description": row[2],
                "category": row[3],
                "target_date": row[4],
                "progress_percentage": row[5],
                "created_at": row[6],
                "milestones": milestones
            })
        
        return goals
    
    # ==================== 振り返り・分析 ====================
    
    def analyze_goal_progress(self, goal_id: int) -> Dict:
        """目標の進捗を分析"""
        c = self.conn.cursor()
        
        # 目標情報取得
        c.execute("""
            SELECT title, created_at, target_date, progress_percentage
            FROM goals
            WHERE id = ?
        """, (goal_id,))
        
        goal_info = c.fetchone()
        if not goal_info:
            return {}
        
        title, created_at, target_date, current_progress = goal_info
        
        # 経過時間計算
        start_date = datetime.fromisoformat(created_at)
        today = datetime.now()
        days_elapsed = (today - start_date).days
        
        # 予想到達日計算
        if current_progress > 0 and target_date:
            target = datetime.fromisoformat(target_date)
            total_days = (target - start_date).days
            days_remaining = (target - today).days
            
            expected_progress = (days_elapsed / total_days) * 100
            progress_gap = current_progress - expected_progress
            
            status = "ahead" if progress_gap > 10 else "on_track" if progress_gap > -10 else "behind"
        else:
            status = "unknown"
            progress_gap = 0
        
        # 進捗履歴取得
        c.execute("""
            SELECT timestamp, progress_percentage, notes
            FROM goal_progress
            WHERE goal_id = ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (goal_id,))
        
        recent_progress = [
            {"date": r[0], "progress": r[1], "notes": r[2]}
            for r in c.fetchall()
        ]
        
        return {
            "goal_id": goal_id,
            "title": title,
            "current_progress": current_progress,
            "status": status,
            "progress_gap": round(progress_gap, 1),
            "days_elapsed": days_elapsed,
            "recent_progress": recent_progress
        }
    
    def generate_progress_insights(self, goal_id: int) -> str:
        """AIが進捗に対するインサイトを生成"""
        
        analysis = self.analyze_goal_progress(goal_id)
        
        if not analysis:
            return "目標が見つかりません。"
        
        prompt = f"""以下の目標の進捗を分析して、アドバイスをください。

目標: {analysis['title']}
現在の進捗: {analysis['current_progress']}%
経過日数: {analysis['days_elapsed']}日
ステータス: {analysis['status']}
進捗ギャップ: {analysis['progress_gap']}%

最近の進捗:
{json.dumps(analysis['recent_progress'], ensure_ascii=False, indent=2)}

以下の形式で簡潔に（3-4文で）回答してください:
1. 現状の評価
2. 具体的なアドバイス
3. 励ましのメッセージ
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7}
            )
            
            return response['message']['content']
            
        except Exception as e:
            print(f"⚠️ インサイト生成エラー: {e}")
            
            # フォールバック
            if analysis['status'] == 'ahead':
                return f"素晴らしいペースです！予定より進んでいます。この調子で頑張りましょう。"
            elif analysis['status'] == 'behind':
                return f"少しペースを上げる必要があります。小さな一歩でも毎日続けることが大切です。"
            else:
                return f"順調に進んでいます。計画通りのペースを維持しましょう。"


class JournalSystem:
    """日記・記録システム"""
    
    def __init__(self, db_connection, model: str = "qwen2.5:7b"):
        self.conn = db_connection
        self.model = model
        if self.conn is not None:  # ← この行を追加
            self._init_tables()
    
    def _init_tables(self):
        """テーブル初期化"""
        c = self.conn.cursor()
        
        # 日記テーブル
        c.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                entry_type TEXT DEFAULT 'daily',
                content TEXT NOT NULL,
                mood TEXT,
                energy_level INTEGER,
                highlights TEXT,
                challenges TEXT,
                gratitude TEXT,
                tomorrow_plans TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # アクティビティログ
        c.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                description TEXT,
                duration_minutes INTEGER,
                related_goal_id INTEGER,
                notes TEXT
            )
        """)
        
        # 週次・月次振り返り
        c.execute("""
            CREATE TABLE IF NOT EXISTS periodic_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                review_type TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                content TEXT NOT NULL,
                insights TEXT,
                wins TEXT,
                learnings TEXT,
                next_actions TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        self.conn.commit()
    
    # ==================== 日記作成 ====================
    
    def create_journal_entry(
        self,
        user_id: str,
        content: str,
        date: Optional[str] = None,
        mood: Optional[str] = None,
        energy_level: Optional[int] = None,
        highlights: List[str] = None,
        challenges: List[str] = None,
        gratitude: List[str] = None
    ) -> int:
        """日記エントリ作成"""
        c = self.conn.cursor()
        
        entry_date = date or datetime.now().date().isoformat()
        
        c.execute("""
            INSERT INTO journal_entries
            (user_id, date, content, mood, energy_level, highlights, 
             challenges, gratitude, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, entry_date, content, mood, energy_level,
            json.dumps(highlights or []),
            json.dumps(challenges or []),
            json.dumps(gratitude or []),
            datetime.now().isoformat()
        ))
        
        entry_id = c.lastrowid
        self.conn.commit()
        
        return entry_id
    
    def extract_journal_from_conversation(
        self,
        user_id: str,
        conversation_history: List[Dict]
    ) -> Dict:
        """
        会話履歴から日記を自動生成
        その日何をしたか、何を感じたかをAIが要約
        """
        
        # 今日の会話を抽出
        today = datetime.now().date().isoformat()
        today_conversations = [
            c for c in conversation_history
            if c.get("timestamp", "").startswith(today)
        ]
        
        if not today_conversations:
            return {}
        
        # 会話をテキストに変換
        conversation_text = "\n".join([
            f"ユーザー: {c['user_message']}\nAI: {c['ai_response']}"
            for c in today_conversations[:10]  # 最新10件
        ])
        
        prompt = f"""以下は今日のユーザーとの会話です。この会話から日記エントリを作成してください。

{conversation_text}

以下のJSON形式で返してください（JSONのみ）:
{{
  "summary": "今日の出来事の要約（3-4文）",
  "mood": "happy/productive/tired/stressed/peaceful/excited",
  "energy_level": 1-10,
  "highlights": ["ハイライト1", "ハイライト2"],
  "challenges": ["課題1", "課題2"],
  "achievements": ["達成したこと1", "達成したこと2"],
  "gratitude": ["感謝すること1", "感謝すること2"]
}}
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.6}
            )
            
            content = response['message']['content']
            
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            print(f"⚠️ 日記生成エラー: {e}")
        
        return {}
    
    def get_journal_entry(self, user_id: str, date: Optional[str] = None) -> Optional[Dict]:
        """特定日の日記取得"""
        c = self.conn.cursor()
        
        target_date = date or datetime.now().date().isoformat()
        
        c.execute("""
            SELECT id, date, content, mood, energy_level, 
                   highlights, challenges, gratitude
            FROM journal_entries
            WHERE user_id = ? AND date = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, target_date))
        
        row = c.fetchone()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "date": row[1],
            "content": row[2],
            "mood": row[3],
            "energy_level": row[4],
            "highlights": json.loads(row[5]) if row[5] else [],
            "challenges": json.loads(row[6]) if row[6] else [],
            "gratitude": json.loads(row[7]) if row[7] else []
        }
    
    def get_recent_entries(self, user_id: str, days: int = 7) -> List[Dict]:
        """最近の日記エントリ取得"""
        c = self.conn.cursor()
        
        start_date = (datetime.now().date() - timedelta(days=days)).isoformat()
        
        c.execute("""
            SELECT id, date, content, mood, energy_level
            FROM journal_entries
            WHERE user_id = ? AND date >= ?
            ORDER BY date DESC
        """, (user_id, start_date))
        
        return [
            {
                "id": r[0], "date": r[1], "content": r[2],
                "mood": r[3], "energy_level": r[4]
            }
            for r in c.fetchall()
        ]
    
    # ==================== 振り返り ====================
    
    def create_weekly_review(self, user_id: str) -> Dict:
        """週次振り返りを生成"""
        
        # 過去7日間の日記取得
        entries = self.get_recent_entries(user_id, days=7)
        
        if not entries:
            return {"message": "この週は日記エントリがありません。"}
        
        # AIに分析させる
        entries_summary = "\n".join([
            f"{e['date']}: {e['mood']} (エネルギー: {e['energy_level']}/10)"
            for e in entries
        ])
        
        prompt = f"""以下は過去1週間の日記データです。週次振り返りを作成してください。

{entries_summary}

以下のJSON形式で返してください（JSONのみ）:
{{
  "overall_mood": "全体的な気分",
  "highlights": ["今週のハイライト1", "ハイライト2"],
  "patterns": ["気づいたパターン1", "パターン2"],
  "improvements": ["改善できること1", "改善できること2"],
  "next_week_focus": ["来週の焦点1", "焦点2"],
  "encouragement": "励ましのメッセージ"
}}
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7}
            )
            
            content = response['message']['content']
            
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                review = json.loads(json_match.group())
                
                # DBに保存
                c = self.conn.cursor()
                
                week_start = (datetime.now().date() - timedelta(days=7)).isoformat()
                week_end = datetime.now().date().isoformat()
                
                c.execute("""
                    INSERT INTO periodic_reviews
                    (user_id, review_type, period_start, period_end, 
                     content, insights, wins, created_at)
                    VALUES (?, 'weekly', ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, week_start, week_end,
                    json.dumps(review, ensure_ascii=False),
                    json.dumps(review.get("patterns", [])),
                    json.dumps(review.get("highlights", [])),
                    datetime.now().isoformat()
                ))
                
                self.conn.commit()
                
                return review
            
        except Exception as e:
            print(f"⚠️ 週次振り返り生成エラー: {e}")
        
        return {"message": "振り返りを生成できませんでした。"}
    
    def log_activity(
        self,
        user_id: str,
        activity_type: str,
        description: str,
        duration_minutes: Optional[int] = None,
        related_goal_id: Optional[int] = None
    ) -> int:
        """アクティビティをログ"""
        c = self.conn.cursor()
        
        c.execute("""
            INSERT INTO activity_log
            (user_id, timestamp, activity_type, description, 
             duration_minutes, related_goal_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id, datetime.now().isoformat(), activity_type,
            description, duration_minutes, related_goal_id
        ))
        
        activity_id = c.lastrowid
        self.conn.commit()
        
        return activity_id
    
    def get_activity_summary(self, user_id: str, days: int = 7) -> Dict:
        """アクティビティサマリー"""
        c = self.conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # アクティビティタイプ別の集計
        c.execute("""
            SELECT activity_type, COUNT(*), SUM(duration_minutes)
            FROM activity_log
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY activity_type
            ORDER BY COUNT(*) DESC
        """, (user_id, start_date))
        
        activities = {}
        for row in c.fetchall():
            activities[row[0]] = {
                "count": row[1],
                "total_minutes": row[2] or 0
            }
        
        return {
            "period_days": days,
            "activities": activities
        }


# ==================== 使用例 ====================

if __name__ == "__main__":
    conn = sqlite3.connect("partner_ai.db")
    
    goal_mgr = GoalManager(conn)
    journal_sys = JournalSystem(conn)
    
    user_id = "test_user"
    
    # 目標作成
    goal_id = goal_mgr.create_goal(
        user_id=user_id,
        title="英語でプレゼンができるようになる",
        description="3ヶ月後の国際会議で英語プレゼン",
        category="skill",
        target_date=(datetime.now() + timedelta(days=90)).date().isoformat()
    )
    
    print(f"✅ 目標作成: ID {goal_id}")
    
    # 計画生成
    plan = goal_mgr.create_goal_plan(
        "英語でプレゼンができるようになる",
        "3ヶ月後の国際会議で英語プレゼン",
        3
    )
    
    print(f"📋 計画:\n{json.dumps(plan, ensure_ascii=False, indent=2)}")
    
    # 日記作成
    entry_id = journal_sys.create_journal_entry(
        user_id=user_id,
        content="今日は英語の勉強を1時間やった。リスニングが少し改善した気がする。",
        mood="productive",
        energy_level=7,
        highlights=["英語学習1時間達成"],
        gratitude=["集中できる時間があったこと"]
    )
    
    print(f"📝 日記作成: ID {entry_id}")
    
    # 週次振り返り
    review = journal_sys.create_weekly_review(user_id)
    print(f"\n🔄 週次振り返り:\n{json.dumps(review, ensure_ascii=False, indent=2)}")
    
    conn.close()