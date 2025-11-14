// components/StatsView.tsx
// 統計情報を表示

import { useState, useEffect } from 'react';
import { MessageSquare, Star, Bot, TrendingUp, ThumbsUp, ThumbsDown } from 'lucide-react';
import { api, type Stats, type Conversation } from '@/lib/api';

interface StatsViewProps {
  userId: string;
}

interface TopicCount {
  topic: string;
  count: number;
}

export default function StatsView({ userId }: StatsViewProps) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const [statsData, historyData] = await Promise.all([
        api.getStats(userId),
        api.getHistory(userId, 100)
      ]);
      
      setStats(statsData);
      setConversations(historyData.conversations);
    } catch (error) {
      console.error('統計取得エラー:', error);
    } finally {
      setLoading(false);
    }
  };

  // トピック抽出（簡易版）
  const extractTopics = (): TopicCount[] => {
    const keywords = ['Python', 'JavaScript', 'React', 'AI', 'プログラミング', '機械学習', 'Web', 'データ', 'アルゴリズム'];
    const topicCounts: { [key: string]: number } = {};

    conversations.forEach(conv => {
      const text = `${conv.user_message} ${conv.ai_response}`;
      keywords.forEach(keyword => {
        if (text.includes(keyword)) {
          topicCounts[keyword] = (topicCounts[keyword] || 0) + 1;
        }
      });
    });

    return Object.entries(topicCounts)
      .map(([topic, count]) => ({ topic, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  };

  // 評価の集計
  const getRatingStats = () => {
    const total = conversations.filter(c => c.rating !== null).length;
    const good = conversations.filter(c => c.rating === 5).length;
    const bad = conversations.filter(c => c.rating === 1).length;
    
    return { total, good, bad, goodRate: total > 0 ? (good / total * 100).toFixed(1) : 0 };
  };

  // モデル使用回数
  const getModelUsage = () => {
    const modelCounts: { [key: string]: number } = {};
    
    conversations.forEach(conv => {
      const model = conv.model_used;
      modelCounts[model] = (modelCounts[model] || 0) + 1;
    });

    return Object.entries(modelCounts)
      .map(([model, count]) => ({ model, count }))
      .sort((a, b) => b.count - a.count);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">統計を読み込み中...</p>
        </div>
      </div>
    );
  }

  const topics = extractTopics();
  const ratingStats = getRatingStats();
  const modelUsage = getModelUsage();

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">統計ダッシュボード</h2>

        {/* サマリーカード */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {/* 総会話数 */}
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-2">
              <MessageSquare className="w-8 h-8 opacity-80" />
              <TrendingUp className="w-6 h-6 opacity-60" />
            </div>
            <div className="text-3xl font-bold mb-1">
              {stats?.total_conversations || 0}
            </div>
            <div className="text-blue-100 text-sm">総会話数</div>
          </div>

          {/* 平均評価 */}
          <div className="bg-gradient-to-br from-yellow-500 to-orange-500 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-2">
              <Star className="w-8 h-8 opacity-80" />
              <span className="text-2xl opacity-60">⭐</span>
            </div>
            <div className="text-3xl font-bold mb-1">
              {stats?.average_rating.toFixed(1) || '0.0'}
            </div>
            <div className="text-orange-100 text-sm">平均評価</div>
          </div>

          {/* 最も使用したモデル */}
          <div className="bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-2">
              <Bot className="w-8 h-8 opacity-80" />
            </div>
            <div className="text-lg font-bold mb-1 truncate">
              {stats?.most_used_model || 'N/A'}
            </div>
            <div className="text-purple-100 text-sm">よく使うモデル</div>
          </div>
        </div>

        {/* 評価の内訳 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">評価の内訳</h3>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ThumbsUp className="w-5 h-5 text-green-600" />
                <span className="text-gray-700">Good評価</span>
              </div>
              <div className="text-right">
                <span className="text-2xl font-bold text-gray-900">{ratingStats.good}</span>
                <span className="text-sm text-gray-500 ml-2">
                  ({ratingStats.goodRate}%)
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ThumbsDown className="w-5 h-5 text-red-600" />
                <span className="text-gray-700">Bad評価</span>
              </div>
              <div className="text-right">
                <span className="text-2xl font-bold text-gray-900">{ratingStats.bad}</span>
              </div>
            </div>

            {/* プログレスバー */}
            {ratingStats.total > 0 && (
              <div className="pt-4">
                <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-green-500 to-green-600"
                    style={{ width: `${ratingStats.goodRate}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* よく話すトピック */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">よく話すトピック</h3>
          
          {topics.length === 0 ? (
            <p className="text-gray-500 text-center py-4">まだデータがありません</p>
          ) : (
            <div className="space-y-3">
              {topics.map((topic, idx) => (
                <div key={topic.topic} className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-sm">
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-gray-900">{topic.topic}</span>
                      <span className="text-sm text-gray-500">{topic.count}回</span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500"
                        style={{ width: `${(topic.count / conversations.length) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* モデル使用統計 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">モデル使用統計</h3>
          
          {modelUsage.length === 0 ? (
            <p className="text-gray-500 text-center py-4">まだデータがありません</p>
          ) : (
            <div className="space-y-3">
              {modelUsage.map((item) => (
                <div key={item.model} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bot className="w-5 h-5 text-purple-600" />
                    <span className="text-gray-700">{item.model}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500"
                        style={{ width: `${(item.count / conversations.length) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-900 w-12 text-right">
                      {item.count}回
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}