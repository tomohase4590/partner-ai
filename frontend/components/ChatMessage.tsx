// components/ChatMessage.tsx
// 個別のチャットメッセージを表示

import { useState } from 'react';
import { Bot, User, ThumbsUp, ThumbsDown, Info, Tag } from 'lucide-react';
import { format } from 'date-fns';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  conversationId?: number;
  rating?: number | null;
  reason?: string;
  tags?: string[];
  onRate?: (conversationId: number, rating: number, comment?: string) => void;
}

export default function ChatMessage({
  role,
  content,
  timestamp,
  conversationId,
  rating,
  reason,
  tags,
  onRate
}: ChatMessageProps) {
  const isUser = role === 'user';
  const [showReason, setShowReason] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackComment, setFeedbackComment] = useState('');

  const handleRate = (newRating: number) => {
    if (!conversationId || !onRate) return;
    
    if (newRating === 1) {
      // Bad評価の場合、コメント入力を表示
      setShowFeedback(true);
    } else {
      // Good評価の場合、すぐに送信
      onRate(conversationId, newRating);
    }
  };

  const submitFeedback = () => {
    if (conversationId && onRate) {
      onRate(conversationId, 1, feedbackComment);
      setShowFeedback(false);
      setFeedbackComment('');
    }
  };

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-4`}>
      {/* アイコン */}
      <div
        className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-500' : 'bg-gray-700'
        }`}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>

      {/* メッセージ本体 */}
      <div className={`flex-1 max-w-[70%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-900 border border-gray-200'
          }`}
        >
          <p className="whitespace-pre-wrap break-words">{content}</p>
        </div>

        {/* タグ表示 */}
        {!isUser && tags && tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2 px-2">
            {tags.map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs"
              >
                <Tag className="w-3 h-3" />
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* 応答理由 */}
        {!isUser && reason && (
          <div className="mt-2 px-2">
            <button
              onClick={() => setShowReason(!showReason)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition"
            >
              <Info className="w-3 h-3" />
              {showReason ? '理由を隠す' : 'なぜこの回答？'}
            </button>
            {showReason && (
              <div className="mt-1 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-gray-700">
                {reason}
              </div>
            )}
          </div>
        )}

        {/* タイムスタンプと評価ボタン */}
        <div className={`flex items-center gap-2 mt-1 px-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          {timestamp && (
            <span className="text-xs text-gray-500">
              {format(new Date(timestamp), 'HH:mm')}
            </span>
          )}

          {/* AI応答の場合のみ評価ボタン表示 */}
          {!isUser && conversationId && onRate && (
            <div className="flex gap-1">
              <button
                onClick={() => handleRate(5)}
                className={`p-1 rounded hover:bg-gray-200 transition ${
                  rating === 5 ? 'text-green-600' : 'text-gray-400'
                }`}
                title="Good"
              >
                <ThumbsUp className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleRate(1)}
                className={`p-1 rounded hover:bg-gray-200 transition ${
                  rating === 1 ? 'text-red-600' : 'text-gray-400'
                }`}
                title="Bad"
              >
                <ThumbsDown className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* フィードバックコメント入力 */}
        {showFeedback && (
          <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg w-full">
            <p className="text-sm text-gray-700 mb-2">何が改善できますか？</p>
            <textarea
              value={feedbackComment}
              onChange={(e) => setFeedbackComment(e.target.value)}
              placeholder="例: もっと具体的な説明が欲しかった"
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm resize-none"
              rows={2}
            />
            <div className="flex gap-2 mt-2">
              <button
                onClick={submitFeedback}
                className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
              >
                送信
              </button>
              <button
                onClick={() => setShowFeedback(false)}
                className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
              >
                キャンセル
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}