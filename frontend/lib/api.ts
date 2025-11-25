// lib/api.ts
// バックエンドとの通信を管理

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// 型定義
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

// APIクライアント
export const api = {
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
  }
};

// ファインチューニング関連の型定義
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

// API関数に追加
export const api = {
  // ... 既存の関数 ...

  // ファインチューニング準備状況
  async getFineTuneReadiness(userId: string): Promise<FineTuneReadiness> {
    const response = await fetch(`${API_BASE}/api/finetune/${userId}/readiness`);
    if (!response.ok) throw new Error('準備状況の取得に失敗しました');
    return response.json();
  },

  // カスタムモデル一覧
  async getCustomModels(userId: string): Promise<CustomModelsResponse> {
    const response = await fetch(`${API_BASE}/api/finetune/${userId}/models`);
    if (!response.ok) throw new Error('モデル一覧の取得に失敗しました');
    return response.json();
  },

  // アクティブなカスタムモデル取得
  async getActiveCustomModel(userId: string): Promise<{ has_custom_model: boolean; model_name: string | null }> {
    const response = await fetch(`${API_BASE}/api/finetune/${userId}/active`);
    if (!response.ok) throw new Error('アクティブモデルの取得に失敗しました');
    return response.json();
  },

  // ファインチューニング実行
  async createFineTunedModel(userId: string, baseModel: string): Promise<FineTuneResponse> {
    const response = await fetch(`${API_BASE}/api/finetune/${userId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ base_model: baseModel }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'ファインチューニングに失敗しました');
    }
    return response.json();
  },

  // カスタムモデル削除
  async deleteCustomModel(userId: string, modelName: string): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE}/api/finetune/${userId}/models/${modelName}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('モデルの削除に失敗しました');
    return response.json();
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
    const response = await fetch(`${API_BASE}/api/finetune/${userId}/evaluate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ model_name: modelName, test_prompts: testPrompts }),
    });
    if (!response.ok) throw new Error('モデル評価に失敗しました');
    return response.json();
  },
};