// lib/api.ts
// バックエンドとの通信を管理

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// 基本型定義
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

// APIクライアント（統合版）
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
};