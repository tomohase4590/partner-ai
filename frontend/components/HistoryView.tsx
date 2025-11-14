// components/HistoryView.tsx
// 会話履歴を表示

import { useState, useEffect } from 'react';
import { Clock, ThumbsUp, ThumbsDown, Search, Filter } from 'lucide-react';
import { api, type Conversation } from '@/lib/api';
import { format } from 'date-fns';

interface HistoryViewProps {
  userId: string;
}

export default function HistoryView({ userId }: HistoryViewProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRating, setFilterRating] = useState<number | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const response = await api.getHistory(userId, 100);
      setConversations(response.conversations);
    } catch (error) {
      console.error('履歴取得エラー:', error);
    } finally {
      setLoading(false);
    }
  };

  // フィルタリング
  const filteredConversations = conversations.filter(conv => {
    const matchesSearch = 
      conv.user_message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      conv.ai_response.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesRating = 
      filterRating === null || conv.rating === filterRating;
    
    return matchesSearch && matchesRating;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">履歴を読み込み中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* ヘッダー */}
      <div className="p-6 border-b border-gray-200 bg-white">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">会話履歴</h2>
        
        {/* 検索とフィルター */}
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="会話を検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={() => setFilterRating(null)}
              className={`px-4 py-2 rounded-lg transition ${
                filterRating === null
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              全て
            </button>
            <button
              onClick={() => setFilterRating(5)}
              className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
                filterRating === 5
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <ThumbsUp className="w-4 h-4" />
              Good
            </button>
            <button
              onClick={() => setFilterRating(1)}
              className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
                filterRating === 1
                  ? 'bg-red-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <ThumbsDown className="w-4 h-4" />
              Bad
            </button>
          </div>
        </div>

        <div className="mt-3 text-sm text-gray-600">
          {filteredConversations.length} 件の会話
        </div>
      </div>

      {/* 会話リスト */}
      <div className="flex-1 overflow-y-auto p-6">
        {filteredConversations.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">会話履歴がありません</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredConversations.map((conv) => (
              <div
                key={conv.id}
                className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-md transition"
              >
                {/* タイムスタンプとモデル */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Clock className="w-4 h-4" />
                    {format(new Date(conv.timestamp), 'yyyy/MM/dd HH:mm')}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                      {conv.model_used}
                    </span>
                    {conv.rating === 5 && (
                      <ThumbsUp className="w-4 h-4 text-green-600" />
                    )}
                    {conv.rating === 1 && (
                      <ThumbsDown className="w-4 h-4 text-red-600" />
                    )}
                  </div>
                </div>

                {/* ユーザーメッセージ */}
                <div className="mb-3">
                  <div className="text-sm font-semibold text-gray-700 mb-1">
                    あなた:
                  </div>
                  <div className="text-gray-900 bg-blue-50 p-3 rounded-lg">
                    {conv.user_message}
                  </div>
                </div>

                {/* AI応答 */}
                <div>
                  <div className="text-sm font-semibold text-gray-700 mb-1">
                    AI:
                  </div>
                  <div className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                    {conv.ai_response.length > 200
                      ? `${conv.ai_response.slice(0, 200)}...`
                      : conv.ai_response}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}