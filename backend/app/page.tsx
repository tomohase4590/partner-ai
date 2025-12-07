'use client';

import { useState, useEffect, useRef } from 'react';
import { Send, Loader2, Settings, History, BarChart3, User, Sparkles, LayoutDashboard } from 'lucide-react';
import ChatMessage from '@/components/ChatMessage';
import HistoryView from '@/components/HistoryView';
import StatsView from '@/components/StatsView';
import ProfileView from '@/components/ProfileView';
import FineTunePanel from '@/components/FineTunePanel';
import DashboardView from '@/components/DashboardView';
import { api, type ChatRequest } from '@/lib/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  conversationId?: number;
  rating?: number | null;
  reason?: string;
  tags?: string[];
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState('qwen2.5:32b');
  const [models, setModels] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<'chat' | 'dashboard' | 'history' | 'stats' | 'profile' | 'finetune'>('chat');
  const [hasCustomModel, setHasCustomModel] = useState(false);
  const [customModelName, setCustomModelName] = useState<string | null>(null);
  
  // モデルリストを再読み込みする関数
  const refreshModels = async () => {
    try {
      console.log('🔄 モデルリストを更新中...');
      
      // 標準モデルを取得
      const response = await api.getModels();
      const modelNames = response.models.map(m => m.name);
      
      // カスタムモデルを取得
      const customResult = await api.getActiveCustomModel(userId);
      
      if (customResult.has_custom_model && customResult.model_name) {
        setHasCustomModel(true);
        setCustomModelName(customResult.model_name);
        
        // カスタムモデルをリストの先頭に追加
        const allModels = [customResult.model_name, ...modelNames.filter(m => m !== customResult.model_name)];
        setModels(allModels);
        
        // 新しく作成されたカスタムモデルを自動選択
        setSelectedModel(customResult.model_name);
        
        console.log('✅ モデルリスト更新完了:', allModels);
      } else {
        setModels(modelNames);
      }
    } catch (error) {
      console.error('モデル更新エラー:', error);
    }
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const userId = 'demo_user'; // 固定ユーザーID

  // 自動スクロール
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 初期化：モデル一覧取得
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await api.getModels();
        const modelNames = response.models.map(m => m.name);
        setModels(modelNames);
        
        // カスタムモデルも取得
        const customResult = await api.getActiveCustomModel(userId);
        if (customResult.has_custom_model && customResult.model_name) {
          setHasCustomModel(true);
          setCustomModelName(customResult.model_name);
          
          // カスタムモデルをリストに追加（重複チェック）
          if (!modelNames.includes(customResult.model_name)) {
            setModels(prev => [customResult.model_name!, ...prev]);
          }
        }
      } catch (error) {
        console.error('モデル取得エラー:', error);
        // フォールバック
        setModels(['qwen2.5:7b', 'gemma3:12b', 'gemma3:4b']);
      }
    };

    const loadHistory = async () => {
      try {
        const history = await api.getHistory(userId, 10);
        const msgs: Message[] = [];
        history.conversations.reverse().forEach(conv => {
          msgs.push({
            role: 'user',
            content: conv.user_message,
            timestamp: conv.timestamp
          });
          msgs.push({
            role: 'assistant',
            content: conv.ai_response,
            timestamp: conv.timestamp,
            conversationId: conv.id,
            rating: conv.rating
          });
        });
        setMessages(msgs);
      } catch (error) {
        console.error('履歴取得エラー:', error);
      }
    };

    const checkCustomModel = async () => {
      try {
        const result = await api.getActiveCustomModel(userId);
        setHasCustomModel(result.has_custom_model);
        setCustomModelName(result.model_name);
        
        // カスタムモデルがあればモデルリストに追加
        if (result.model_name) {
          setModels(prev => {
            if (!prev.includes(result.model_name!)) {
              return [result.model_name!, ...prev];
            }
            return prev;
          });
        }
      } catch (error) {
        console.error('カスタムモデル確認エラー:', error);
      }
    };

    fetchModels();
    loadHistory();
    // fetchModelsの後にcheckCustomModelを実行
    fetchModels().then(() => checkCustomModel());
  }, []);

  // メッセージ送信
  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const request: ChatRequest = {
        user_id: userId,
        message: input,
        model: selectedModel
      };

      const response = await api.sendMessage(request);

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
        conversationId: response.conversation_id,
        rating: null,
        reason: (response as any).reason,
        tags: (response as any).tags
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('送信エラー:', error);
      alert('エラーが発生しました。バックエンドが起動しているか確認してください。');
    } finally {
      setLoading(false);
    }
  };

  // Enter キーで送信
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 評価
  const handleRate = async (conversationId: number, rating: number, comment?: string) => {
    try {
      await api.sendFeedback(conversationId, rating, comment);
      
      // UIを更新
      setMessages(prev =>
        prev.map(msg =>
          msg.conversationId === conversationId
            ? { ...msg, rating }
            : msg
        )
      );
    } catch (error) {
      console.error('フィードバック送信エラー:', error);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* ヘッダー */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
              <span className="text-white font-bold text-xl">P</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">パートナーAI</h1>
              <p className="text-sm text-gray-500">あなたと共に成長するAI</p>
            </div>
          </div>

          {/* タブナビゲーション */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
                activeTab === 'chat'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <Send className="w-4 h-4" />
              チャット
            </button>
            <button
              onClick={() => setActiveTab('profile')}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
                activeTab === 'profile'
                  ? 'bg-purple-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <User className="w-4 h-4" />
              プロファイル
            </button>
            <button
              onClick={() => setActiveTab('finetune')}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition relative ${
                activeTab === 'finetune'
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              カスタムAI
              {hasCustomModel && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
                activeTab === 'history'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <History className="w-4 h-4" />
              履歴
            </button>
            <button
              onClick={() => setActiveTab('stats')}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
                activeTab === 'stats'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              統計
            </button>
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
                activeTab === 'dashboard'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              ダッシュボード
            </button>
          </div>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main className="flex-1 overflow-hidden">
        <div className="max-w-4xl mx-auto h-full flex flex-col">
          {/* チャットエリア */}
          {activeTab === 'chat' && (
            <>
              <div className="flex-1 overflow-y-auto px-6 py-4">
                {messages.length === 0 ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center">
                      <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mx-auto mb-4 flex items-center justify-center">
                        <span className="text-white text-3xl font-bold">P</span>
                      </div>
                      <h2 className="text-2xl font-bold text-gray-900 mb-2">
                        こんにちは！
                      </h2>
                      <p className="text-gray-600">
                        何でも聞いてください。一緒に成長していきましょう！
                      </p>
                      {hasCustomModel && customModelName && (
                        <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-100 to-indigo-100 rounded-lg">
                          <Sparkles className="w-4 h-4 text-purple-600" />
                          <span className="text-sm text-purple-800 font-medium">
                            カスタムモデル利用可能
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <ChatMessage
                      key={idx}
                      role={msg.role}
                      content={msg.content}
                      timestamp={msg.timestamp}
                      conversationId={msg.conversationId}
                      rating={msg.rating}
                      reason={msg.reason}
                      tags={msg.tags}
                      onRate={handleRate}
                    />
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* 入力エリア */}
              <div className="border-t border-gray-200 bg-white px-6 py-4">
                <div className="flex items-center gap-2 mb-2">
                  <Settings className="w-4 h-4 text-gray-500" />
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="text-sm px-3 py-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {hasCustomModel && customModelName && (
                      <optgroup label="カスタムモデル">
                        <option value={customModelName}>
                          ✨ {customModelName} (あなた専用)
                        </option>
                      </optgroup>
                    )}
                    <optgroup label="標準モデル">
                      {models.filter(m => m !== customModelName).map(model => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </optgroup>
                  </select>
                  <span className="text-xs text-gray-500">
                    {loading ? '応答中...' : '準備完了'}
                  </span>
                </div>

                <div className="flex gap-2">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="メッセージを入力... (Shift+Enterで改行)"
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                    rows={2}
                    disabled={loading}
                  />
                  <button
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="px-6 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition flex items-center gap-2"
                  >
                    {loading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>
            </>
          )}

          {/* プロファイルタブ */}
          {activeTab === 'profile' && (
            <ProfileView userId={userId} />
          )}

          {/* ファインチューニングタブ */}
          {activeTab === 'finetune' && (
            <FineTunePanel userId={userId} onModelCreated={refreshModels} />
          )}

          {/* 履歴タブ */}
          {activeTab === 'history' && (
            <HistoryView userId={userId} />
          )}

          {/* 統計タブ */}
          {activeTab === 'stats' && (
            <StatsView userId={userId} />
          )}
          {/* ダッシュボードタブ */}
          {activeTab === 'dashboard' && (
            <DashboardView userId={userId} />
          )}
        </div>
      </main>
    </div>
  );
}