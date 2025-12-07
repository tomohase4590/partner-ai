// lib/api.ts
// バックエンドとの通信を管理

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// ==================== 基本型定義 ====================

export interface ChatRequest {
  user_id: string;
  message: string;
  model?: string;
}

export interface ChatResponse {
  conversation_id: number;
  response: string;
  model_used: string;
  timestamp: string;
  reason?: string;
  tags?: string[];
}

export interface Conversation {
  id: number;
  timestamp: string;
  user_message: string;
  ai_response: string;
  model_used: string;
  rating: number | null;
  tags?: string[];
  reason?: string;
}

export interface HistoryResponse {
  conversations: Conversation[];
  total: number;
}

export interface Stats {
  total_conversations: number;
  average_rating: number;
  most_used_model: string | null;
}

export interface Model {
  name: string;
  size_gb: number;
  parameter_size?: string;
  quantization?: string;
}

export interface ModelsResponse {
  models: Model[];
}

// ==================== ファインチューニング関連の型定義 ====================

export interface FineTuneReadiness {
  ready: boolean;
  total_conversations: number;
  high_rated_conversations: number;
  usable_for_training: number;
  required: number;
  progress_percentage: number;
}

export interface CustomModel {
  model_name: string;
  base_model: string;
  training_size: number;
  created_at: string;
  is_active: boolean;
}

export interface CustomModelsResponse {
  models: CustomModel[];
}

export interface FineTuneResponse {
  status: string;
  message: string;
  model_name?: string;
  training_size?: number;
  current_count?: number;
  required_count?: number;
}

// ==================== スケジュール・タスク・習慣関連の型定義 (新規追加) ====================

export interface Schedule {
  id: number;
  title: string;
  description?: string;
  start_time: string;
  end_time?: string;
  location?: string;
  status: string;
}

export interface Task {
  id: number;
  title: string;
  description?: string;
  due_date?: string;
  priority: 'high' | 'medium' | 'low';
  estimated_minutes?: number;
  status: string;
}

export interface Habit {
  id: number;
  title: string;
  frequency: string;
  current_streak: number;
  last_completed?: string;
}

export interface DashboardData {
  schedules: Schedule[];
  urgent_tasks: Task[];
  due_today: Task[];
  free_time_slots: Array<{
    start: string;
    end: string;
    duration_minutes: number;
  }>;
  recommendation: string;
}


