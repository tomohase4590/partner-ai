'use client';

import { useState, useEffect } from 'react';
import { 
  Calendar, CheckSquare, Zap, Clock, MapPin, 
  AlertCircle, CheckCircle2, Trophy, Trash2
} from 'lucide-react';
import { api } from '@/lib/api';

interface DashboardData {
  schedules: any[];
  urgent_tasks: any[];
  due_today: any[];
  recommendation: string;
}

export default function AdvancedDashboard({ userId }: { userId: string }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [habits, setHabits] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [dashboardRes, habitsRes, tasksRes] = await Promise.all([
        api.getDailyPlan(userId).catch(() => null),
        api.getHabits(userId).catch(() => ({ habits: [] })),
        api.getTasks(userId).catch(() => ({ tasks: [] }))
      ]);
      
      setData(dashboardRes);
      setHabits(habitsRes?.habits || []);
      setTasks(tasksRes?.tasks || []);
    } catch (error) {
      console.error('データ取得エラー:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleHabitComplete = async (habitId: number) => {
    try {
      await api.completeHabit(userId, habitId);
      loadData();
    } catch (error) {
      console.error('習慣更新エラー:', error);
    }
  };

  const handleDeleteSchedule = async (scheduleId: number) => {
    if (!confirm('この予定を削除しますか？')) return;
    
    try {
      await api.deleteSchedule(scheduleId);
      loadData();
    } catch (error) {
      console.error('削除エラー:', error);
    }
  };

  const handleCompleteTask = async (taskId: number) => {
    try {
      await api.completeTask(taskId);
      loadData();
    } catch (error) {
      console.error('タスク完了エラー:', error);
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    if (!confirm('このタスクを削除しますか？')) return;
    
    try {
      await api.deleteTask(taskId);
      loadData();
    } catch (error) {
      console.error('削除エラー:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (!data) return (
    <div className="p-6 text-center text-gray-500">
      <p>データを読み込めませんでした。</p>
    </div>
  );

  return (
    <div className="h-full overflow-y-auto p-6 bg-gray-50">
      <div className="max-w-5xl mx-auto space-y-6">
        
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl p-6 text-white shadow-lg">
          <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
            <Zap className="w-6 h-6 text-yellow-300" />
            今日のブリーフィング
          </h2>
          <p className="text-blue-100 text-lg">
            {data.recommendation || "今日も一日頑張りましょう！"}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-blue-500" />
                今日の予定
              </h3>
              
              {(data.schedules || []).length === 0 ? (
                <p className="text-gray-500 text-center py-4">予定はありません</p>
              ) : (
                <div className="space-y-3">
                  {(data.schedules || []).map((schedule: any) => (
                    <div key={schedule.id} className="group relative p-3 rounded-lg bg-blue-50 border hover:shadow-md transition">
                      <div className="flex gap-4">
                        <div className="flex flex-col items-center min-w-[60px] text-blue-800">
                          <span className="text-sm font-bold">
                            {new Date(schedule.start_time).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <div className="flex-1">
                          <div className="font-bold">{schedule.title}</div>
                          {schedule.location && (
                            <div className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                              <MapPin className="w-3 h-3" />
                              {schedule.location}
                            </div>
                          )}
                        </div>
                        <div className="opacity-0 group-hover:opacity-100 transition">
                          <button
                            onClick={() => handleDeleteSchedule(schedule.id)}
                            className="p-1 rounded hover:bg-red-100 text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Trophy className="w-5 h-5 text-yellow-500" />
                習慣トラッカー
              </h3>
              
              {habits.length === 0 ? (
                <p className="text-gray-500 text-center py-4 text-sm">
                  習慣が登録されていません
                </p>
              ) : (
                <div className="space-y-3">
                  {habits.map((habit: any) => {
                    const isDone = habit.last_completed && 
                      new Date(habit.last_completed).toDateString() === new Date().toDateString();

                    return (
                      <div key={habit.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
                        <div>
                          <div className="font-semibold">{habit.title}</div>
                          <div className="text-xs text-gray-500">
                            {habit.current_streak}日連続 🔥
                          </div>
                        </div>
                        <button
                          onClick={() => !isDone && handleHabitComplete(habit.id)}
                          disabled={isDone}
                          className={`p-2 rounded-full transition ${
                            isDone 
                              ? 'bg-green-100 text-green-600' 
                              : 'bg-gray-100 hover:bg-green-500 hover:text-white'
                          }`}
                        >
                          <CheckCircle2 className="w-6 h-6" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
              <CheckSquare className="w-5 h-5 text-green-500" />
              タスク
            </h3>

            <div className="space-y-4">
              {(data.due_today || []).length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-red-500 uppercase mb-2 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> 今日が期限
                  </h4>
                  {(data.due_today || []).map((task: any) => (
                    <TaskCard key={task.id} task={task} onComplete={handleCompleteTask} onDelete={handleDeleteTask} urgent />
                  ))}
                </div>
              )}

              {(data.urgent_tasks || []).length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">優先度: 高</h4>
                  {(data.urgent_tasks || []).map((task: any) => (
                    <TaskCard key={task.id} task={task} onComplete={handleCompleteTask} onDelete={handleDeleteTask} />
                  ))}
                </div>
              )}

              {tasks.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">その他</h4>
                  {tasks.map((task: any) => (
                    <TaskCard key={task.id} task={task} onComplete={handleCompleteTask} onDelete={handleDeleteTask} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TaskCard({ task, onComplete, onDelete, urgent = false }: any) {
  return (
    <div className={`group p-3 rounded-lg border flex gap-3 hover:shadow-md transition mb-2 ${
      urgent ? 'bg-red-50 border-red-200' : 'bg-white'
    }`}>
      <div className={`mt-1 w-2 h-2 rounded-full ${
        task.priority === 'high' ? 'bg-orange-500' : 'bg-blue-500'
      }`} />
      <div className="flex-1 min-w-0">
        <div className="font-medium">{task.title}</div>
        {task.due_date && (
          <div className="text-xs text-gray-500 mt-1 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {task.due_date}
          </div>
        )}
      </div>
      <div className="opacity-0 group-hover:opacity-100 transition flex gap-1">
        <button onClick={() => onComplete(task.id)} className="p-1 rounded hover:bg-green-100 text-green-600">
          <CheckCircle2 className="w-4 h-4" />
        </button>
        <button onClick={() => onDelete(task.id)} className="p-1 rounded hover:bg-red-100 text-red-600">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}