"""
assistant_brain.py
AIアシスタントの「脳」- 判断・提案・サポート
"""

import ollama
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json


class AssistantBrain:
    """AIアシスタントの意思決定システム"""
    
    def __init__(self, schedule_manager, model: str = "qwen2.5:7b"):
        self.schedule_mgr = schedule_manager
        self.model = model
    
    # ==================== 会話理解 ====================
    
    def understand_intent(self, user_message: str, context: Dict) -> Dict:
        """
        ユーザーの意図を理解
        - 質問なのか、依頼なのか、雑談なのか
        - 何をサポートすべきか
        """
        
        prompt = f"""以下のユーザーメッセージの意図を分析してください。

メッセージ: {user_message}

コンテキスト:
- 現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- 未完了タスク数: {context.get('pending_tasks_count', 0)}
- 今日の予定数: {context.get('today_schedules_count', 0)}

以下のJSON形式で返してください（JSONのみ）:
{{
  "intent": "question/request/chat/task_check/schedule_inquiry",
  "requires_action": true/false,
  "action_type": "create_task/create_schedule/start_work_session/provide_info/none",
  "urgency": "high/medium/low",
  "emotional_tone": "stressed/excited/neutral/confused",
  "keywords": ["キーワード1", "キーワード2"]
}}
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
                return json.loads(json_match.group())
            
        except Exception as e:
            print(f"⚠️ 意図理解エラー: {e}")
        
        return {"intent": "chat", "requires_action": False}
    
    def detect_stress_level(self, user_message: str, recent_history: List[Dict]) -> Dict:
        """
        ストレスレベルを検出
        - 焦り、疲労、不安などのシグナル
        """
        
        # メッセージから感情シグナル検出
        stress_keywords = ["疲れた", "無理", "間に合わない", "やばい", "焦る"]
        positive_keywords = ["できた", "うまくいった", "楽しい", "良かった"]
        
        stress_score = sum(1 for kw in stress_keywords if kw in user_message)
        positive_score = sum(1 for kw in positive_keywords if kw in user_message)
        
        # 最近の会話パターン
        recent_short_messages = sum(
            1 for h in recent_history[-5:] 
            if len(h.get("user", "")) < 20
        )
        
        level = "low"
        if stress_score >= 2 or recent_short_messages >= 3:
            level = "high"
        elif stress_score >= 1:
            level = "medium"
        
        return {
            "level": level,
            "stress_score": stress_score,
            "positive_score": positive_score,
            "needs_support": level in ["medium", "high"]
        }
    
    # ==================== タスクサポート ====================
    
    def provide_task_support(self, task: Dict, context: Dict) -> str:
        """
        タスクに対する具体的なサポートを提供
        - 始め方のアドバイス
        - 進捗確認
        - 励まし
        """
        
        task_status = task.get("status", "pending")
        
        if task_status == "pending":
            # まだ始めていない
            strategy = self.schedule_mgr.suggest_task_strategy(
                task["title"],
                task.get("description", ""),
                context.get("energy_level", "medium")
            )
            
            return f"""「{task['title']}」に取り組みますか？

📋 取り組み方:
{strategy}

まずは最初の5分だけ始めてみましょう。集中モードを開始しますか？"""
        
        elif task_status == "in_progress":
            # 進行中
            return f"""「{task['title']}」進んでいますか？

進捗を教えてください:
- 順調に進んでいる
- つまずいている
- 休憩したい

何かサポートできることはありますか？"""
        
        else:
            return "他にサポートが必要なタスクはありますか？"
    
    def suggest_next_action(self, user_id: str, current_context: Dict) -> str:
        """
        次に取るべき行動を提案
        - 今すべきこと
        - 優先順位
        """
        
        # 今日の計画取得
        daily_plan = self.schedule_mgr.suggest_daily_plan(user_id)
        
        now = datetime.now()
        hour = now.hour
        
        # 時間帯による提案
        if hour < 10:
            # 午前: 難しいタスクを提案
            if daily_plan["urgent_tasks"]:
                task = daily_plan["urgent_tasks"][0]
                return f"""おはようございます！今日は頭が冴えている時間ですね。

