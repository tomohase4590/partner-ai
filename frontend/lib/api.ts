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
  }
};