// ==================== APIクライアント（統合版） ====================
export const api = {
  // ==================== 基本機能 ====================
  
  // チャット送信
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await axios.post(`${API_BASE_URL}/api/chat`, request);
    return response.data;
  },

  // 履歴取得
  async getHistory(userId: string, limit: number = 50): Promise<HistoryResponse> {
    const response = await axios.get(`${API_BASE_URL}/api/history/${userId}`, {
      params: { limit }
    });
    return response.data;
  },

  // フィードバック送信
  async sendFeedback(conversationId: number, rating: number, comment?: string): Promise<void> {
    await axios.post(`${API_BASE_URL}/api/feedback`, {
      conversation_id: conversationId,
      rating,
      comment
    });
  },

  // 統計取得
  async getStats(userId: string): Promise<Stats> {
    const response = await axios.get(`${API_BASE_URL}/api/stats/${userId}`);
    return response.data;
  },

  // モデル一覧取得
  async getModels(): Promise<ModelsResponse> {
    const response = await axios.get(`${API_BASE_URL}/api/models`);
    return response.data;
  },

  // ヘルスチェック
  async healthCheck(): Promise<boolean> {
    try {
      const response = await axios.get(`${API_BASE_URL}/`);
      return response.status === 200;
    } catch {
      return false;
    }
  },

  // 会話のタグを更新
  async updateConversationTags(conversationId: number, tags: string[]): Promise<void> {
    await axios.post(`${API_BASE_URL}/api/conversation/${conversationId}/tags`, tags);
  },

  // ==================== ファインチューニング機能 ====================

  // ファインチューニング準備状況
  async getFineTuneReadiness(userId: string): Promise<FineTuneReadiness> {
    const response = await axios.get(`${API_BASE_URL}/api/finetune/${userId}/readiness`);
    return response.data;
  },

  // カスタムモデル一覧
  async getCustomModels(userId: string): Promise<CustomModelsResponse> {
    const response = await axios.get(`${API_BASE_URL}/api/finetune/${userId}/models`);
    return response.data;
  },

  // アクティブなカスタムモデル取得
  async getActiveCustomModel(userId: string): Promise<{ has_custom_model: boolean; model_name: string | null }> {
    const response = await axios.get(`${API_BASE_URL}/api/finetune/${userId}/active`);
    return response.data;
  },

  // ファインチューニング実行
  async createFineTunedModel(userId: string, baseModel: string): Promise<FineTuneResponse> {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/finetune/${userId}`, {
        base_model: baseModel
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'ファインチューニングに失敗しました');
    }
  },

  // カスタムモデル削除
  async deleteCustomModel(userId: string, modelName: string): Promise<{ status: string; message: string }> {
    const response = await axios.delete(`${API_BASE_URL}/api/finetune/${userId}/models/${modelName}`);
    return response.data;
  },

  // カスタムモデル評価
  async evaluateCustomModel(
    userId: string,
    modelName: string,
    testPrompts?: string[]
  ): Promise<{
    model_name: string;
    success_rate: number;
    total_tests: number;
    successful_tests: number;
    results: Array<{
      prompt: string;
      response?: string;
      error?: string;
      success: boolean;
    }>;
  }> {
    const response = await axios.post(`${API_BASE_URL}/api/finetune/${userId}/evaluate`, {
      model_name: modelName,
      test_prompts: testPrompts
    });
    return response.data;
  },

  // ==================== スケジュール・タスク・習慣機能 (新規追加) ====================

  // ダッシュボード情報（今日の予定・タスク・AI提案）の取得
  async getDailyPlan(userId: string): Promise<DashboardData> {
    const response = await axios.get(`${API_BASE_URL}/api/dashboard/${userId}`);
    return response.data;
  },

  // 習慣リストの取得
  async getHabits(userId: string): Promise<{ habits: Habit[] }> {
    const response = await axios.get(`${API_BASE_URL}/api/habits/${userId}`);
    return response.data;
  },

  // 習慣の完了チェック
  async completeHabit(userId: string, habitId: number): Promise<{ status: string; updated: boolean }> {
    const response = await axios.post(`${API_BASE_URL}/api/habits/${userId}/${habitId}/complete`);
    return response.data;
  },

  // スケジュールの作成（必要に応じて使用）
  async createSchedule(userId: string, data: Partial<Schedule>): Promise<{ status: string; schedule_id: number }> {
    const response = await axios.post(`${API_BASE_URL}/api/schedules/${userId}`, data);
    return response.data;
  },

  // lib/api.ts に以下を追加

  // ==================== スケジュール管理 ====================

  // スケジュール一覧取得
  async getSchedules(userId: string, days: number = 7): Promise<{ schedules: Schedule[]; total: number }> {
    const response = await axios.get(`${API_BASE_URL}/api/schedules/${userId}`, {
      params: { days }
    });
    return response.data;
  },

  // スケジュール更新
  async updateSchedule(scheduleId: number, data: Partial<Schedule>): Promise<{ status: string; message: string }> {
    const response = await axios.put(`${API_BASE_URL}/api/schedules/${scheduleId}`, data);
    return response.data;
  },

  // スケジュール削除
  async deleteSchedule(scheduleId: number): Promise<{ status: string; message: string }> {
    const response = await axios.delete(`${API_BASE_URL}/api/schedules/${scheduleId}`);
    return response.data;
  },

  // ==================== タスク管理 ====================

  // タスク一覧取得
  async getTasks(userId: string): Promise<{ tasks: Task[]; total: number }> {
    const response = await axios.get(`${API_BASE_URL}/api/tasks/${userId}`);
    return response.data;
  },

  // タスク更新
  async updateTask(taskId: number, data: Partial<Task>): Promise<{ status: string; message: string }> {
    const response = await axios.put(`${API_BASE_URL}/api/tasks/${taskId}`, data);
    return response.data;
  },

  // タスク完了
  async completeTask(taskId: number): Promise<{ status: string; completed: boolean }> {
    const response = await axios.post(`${API_BASE_URL}/api/tasks/${taskId}/complete`);
    return response.data;
  },

  // タスク削除
  async deleteTask(taskId: number): Promise<{ status: string; message: string }> {
    const response = await axios.delete(`${API_BASE_URL}/api/tasks/${taskId}`);
    return response.data;
  },

  // ==================== 目標管理 ====================

  // 目標一覧取得
  async getGoals(userId: string): Promise<{ goals: Array<any>; total: number }> {
    const response = await axios.get(`${API_BASE_URL}/api/goals/${userId}`);
    return response.data;
  },

  // 目標更新
  async updateGoal(goalId: number, data: any): Promise<{ status: string; message: string }> {
    const response = await axios.put(`${API_BASE_URL}/api/goals/${goalId}`, data);
    return response.data;
  },

  // 目標削除
  async deleteGoal(goalId: number): Promise<{ status: string; message: string }> {
    const response = await axios.delete(`${API_BASE_URL}/api/goals/${goalId}`);
    return response.data;
  }
};

