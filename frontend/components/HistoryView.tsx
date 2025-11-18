// components/HistoryView.tsx
// 会話履歴を表示

import { useState, useEffect } from 'react';
import { Clock, ThumbsUp, ThumbsDown, Search, Filter, Calendar, Tag as TagIcon, X, Plus } from 'lucide-react';
import { api, type Conversation } from '@/lib/api';
import { format, parseISO, isAfter, isBefore } from 'date-fns';

interface HistoryViewProps {
  userId: string;
}

export default function HistoryView({ userId }: HistoryViewProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRating, setFilterRating] = useState<number | null>(null);
  const [filterTag, setFilterTag] = useState<string>('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [allTags, setAllTags] = useState<string[]>([]);
  const [editingTags, setEditingTags] = useState<number | null>(null);
  const [newTag, setNewTag] = useState('');

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const response = await api.getHistory(userId, 100);
      setConversations(response.conversations);
      
      // 全タグを抽出
      const tags = new Set<string>();
      response.conversations.forEach(conv => {
        conv.tags?.forEach(tag => tags.add(tag));
      });
      setAllTags(Array.from(tags));
    } catch (error) {
      console.error('履歴取得エラー:', error);
    } finally {
      setLoading(false);
    }
  };

  // タグを追加
  const addTag = async (conversationId: number, currentTags: string[]) => {
    if (!newTag.trim()) return;
    
    const updatedTags = [...currentTags, newTag.trim()];
    
    try {
      await api.updateConversationTags(conversationId, updatedTags);
      
      // ローカルステートを更新
      setConversations(prev =>
        prev.map(conv =>
          conv.id === conversationId
            ? { ...conv, tags: updatedTags }
            : conv
        )
      );
      
      // 全タグリストを更新
      if (!allTags.includes(newTag.trim())) {
        setAllTags(prev => [...prev, newTag.trim()]);
      }
      
      setNewTag('');
    } catch (error) {
      console.error('タグ追加エラー:', error);
    }
  };

  // タグを削除
  const removeTag = async (conversationId: number, currentTags: string[], tagToRemove: string) => {
    const updatedTags = currentTags.filter(t => t !== tagToRemove);
    
    try {
      await api.updateConversationTags(conversationId, updatedTags);
      
      setConversations(prev =>
        prev.map(conv =>
          conv.id === conversationId
            ? { ...conv, tags: updatedTags }
            : conv
        )
      );
    } catch (error) {
      console.error('タグ削除エラー:', error);
    }
  };

  // フィルタリング
  const filteredConversations = conversations.filter(conv => {
    // ワード検索
    const matchesSearch = 
      conv.user_message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      conv.ai_response.toLowerCase().includes(searchQuery.toLowerCase());
    
    // 評価フィルタ
    const matchesRating = 
      filterRating === null || conv.rating === filterRating;
    
    // タグフィルタ
    const matchesTag = 
      !filterTag || (conv.tags && conv.tags.includes(filterTag));
    
    // 日付フィルタ
    let matchesDate = true;
    if (startDate || endDate) {
      const convDate = parseISO(conv.timestamp);
      if (startDate && isBefore(convDate, parseISO(startDate))) {
        matchesDate = false;
      }
      if (endDate && isAfter(convDate, parseISO(endDate + 'T23:59:59'))) {
        matchesDate = false;
      }
    }
    
    return matchesSearch && matchesRating && matchesTag && matchesDate;
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
        
        {/* 検索バー */}
        <div className="mb-4 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="会話を検索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* フィルター */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* 日付範囲 */}
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-500" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="flex-1 text-sm px-2 py-1 border border-gray-300 rounded"
              placeholder="開始日"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">〜</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="flex-1 text-sm px-2 py-1 border border-gray-300 rounded"
              placeholder="終了日"
            />
          </div>

          {/* タグフィルタ */}
          <div className="flex items-center gap-2">
            <TagIcon className="w-4 h-4 text-gray-500" />
            <select
              value={filterTag}
              onChange={(e) => setFilterTag(e.target.value)}
              className="flex-1 text-sm px-2 py-1 border border-gray-300 rounded"
            >
              <option value="">全てのタグ</option>
              {allTags.map(tag => (
                <option key={tag} value={tag}>{tag}</option>
              ))}
            </select>
          </div>

          {/* 評価フィルタ */}
          <div className="flex gap-2">
            <button
              onClick={() => setFilterRating(null)}
              className={`flex-1 px-3 py-1 rounded text-sm transition ${
                filterRating === null
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              全て
            </button>
            <button
              onClick={() => setFilterRating(5)}
              className={`flex-1 px-3 py-1 rounded text-sm transition ${
                filterRating === 5
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <ThumbsUp className="w-3 h-3 inline" />
            </button>
            <button
              onClick={() => setFilterRating(1)}
              className={`flex-1 px-3 py-1 rounded text-sm transition ${
                filterRating === 1
                  ? 'bg-red-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <ThumbsDown className="w-3 h-3 inline" />
            </button>
          </div>
        </div>

        {/* フィルタクリア */}
        {(searchQuery || filterRating !== null || filterTag || startDate || endDate) && (
          <button
            onClick={() => {
              setSearchQuery('');
              setFilterRating(null);
              setFilterTag('');
              setStartDate('');
              setEndDate('');
            }}
            className="mt-3 text-sm text-blue-600 hover:text-blue-800"
          >
            フィルタをクリア
          </button>
        )}

        <div className="mt-3 text-sm text-gray-600">
          {filteredConversations.length} 件の会話
        </div>
      </div>

      {/* 会話リスト */}
      <div className="flex-1 overflow-y-auto p-6">
        {filteredConversations.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">該当する会話がありません</p>
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
                    {format(parseISO(conv.timestamp), 'yyyy/MM/dd HH:mm')}
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

                {/* タグ表示・編集 */}
                <div className="mb-3">
                  <div className="flex flex-wrap gap-2 items-center">
                    {conv.tags && conv.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm"
                      >
                        <TagIcon className="w-3 h-3" />
                        {tag}
                        {editingTags === conv.id && (
                          <button
                            onClick={() => removeTag(conv.id, conv.tags || [], tag)}
                            className="hover:text-red-600"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        )}
                      </span>
                    ))}
                    
                    {/* タグ追加ボタン */}
                    {editingTags === conv.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={newTag}
                          onChange={(e) => setNewTag(e.target.value)}
                          onKeyPress={(e) => {
                            if (e.key === 'Enter') {
                              addTag(conv.id, conv.tags || []);
                            }
                          }}
                          placeholder="新しいタグ"
                          className="px-2 py-1 text-sm border border-gray-300 rounded w-32"
                        />
                        <button
                          onClick={() => addTag(conv.id, conv.tags || [])}
                          className="p-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => {
                            setEditingTags(null);
                            setNewTag('');
                          }}
                          className="text-sm text-gray-600 hover:text-gray-800"
                        >
                          完了
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setEditingTags(conv.id)}
                        className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                      >
                        + タグ追加
                      </button>
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