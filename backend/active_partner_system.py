"""
active_partner_system.py
AIが能動的に話しかけ、毎日の記録をサポートし、適切なタイミングでリマインドする
本当のパートナーのような存在
"""

import sqlite3
from datetime import datetime, timedelta, time
from typing import Dict, Optional, List
import json
import random
from enum import Enum


class MessagePriority(Enum):
    """メッセージの優先度"""
    CRITICAL = 1  # 即座に表示すべき
    HIGH = 2      # 重要だがタイミングを見る
    MEDIUM = 3    # 適切なタイミングで
    LOW = 4       # ユーザーが次にアクセスしたとき


class ConversationInitiator:
    """AIから会話を始めるシステム"""
    
    def __init__(
        self,
        db_connection,
        goal_manager,
        journal_system,
        schedule_manager
    ):
        self.conn = db_connection
        self.goal_mgr = goal_manager
        self.journal_sys = journal_system
        self.schedule_mgr = schedule_manager
        if self.conn is not None:  # ← この行を追加
            self._init_tables()
    
    def _init_tables(self):
        """テーブル初期化"""
        c = self.conn.cursor()
        
        # AIからのメッセージキュー
        c.execute("""
            CREATE TABLE IF NOT EXISTS ai_messages_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message_type TEXT NOT NULL,
                priority INTEGER NOT NULL,
                message_content TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                sent INTEGER DEFAULT 0,
                sent_at TEXT,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_at TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # ユーザーの活動パターン
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_activity_patterns (
                user_id TEXT PRIMARY KEY,
                typical_morning_time TEXT,
                typical_evening_time TEXT,
                typical_work_hours TEXT,
                preferred_reminder_times TEXT,
                quiet_hours_start TEXT,
                quiet_hours_end TEXT,
                last_updated TEXT
            )
        """)
        
        # リマインダー設定
        c.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                remind_at TEXT NOT NULL,
                repeat_pattern TEXT,
                enabled INTEGER DEFAULT 1,
                related_goal_id INTEGER,
                related_task_id INTEGER,
                created_at TEXT NOT NULL
            )
        """)
        
        # 会話開始履歴
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversation_initiations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                initiated_at TEXT NOT NULL,
                message_type TEXT NOT NULL,
                user_responded INTEGER DEFAULT 0,
                response_time_seconds INTEGER,
                user_sentiment TEXT
            )
        """)
        
        self.conn.commit()
    
    # ==================== ユーザーパターン学習 ====================
    
    def learn_user_patterns(self, user_id: str):
        """
        ユーザーの活動パターンを学習
        - いつも何時に会話を始めるか
        - いつが忙しいか
        - どの時間帯に反応が良いか
        """
        c = self.conn.cursor()
        
        # 過去30日間の会話を分析
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        c.execute("""
            SELECT timestamp
            FROM conversations
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY timestamp
        """, (user_id, start_date))
        
        timestamps = [datetime.fromisoformat(row[0]) for row in c.fetchall()]
        
        if not timestamps:
            return self._get_default_patterns()
        
        # 朝の会話時間を抽出
        morning_times = [
            t.time() for t in timestamps
            if 6 <= t.hour <= 11
        ]
        
        # 夜の会話時間を抽出
        evening_times = [
            t.time() for t in timestamps
            if 18 <= t.hour <= 23
        ]
        
        # 平均時間を計算
        typical_morning = self._calculate_average_time(morning_times) if morning_times else "08:00"
        typical_evening = self._calculate_average_time(evening_times) if evening_times else "20:00"
        
        # パターンを保存
        c.execute("""
            INSERT OR REPLACE INTO user_activity_patterns
            (user_id, typical_morning_time, typical_evening_time, last_updated)
            VALUES (?, ?, ?, ?)
        """, (user_id, typical_morning, typical_evening, datetime.now().isoformat()))
        
        self.conn.commit()
        
        return {
            "typical_morning_time": typical_morning,
            "typical_evening_time": typical_evening
        }
    
    def _calculate_average_time(self, times: List[time]) -> str:
        """時刻の平均を計算"""
        if not times:
            return "08:00"
        
        total_minutes = sum(t.hour * 60 + t.minute for t in times)
        avg_minutes = total_minutes // len(times)
        
        hour = avg_minutes // 60
        minute = avg_minutes % 60
        
        return f"{hour:02d}:{minute:02d}"
    
    def _get_default_patterns(self) -> Dict:
        """デフォルトパターン"""
        return {
            "typical_morning_time": "08:00",
            "typical_evening_time": "20:00"
        }
    
    def get_user_patterns(self, user_id: str) -> Dict:
        """ユーザーパターン取得"""
        c = self.conn.cursor()
        
        c.execute("""
            SELECT typical_morning_time, typical_evening_time,
                   quiet_hours_start, quiet_hours_end
            FROM user_activity_patterns
            WHERE user_id = ?
        """, (user_id,))
        
        row = c.fetchone()
        
        if not row:
            return self._get_default_patterns()
        
        return {
            "typical_morning_time": row[0],
            "typical_evening_time": row[1],
            "quiet_hours_start": row[2],
            "quiet_hours_end": row[3]
        }
    
    # ==================== メッセージ生成 ====================
    
    def generate_morning_checkin(self, user_id: str) -> Dict:
        """朝のチェックインメッセージ"""
        
        # 今日の予定
        schedules = self.schedule_mgr.get_today_schedule(user_id)
        
        # 優先タスク
        tasks = self.schedule_mgr.get_pending_tasks(user_id)
        urgent_tasks = [t for t in tasks if t["priority"] == "high"][:2]
        
        # アクティブな目標
        goals = self.goal_mgr.get_active_goals(user_id)
        
        greetings = [
            "おはようございます!",
            "おはようございます! 今日も良い一日にしましょう。",
            "おはよう! 新しい一日の始まりです。"
        ]
        
        message = random.choice(greetings) + "\n\n"
        
        # 予定がある場合
        if schedules:
            message += f"📅 今日は{len(schedules)}件の予定があります\n"
            first = schedules[0]
            start_time = datetime.fromisoformat(first["start_time"]).strftime("%H:%M")
            message += f"最初の予定: {start_time} - {first['title']}\n\n"
        else:
            message += "📅 今日は予定のない日ですね\n\n"
        
        # 優先タスク
        if urgent_tasks:
            message += "✅ 今日取り組むべきこと:\n"
            for task in urgent_tasks:
                message += f"・{task['title']}\n"
            message += "\n"
        
        # 目標の進捗
        if goals:
            goal = goals[0]
            if goal['progress_percentage'] > 0:
                message += f"🎯 「{goal['title']}」: {goal['progress_percentage']}%\n"
        
        message += "\n今日は何に挑戦しますか? 応援しています! 💪"
        
        return {
            "type": "morning_checkin",
            "priority": MessagePriority.MEDIUM.value,
            "content": message,
            "requires_response": False
        }
    
    def generate_evening_reflection(self, user_id: str) -> Dict:
        """夕方の振り返りプロンプト"""
        
        # 今日の日記エントリをチェック
        today_entry = self.journal_sys.get_journal_entry(user_id)
        
        if today_entry:
            # すでに日記があれば軽いメッセージ
            return {
                "type": "evening_simple",
                "priority": MessagePriority.LOW.value,
                "content": "今日もお疲れ様でした! ゆっくり休んでくださいね😊",
                "requires_response": False
            }
        
        # 今日の予定を確認
        schedules = self.schedule_mgr.get_today_schedule(user_id)
        
        message = "今日も1日お疲れ様でした! ✨\n\n"
        
        if schedules:
            message += f"今日は{len(schedules)}件の予定をこなしましたね。\n\n"
        
        message += "少しだけ今日を振り返りませんか?\n\n"
        message += "📝 今日の出来事:\n"
        message += "・うまくいったこと\n"
        message += "・学んだこと\n"
        message += "・感謝したいこと\n\n"
        message += "何でも大丈夫です。気軽に話してください😊"
        
        return {
            "type": "evening_reflection",
            "priority": MessagePriority.HIGH.value,
            "content": message,
            "requires_response": True
        }
    
    def generate_goal_checkin(self, user_id: str, goal: Dict) -> Dict:
        """目標の定期チェックイン"""
        
        progress = goal['progress_percentage']
        
        message = f"「{goal['title']}」の進捗チェックです\n\n"
        message += f"📊 現在の進捗: {progress}%\n\n"
        
        if progress < 20:
            message += "まだ始めたばかりですね。\n"
            message += "最初の一歩が一番大変ですが、焦らず進めていきましょう。\n\n"
        elif progress < 50:
            message += "順調に進んでいますね!\n"
            message += "この調子で続けていきましょう。\n\n"
        elif progress < 80:
            message += "素晴らしい進捗です!\n"
            message += "ゴールが見えてきましたね。\n\n"
        else:
            message += "もうすぐ完成です!\n"
            message += "あと少し、頑張りましょう!\n\n"
        
        message += "最近の取り組みはいかがですか?\n"
        message += "何か困っていることがあれば教えてください。"
        
        return {
            "type": "goal_checkin",
            "priority": MessagePriority.MEDIUM.value,
            "content": message,
            "requires_response": True,
            "metadata": {"goal_id": goal['id']}
        }
    
    def generate_task_reminder(self, user_id: str, task: Dict) -> Dict:
        """タスクリマインダー"""
        
        due_date = task.get('due_date')
        if due_date:
            due = datetime.fromisoformat(due_date).date()
            today = datetime.now().date()
            days_left = (due - today).days
            
            if days_left == 0:
                urgency = "今日が期限"
                emoji = "⚠️"
            elif days_left == 1:
                urgency = "明日が期限"
                emoji = "📌"
            else:
                urgency = f"あと{days_left}日"
                emoji = "📅"
        else:
            urgency = "期限なし"
            emoji = "✅"
        
        message = f"{emoji} タスクのリマインダーです\n\n"
        message += f"「{task['title']}」\n"
        message += f"期限: {urgency}\n\n"
        
        if task.get('priority') == 'high':
            message += "優先度が高いタスクです。\n"
        
        message += "取り組みましょうか?"
        
        return {
            "type": "task_reminder",
            "priority": MessagePriority.HIGH.value,
            "content": message,
            "requires_response": True,
            "metadata": {"task_id": task['id']}
        }
    
    def generate_habit_reminder(self, user_id: str, habit: Dict) -> Dict:
        """習慣リマインダー"""
        
        message = f"🔔 習慣のリマインダー\n\n"
        message += f"「{habit['title']}」\n"
        message += f"今日はもうやりましたか?\n\n"
        
        if habit.get('current_streak', 0) > 0:
            message += f"現在{habit['current_streak']}日連続です!\n"
            message += "この調子で続けましょう! 🔥"
        else:
            message += "今日から再スタートしましょう!"
        
        return {
            "type": "habit_reminder",
            "priority": MessagePriority.MEDIUM.value,
            "content": message,
            "requires_response": True,
            "metadata": {"habit_id": habit.get('id')}
        }
    
    def generate_break_suggestion(self, user_id: str, work_duration: int) -> Dict:
        """休憩提案"""
        
        message = f"💡 休憩のおすすめ\n\n"
        message += f"もう{work_duration}分集中していますね。\n"
        message += "そろそろ休憩を取りませんか?\n\n"
        message += "おすすめの休憩方法:\n"
        message += "・5分間のストレッチ\n"
        message += "・窓の外を見る\n"
        message += "・水を飲む\n"
        message += "・軽く歩く\n\n"
        message += "リフレッシュして、また集中しましょう!"
        
        return {
            "type": "break_suggestion",
            "priority": MessagePriority.LOW.value,
            "content": message,
            "requires_response": False
        }
    
    def generate_weekly_review_prompt(self, user_id: str) -> Dict:
        """週次振り返りプロンプト"""
        
        message = "🎉 今週もお疲れ様でした!\n\n"
        message += "1週間を振り返ってみませんか?\n\n"
        message += "以下について教えてください:\n"
        message += "1. 今週の一番の成果は?\n"
        message += "2. 新しく学んだことは?\n"
        message += "3. 来週改善したいことは?\n\n"
        message += "振り返ることで、成長を実感できますよ😊"
        
        return {
            "type": "weekly_review",
            "priority": MessagePriority.HIGH.value,
            "content": message,
            "requires_response": True
        }
    
    def generate_encouragement(self, user_id: str, context: str) -> Dict:
        """励ましメッセージ"""
        
        encouragements = {
            "struggling": "大丈夫、うまくいかない日もあります。明日また頑張りましょう。一緒に乗り越えていきましょう!",
            "tired": "お疲れのようですね。無理せず、今日はゆっくり休みましょう。休むことも大切な仕事です。",
            "procrastinating": "始めるのが一番大変ですよね。まずは5分だけやってみませんか? 小さな一歩から始めましょう!",
            "celebrating": "素晴らしい! よく頑張りましたね。この成功を喜びましょう! 🎉"
        }
        
        message = encouragements.get(context, "応援しています! 一緒に頑張りましょう!")
        
        return {
            "type": "encouragement",
            "priority": MessagePriority.MEDIUM.value,
            "content": message,
            "requires_response": False
        }
    
    # ==================== タイミング判定 ====================
    
    def should_send_message_now(
        self,
        user_id: str,
        message_type: str,
        scheduled_time: Optional[str] = None
    ) -> bool:
        """
        今メッセージを送るべきか判定
        - ユーザーのアクティブ時間か
        - 静かな時間（quiet hours）ではないか
        - 最近送りすぎていないか
        """
        
        now = datetime.now()
        current_hour = now.hour
        
        # 深夜・早朝は避ける
        if current_hour < 6 or current_hour >= 23:
            return False
        
        # ユーザーパターンを取得
        patterns = self.get_user_patterns(user_id)
        
        # quiet hours チェック
        if patterns.get('quiet_hours_start') and patterns.get('quiet_hours_end'):
            quiet_start = datetime.strptime(patterns['quiet_hours_start'], "%H:%M").time()
            quiet_end = datetime.strptime(patterns['quiet_hours_end'], "%H:%M").time()
            
            if quiet_start <= now.time() <= quiet_end:
                return False
        
        # 最近のメッセージ頻度チェック
        c = self.conn.cursor()
        
        # 過去1時間以内に送ったメッセージ
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        
        c.execute("""
            SELECT COUNT(*)
            FROM ai_messages_queue
            WHERE user_id = ? AND sent = 1 AND sent_at >= ?
        """, (user_id, one_hour_ago))
        
        recent_count = c.fetchone()[0]
        
        # 1時間に3件以上は送らない
        if recent_count >= 3:
            return False
        
        # scheduled_time が指定されている場合
        if scheduled_time:
            scheduled = datetime.fromisoformat(scheduled_time)
            time_diff = abs((scheduled - now).total_seconds())
            
            # 指定時刻の前後15分以内ならOK
            if time_diff <= 900:  # 15分 = 900秒
                return True
            else:
                return False
        
        return True
    
    # ==================== メッセージキュー管理 ====================
    
    def queue_message(
        self,
        user_id: str,
        message_type: str,
        priority: int,
        content: str,
        scheduled_time: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """メッセージをキューに追加"""
        c = self.conn.cursor()
        
        if not scheduled_time:
            scheduled_time = datetime.now().isoformat()
        
        c.execute("""
            INSERT INTO ai_messages_queue
            (user_id, message_type, priority, message_content, 
             scheduled_time, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, message_type, priority, content,
            scheduled_time, json.dumps(metadata or {}),
            datetime.now().isoformat()
        ))
        
        message_id = c.lastrowid
        self.conn.commit()
        
        return message_id
    
    def get_pending_messages(self, user_id: str) -> List[Dict]:
        """送信待ちのメッセージを取得"""
        c = self.conn.cursor()
        
        now = datetime.now().isoformat()
        
        c.execute("""
            SELECT id, message_type, priority, message_content, 
                   scheduled_time, metadata
            FROM ai_messages_queue
            WHERE user_id = ? 
              AND sent = 0
              AND scheduled_time <= ?
            ORDER BY priority ASC, scheduled_time ASC
        """, (user_id, now))
        
        messages = []
        for row in c.fetchall():
            messages.append({
                "id": row[0],
                "message_type": row[1],
                "priority": row[2],
                "content": row[3],
                "scheduled_time": row[4],
                "metadata": json.loads(row[5]) if row[5] else {}
            })
        
        return messages
    
    def mark_message_sent(self, message_id: int) -> bool:
        """メッセージを送信済みにマーク"""
        c = self.conn.cursor()
        
        c.execute("""
            UPDATE ai_messages_queue
            SET sent = 1, sent_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), message_id))
        
        self.conn.commit()
        return c.rowcount > 0
    
    def mark_message_acknowledged(self, message_id: int) -> bool:
        """ユーザーが確認したことをマーク"""
        c = self.conn.cursor()
        
        c.execute("""
            UPDATE ai_messages_queue
            SET acknowledged = 1, acknowledged_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), message_id))
        
        self.conn.commit()
        return c.rowcount > 0
    
    # ==================== 定期的なチェック ====================
    
    def check_and_queue_daily_messages(self, user_id: str):
        """
        定期的に実行して、適切なメッセージをキューに追加
        - 朝のチェックイン
        - 夜の振り返り
        - タスクリマインダー
        - 目標チェックイン
        """
        
        now = datetime.now()
        patterns = self.get_user_patterns(user_id)
        
        # 朝のチェックインをキュー
        morning_time = patterns.get('typical_morning_time', '08:00')
        morning_dt = datetime.combine(now.date(), datetime.strptime(morning_time, "%H:%M").time())
        
        # 今日の朝のメッセージがまだキューにない場合
        c = self.conn.cursor()
        c.execute("""
            SELECT id FROM ai_messages_queue
            WHERE user_id = ? 
              AND message_type = 'morning_checkin'
              AND DATE(scheduled_time) = DATE(?)
        """, (user_id, now.isoformat()))
        
        if not c.fetchone():
            morning_msg = self.generate_morning_checkin(user_id)
            self.queue_message(
                user_id=user_id,
                message_type=morning_msg['type'],
                priority=morning_msg['priority'],
                content=morning_msg['content'],
                scheduled_time=morning_dt.isoformat()
            )
        
        # 夜の振り返りをキュー
        evening_time = patterns.get('typical_evening_time', '20:00')
        evening_dt = datetime.combine(now.date(), datetime.strptime(evening_time, "%H:%M").time())
        
        c.execute("""
            SELECT id FROM ai_messages_queue
            WHERE user_id = ?
              AND message_type IN ('evening_reflection', 'evening_simple')
              AND DATE(scheduled_time) = DATE(?)
        """, (user_id, now.isoformat()))
        
        if not c.fetchone():
            evening_msg = self.generate_evening_reflection(user_id)
            self.queue_message(
                user_id=user_id,
                message_type=evening_msg['type'],
                priority=evening_msg['priority'],
                content=evening_msg['content'],
                scheduled_time=evening_dt.isoformat()
            )
        
        # 週次振り返り（日曜日の夕方）
        if now.weekday() == 6:  # 日曜日
            review_time = datetime.combine(now.date(), time(hour=18, minute=0))
            
            c.execute("""
                SELECT id FROM ai_messages_queue
                WHERE user_id = ?
                  AND message_type = 'weekly_review'
                  AND DATE(scheduled_time) = DATE(?)
            """, (user_id, now.isoformat()))
            
            if not c.fetchone():
                review_msg = self.generate_weekly_review_prompt(user_id)
                self.queue_message(
                    user_id=user_id,
                    message_type=review_msg['type'],
                    priority=review_msg['priority'],
                    content=review_msg['content'],
                    scheduled_time=review_time.isoformat()
                )
        
        # タスクリマインダー（期限が近いもの）
        tasks = self.schedule_mgr.get_pending_tasks(user_id)
        for task in tasks:
            if task.get('due_date'):
                due = datetime.fromisoformat(task['due_date']).date()
                days_left = (due - now.date()).days
                
                # 期限が今日または明日のタスク
                if 0 <= days_left <= 1:
                    # すでにリマインダーが送られていないかチェック
                    c.execute("""
                        SELECT id FROM ai_messages_queue
                        WHERE user_id = ?
                          AND message_type = 'task_reminder'
                          AND metadata LIKE ?
                          AND DATE(scheduled_time) = DATE(?)
                    """, (user_id, f'%"task_id": {task["id"]}%', now.isoformat()))
                    
                    if not c.fetchone():
                        reminder_msg = self.generate_task_reminder(user_id, task)
                        # 午前10時にリマインド
                        reminder_time = datetime.combine(now.date(), time(hour=10, minute=0))
                        
                        self.queue_message(
                            user_id=user_id,
                            message_type=reminder_msg['type'],
                            priority=reminder_msg['priority'],
                            content=reminder_msg['content'],
                            scheduled_time=reminder_time.isoformat(),
                            metadata=reminder_msg.get('metadata')
                        )


# ==================== 使用例 ====================

if __name__ == "__main__":
    from goal_journal_system import GoalManager, JournalSystem
    from schedule_manager import ScheduleManager
    
    conn = sqlite3.connect("partner_ai.db")
    
    goal_mgr = GoalManager(conn)
    journal_sys = JournalSystem(conn)
    schedule_mgr = ScheduleManager(conn)
    
    initiator = ConversationInitiator(conn, goal_mgr, journal_sys, schedule_mgr)
    
    user_id = "test_user"
    
    # ユーザーパターンを学習
    patterns = initiator.learn_user_patterns(user_id)
    print(f"📊 学習したパターン: {patterns}")
    
    # 今日のメッセージをキューに追加
    initiator.check_and_queue_daily_messages(user_id)
    
    # 送信待ちメッセージを取得
    pending = initiator.get_pending_messages(user_id)
    
    print(f"\n📬 送信待ちメッセージ: {len(pending)}件")
    for msg in pending:
        print(f"\n{msg['message_type']}:")
        print(msg['content'])
    
    conn.close()