優先度の高い「{task['title']}」から始めるのはいかがですか？
集中して取り組むには最適な時間帯です。"""
            
        elif hour < 15:
            # 昼: 適度なタスク
            if daily_plan["schedules"]:
                next_schedule = daily_plan["schedules"][0]
                return f"""次の予定「{next_schedule['title']}」まで時間があります。
その前にできるタスクに取り組みましょうか？"""
            
        elif hour < 18:
            # 夕方: 簡単なタスクまたは明日の準備
            return """もうすぐ夕方ですね。今日の振り返りと明日の準備をしましょうか？

今日達成できたこと:
- [確認中...]

明日の予定:
- [確認中...]"""
        
        else:
            # 夜: リラックス提案
            return """お疲れ様でした！今日も1日頑張りましたね。

明日に備えてゆっくり休んでください。
明日の重要なタスクをリマインドしますか？"""
        
        return "何かお手伝いできることはありますか？"
    
    # ==================== スケジュールサポート ====================
    
    def analyze_schedule_feasibility(
        self,
        user_id: str,
        new_schedule: Dict
    ) -> Dict:
        """
        スケジュールの実行可能性を分析
        - 移動時間は十分か
        - 前後の予定との間隔は適切か
        """
        
        start_time = new_schedule["start_time"]
        
        # 前後の予定をチェック
        nearby_schedules = self.schedule_mgr.get_upcoming_schedules(user_id, days=1)
        
        warnings = []
        suggestions = []
        
        for schedule in nearby_schedules:
            # 時間の近さをチェック
            schedule_time = datetime.fromisoformat(schedule["start_time"])
            new_time = datetime.fromisoformat(start_time)
            
            time_diff = abs((schedule_time - new_time).total_seconds() / 60)
            
            if time_diff < 30:
                warnings.append(f"「{schedule['title']}」と時間が近すぎます")
            elif time_diff < 60:
                suggestions.append("移動時間を考慮してください")
        
        return {
            "feasible": len(warnings) == 0,
            "warnings": warnings,
            "suggestions": suggestions
        }
    
    def suggest_optimal_time(
        self,
        user_id: str,
        task_title: str,
        duration_minutes: int,
        days_ahead: int = 7
    ) -> List[Dict]:
        """
        タスクに最適な時間帯を提案
        - 既存のスケジュールと競合しない
        - ユーザーの生産性が高い時間帯
        """
        
        schedules = self.schedule_mgr.get_upcoming_schedules(user_id, days=days_ahead)
        
        # 簡易実装: 空き時間を検出
        suggestions = []
        
        for day_offset in range(days_ahead):
            target_date = datetime.now().date() + timedelta(days=day_offset)
            
            # その日の予定を確認
            day_schedules = [
                s for s in schedules
                if datetime.fromisoformat(s["start_time"]).date() == target_date
            ]
            
            if not day_schedules:
                # 予定がない日 - 午前を提案
                suggestions.append({
                    "date": target_date.isoformat(),
                    "time": "10:00",
                    "reason": "予定のない日です。午前中の集中時間がおすすめ"
                })
        
        return suggestions[:3]
    
    # ==================== モチベーション管理 ====================
    
    def generate_encouragement(self, task: Dict, progress: int) -> str:
        """
        タスクの進捗に応じた励まし
        """
        
        if progress < 25:
            return f"""「{task['title']}」始めましたね！素晴らしい第一歩です。

最初の一歩が一番大変ですが、もう始めています。
このペースで進めていきましょう！💪"""
        
        elif progress < 50:
            return f"""「{task['title']}」もう{progress}%進みました！

半分まであと少しです。ここまで来たら完走できます。
休憩を挟みながら、引き続き頑張りましょう！"""
        
        elif progress < 75:
            return f"""「{task['title']}」順調ですね！{progress}%完了です。

もう大部分が終わっています。最後まで気を抜かずに！
ゴールが見えてきました。🎯"""
        
        else:
            return f"""「{task['title']}」もうすぐ完成です！{progress}%！

