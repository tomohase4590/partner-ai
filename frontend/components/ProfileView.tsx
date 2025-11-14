// components/ProfileView.tsx
// ユーザープロファイルを表示

import { useState, useEffect } from 'react';
import { Brain, Heart, BookOpen, TrendingUp, Sparkles } from 'lucide-react';
import axios from 'axios';

interface ProfileViewProps {
  userId: string;
}

interface UserProfile {
  tone: string;
  interests: string[];
  preferences: string[];
  memories: string[];
  topic_counts: { [key: string]: number };
  total_conversations: number;
}

export default function ProfileView({ userId }: ProfileViewProps) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`http://localhost:8000/api/profile/${userId}`);
      setProfile(response.data.profile);
    } catch (error) {
      console.error('プロファイル取得エラー:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">プロファイルを読み込み中...</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">プロファイルを読み込めませんでした</p>
      </div>
    );
  }

  // トピックを頻度順にソート
  const sortedTopics = Object.entries(profile.topic_counts || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        {/* ヘッダー */}
        <div className="bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl p-8 text-white mb-6">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center backdrop-blur">
              <Brain className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-3xl font-bold">あなたのプロファイル</h2>
              <p className="text-purple-100">AIが学習した情報</p>
            </div>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              <span>総会話数: {profile.total_conversations}</span>
            </div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              <span>学習した記憶: {profile.memories.length}件</span>
            </div>
          </div>
        </div>

        {/* 興味・関心 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Heart className="w-6 h-6 text-red-500" />
            <h3 className="text-xl font-bold text-gray-900">興味・関心</h3>
          </div>

          {profile.interests.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              まだ興味・関心が学習されていません。
              <br />
              もっと会話を続けると、AIがあなたの興味を学習します！
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {profile.interests.map((interest, idx) => (
                <div
                  key={idx}
                  className="px-4 py-2 bg-gradient-to-r from-red-500 to-pink-500 text-white rounded-full font-semibold shadow-md"
                >
                  {interest}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 学習した記憶 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="w-6 h-6 text-purple-500" />
            <h3 className="text-xl font-bold text-gray-900">学習した記憶</h3>
          </div>

          {profile.memories.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              まだ記憶がありません。
              <br />
              会話を続けると、AIがあなたについて学習していきます！
            </p>
          ) : (
            <div className="space-y-3">
              {profile.memories.map((memory, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 bg-purple-500 text-white rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0">
                      {idx + 1}
                    </div>
                    <p className="text-gray-900 flex-1">{memory}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* よく話すトピック（詳細版） */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-6 h-6 text-blue-500" />
            <h3 className="text-xl font-bold text-gray-900">よく話すトピック</h3>
          </div>

          {sortedTopics.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              まだトピックが記録されていません。
            </p>
          ) : (
            <div className="space-y-3">
              {sortedTopics.map(([topic, count], idx) => {
                const maxCount = sortedTopics[0][1];
                const percentage = (count / maxCount) * 100;
                
                return (
                  <div key={topic} className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-sm">
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-gray-900">{topic}</span>
                        <span className="text-sm text-gray-500">{count}回</span>
                      </div>
                      <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* パーソナライゼーションのヒント */}
        <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg">
          <div className="flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-blue-600 flex-shrink-0 mt-1" />
            <div className="text-sm text-gray-700">
              <p className="font-semibold mb-1">💡 パーソナライゼーションについて</p>
              <p>
                会話を続けるほど、AIはあなたの興味や好みを学習し、
                より適切な応答ができるようになります。
                学習した情報は、今後の会話で自動的に活用されます！
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}