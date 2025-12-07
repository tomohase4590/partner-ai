"""
proactive_assistant.py
AIから能動的に話しかける・提案するシステム
"""

class ProactiveAssistant:
    """積極的に支援するアシスタント"""
    
    def __init__(self, db_connection, task_manager, profile_manager):
        self.conn = db_connection
        self.task_manager = task_manager
        self.profile_manager = profile_manager
    
    def generate_daily_greeting(self, user_id: str) -> str:
        """
        時間帯とユーザー状態に応じた挨拶
        """
        hour = datetime.now().hour
        profile = self.profile_manager.get_profile(user_id)
        daily_focus = self.task_manager.suggest_daily_focus(user_id)
        
        # 時間帯による挨拶
        if hour < 12:
            greeting = "おはようございます！"
        elif hour < 18:
            greeting = "こんにちは！"
        else:
            greeting = "こんばんは！"
        
        # タスク状況を加味
        message = greeting
        
        if daily_focus["overdue_count"] > 0:
            message += f"\n期限切れのタスクが{daily_focus['overdue_count']}件あります。一緒に片付けましょうか？"
        elif daily_focus["urgent_tasks"]:
            task = daily_focus["urgent_tasks"][0]
            message += f"\n今日は「{task['title']}」に取り組む予定でしたね。進捗はいかがですか？"
        else:
            message += "\n今日も良い一日になりそうですね！何かお手伝いできることはありますか？"
        
        return message
    
    def should_send_reminder(self, user_id: str) -> Optional[str]:
        """
        リマインダーが必要かチェック
        - 長時間タスクが放置されている
        - 習慣の実行時間
        """
        # 実装...
        pass
    
    def detect_stress_signals(self, recent_conversations: List[Dict]) -> Dict:
        """
        ストレスや疲労のシグナルを検出
        - 否定的な言葉の増加
        - 短い返答が続く
        - 深夜の会話
        """
        # 実装...
        pass