あと少しで完了です。最後の仕上げを丁寧にやりましょう。
達成感を味わう準備はできていますか？✨"""
    
    def celebrate_achievement(self, task: Dict, stats: Dict) -> str:
        """
        タスク完了時の祝福メッセージ
        """
        
        completed_count = stats.get("completed_tasks", 0)
        
        messages = [
            f"""🎉 「{task['title']}」完了おめでとうございます！

よく頑張りました。一つ一つ達成していくあなたは素晴らしいです。"""
        ]
        
        if completed_count >= 5:
            messages.append(f"\n今週すでに{completed_count}個のタスクを完了しています。すごいペースです！")
        
        if task.get("priority") == "high":
            messages.append("\n優先度の高いタスクを片付けましたね。大きな前進です。")
        
        return "".join(messages)
    
    # ==================== プロアクティブ提案 ====================
    
    def should_send_reminder(self, user_id: str) -> Optional[Dict]:
        """
        リマインダーを送るべきか判断
        """
        
        # 今後1時間以内の予定
        schedules = self.schedule_mgr.get_upcoming_schedules(user_id, days=1)
        now = datetime.now()
        
        for schedule in schedules:
            start_time = datetime.fromisoformat(schedule["start_time"])
            time_until = (start_time - now).total_seconds() / 60
            
            if 0 < time_until <= 15:
                return {
                    "type": "schedule_reminder",
                    "schedule": schedule,
                    "minutes_until": int(time_until),
                    "message": f"まもなく「{schedule['title']}」が始まります（{int(time_until)}分後）"
                }
        
        # 期限が迫っているタスク
        tasks = self.schedule_mgr.get_pending_tasks(user_id)
        
        for task in tasks:
            if task.get("due_date"):
                due = datetime.fromisoformat(task["due_date"])
                days_until = (due.date() - now.date()).days
                
                if days_until == 0 and task["status"] == "pending":
                    return {
                        "type": "task_deadline",
                        "task": task,
                        "message": f"「{task['title']}」の期限は今日です。取り組みましょうか？"
                    }
        
        return None
    
    def generate_daily_briefing(self, user_id: str) -> str:
        """
        朝の定例ブリーフィング
        """
        
        daily_plan = self.schedule_mgr.suggest_daily_plan(user_id)
        stats = self.schedule_mgr.get_work_statistics(user_id, days=7)
        
        briefing = f"""おはようございます！今日のブリーフィングです。

📅 今日の予定: {len(daily_plan['schedules'])}件
"""
        
        if daily_plan['schedules']:
            for i, s in enumerate(daily_plan['schedules'][:3], 1):
                start = datetime.fromisoformat(s['start_time']).strftime('%H:%M')
                briefing += f"{i}. {start} - {s['title']}\n"
        
        briefing += f"\n✅ 優先タスク: {len(daily_plan['urgent_tasks'])}件\n"
        
        if daily_plan['urgent_tasks']:
            for task in daily_plan['urgent_tasks'][:2]:
                briefing += f"・{task['title']}\n"
        
        briefing += f"\n📊 今週の作業時間: {stats['total_work_hours']}時間\n"
        
        briefing += f"\n{daily_plan['recommendation']}"
        
        return briefing


# ==================== 使用例 ====================

if __name__ == "__main__":
    import sqlite3
    from schedule_manager import ScheduleManager
    
    conn = sqlite3.connect("partner_ai.db")
    schedule_mgr = ScheduleManager(conn)
    
    brain = AssistantBrain(schedule_mgr)
    
    user_id = "test_user"
    
    # 意図理解
    message = "明日のミーティングまでに資料作らないと"
    intent = brain.understand_intent(message, {
        "pending_tasks_count": 5,
        "today_schedules_count": 2
    })
    
    print(f"🧠 意図: {intent}")
    
    # 次のアクション提案
    suggestion = brain.suggest_next_action(user_id, {})
    print(f"\n💡 提案:\n{suggestion}")
    
    # 朝のブリーフィング
    briefing = brain.generate_daily_briefing(user_id)
    print(f"\n📋 ブリーフィング:\n{briefing}")
    
    conn.close()