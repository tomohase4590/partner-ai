import { useState, useEffect } from 'react';
import { Bell, X, MessageCircle, Clock, Sparkles } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

interface AIMessage {
  id: number;
  message_type: string;
  content: string;
  scheduled_time: string;
  priority: number;
}

interface Props {
  userId: string;
  onMessageClick?: (message: AIMessage) => void;
}

export default function AIMessageNotification({ userId, onMessageClick }: Props) {
  const [messages, setMessages] = useState<AIMessage[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<AIMessage | null>(null);
  const [replyText, setReplyText] = useState('');
  const [replying, setReplying] = useState(false);

  // 30秒ごとにメッセージをチェック
  useEffect(() => {
    checkMessages();
    const interval = setInterval(checkMessages, 30000);
    return () => clearInterval(interval);
  }, [userId]);

  const checkMessages = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/messages/${userId}/pending`);
      const data = await response.json();
      
      if (data.has_messages && data.messages.length > 0) {
        setMessages(data.messages);
        
        // 新しいメッセージがあれば自動で開く
        if (data.messages.length > 0 && !showModal) {
          setShowModal(true);
          setSelectedMessage(data.messages[0]);
        }
      } else {
        setMessages([]);
      }
    } catch (error) {
      console.error('メッセージ取得エラー:', error);
    }
  };

  const handleAcknowledge = async (messageId: number) => {
    try {
      await fetch(`${API_BASE_URL}/api/messages/${userId}/${messageId}/acknowledge`, {
        method: 'POST'
      });
      
      // メッセージリストから削除
      setMessages(prev => prev.filter(m => m.id !== messageId));
      
      if (messages.length <= 1) {
        setShowModal(false);
        setSelectedMessage(null);
      } else {
        // 次のメッセージを表示
        const nextMessage = messages.find(m => m.id !== messageId);
        if (nextMessage) {
          setSelectedMessage(nextMessage);
        }
      }
    } catch (error) {
      console.error('確認エラー:', error);
    }
  };

  const handleReply = async () => {
    if (!selectedMessage || !replyText.trim()) return;
    
    setReplying(true);
    try {
      await fetch(`${API_BASE_URL}/api/messages/${userId}/${selectedMessage.id}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: replyText })
      });
      
      setReplyText('');
      handleAcknowledge(selectedMessage.id);
    } catch (error) {
      console.error('返信エラー:', error);
    } finally {
      setReplying(false);
    }
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'morning_checkin':
        return '☀️';
      case 'evening_reflection':
        return '🌙';
      case 'task_reminder':
        return '📌';
      case 'habit_reminder':
        return '🔔';
      case 'weekly_review':
        return '📊';
      case 'encouragement':
        return '💪';
      default:
        return '💬';
    }
  };

  const getMessageTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'morning_checkin': '朝のチェックイン',
      'evening_reflection': '夜の振り返り',
      'task_reminder': 'タスクリマインダー',
      'habit_reminder': '習慣リマインダー',
      'weekly_review': '週次振り返り',
      'encouragement': '励ましメッセージ'
    };
    return labels[type] || 'メッセージ';
  };

  return (
    <>
      {/* 通知バッジ */}
      {messages.length > 0 && (
        <button
          onClick={() => {
            setShowModal(true);
            if (!selectedMessage && messages[0]) {
              setSelectedMessage(messages[0]);
            }
          }}
          className="relative p-2 rounded-lg hover:bg-gray-100 transition"
        >
          <Bell className="w-5 h-5 text-gray-700" />
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center animate-pulse">
            {messages.length}
          </span>
        </button>
      )}

      {/* メッセージモーダル */}
      {showModal && selectedMessage && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
            {/* ヘッダー */}
            <div className="bg-gradient-to-r from-blue-500 to-indigo-600 p-6 text-white">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{getMessageIcon(selectedMessage.message_type)}</span>
                  <div>
                    <h3 className="text-xl font-bold">
                      {getMessageTypeLabel(selectedMessage.message_type)}
                    </h3>
                    <p className="text-sm text-blue-100 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(selectedMessage.scheduled_time).toLocaleString('ja-JP', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setShowModal(false);
                    setSelectedMessage(null);
                  }}
                  className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              {messages.length > 1 && (
                <div className="text-sm text-blue-100">
                  {messages.length}件のメッセージ
                </div>
              )}
            </div>

            {/* メッセージ本文 */}
            <div className="p-6 max-h-[400px] overflow-y-auto">
              <div className="prose prose-sm max-w-none">
                <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                  {selectedMessage.content}
                </p>
              </div>
            </div>

            {/* 返信エリア */}
            <div className="border-t p-4 bg-gray-50">
              <textarea
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                placeholder="返信を入力..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
              />
              
              <div className="flex gap-2 mt-3">
                <button
                  onClick={handleReply}
                  disabled={!replyText.trim() || replying}
                  className="flex-1 py-2 px-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
                >
                  {replying ? (
                    <>
                      <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                      返信中...
                    </>
                  ) : (
                    <>
                      <MessageCircle className="w-4 h-4" />
                      返信する
                    </>
                  )}
                </button>
                
                <button
                  onClick={() => handleAcknowledge(selectedMessage.id)}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition"
                >
                  確認のみ
                </button>
              </div>
            </div>

            {/* 次のメッセージボタン */}
            {messages.length > 1 && (
              <div className="border-t p-4 bg-blue-50">
                <button
                  onClick={() => {
                    const currentIndex = messages.findIndex(m => m.id === selectedMessage.id);
                    const nextIndex = (currentIndex + 1) % messages.length;
                    setSelectedMessage(messages[nextIndex]);
                    setReplyText('');
                  }}
                  className="w-full py-2 text-blue-600 hover:text-blue-800 font-medium transition flex items-center justify-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  次のメッセージ ({messages.length - 1}件残り)
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}