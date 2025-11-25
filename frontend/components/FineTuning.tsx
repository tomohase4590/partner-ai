/**
 * ファインチューニングUI
 * ユーザー専用モデルの作成と管理
 */

'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface ReadinessStatus {
  ready: boolean;
  total_conversations: number;
  high_rated_conversations: number;
  usable_for_training: number;
  required: number;
  progress_percentage: number;
}

interface CustomModel {
  model_name: string;
  base_model: string;
  training_size: number;
  created_at: string;
  is_active: boolean;
}

interface FineTuneProps {
  userId: string;
}

export const FineTunePanel: React.FC<FineTuneProps> = ({ userId }) => {
  const [readiness, setReadiness] = useState<ReadinessStatus | null>(null);
  const [models, setModels] = useState<CustomModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string>('');
  const [selectedBaseModel, setSelectedBaseModel] = useState('qwen2.5:32b');

  // データ取得
  useEffect(() => {
    loadReadiness();
    loadModels();
  }, [userId]);

  const loadReadiness = async () => {
    try {
      const res = await api.getFineTuneReadiness(userId);
      setReadiness(res);
    } catch (error) {
      console.error('準備状況の取得に失敗:', error);
    }
  };

  const loadModels = async () => {
    try {
      const res = await api.getCustomModels(userId);
      setModels(res.models);
    } catch (error) {
      console.error('モデル一覧の取得に失敗:', error);
    }
  };

  const handleFineTune = async () => {
    setLoading(true);
    setStatus('モデルを作成中... これには数分かかる場合があります');

    try {
      const res = await api.createFineTunedModel(userId, selectedBaseModel);

      if (res.status === 'insufficient_data') {
        setStatus(`❌ ${res.message}`);
      } else {
        setStatus(`✅ ${res.message}`);
        await loadModels();
        await loadReadiness();
      }
    } catch (error: any) {
      setStatus(`❌ エラー: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteModel = async (modelName: string) => {
    if (!confirm(`モデル ${modelName} を削除しますか？`)) {
      return;
    }

    try {
      await api.deleteCustomModel(userId, modelName);
      setStatus(`✅ モデル ${modelName} を削除しました`);
      await loadModels();
    } catch (error: any) {
      setStatus(`❌ 削除エラー: ${error.message}`);
    }
  };

  if (!readiness) {
    return <div className="p-4">読み込み中...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* ヘッダー */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg p-6 text-white">
        <h1 className="text-3xl font-bold mb-2">🧠 カスタムAIモデル</h1>
        <p className="text-purple-100">
          あなたの会話履歴から学習した専用AIモデルを作成できます
        </p>
      </div>

      {/* 準備状況 */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold mb-4">📊 データ準備状況</h2>

        <div className="space-y-4">
          {/* プログレスバー */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span>トレーニング用会話</span>
              <span className="font-bold">
                {readiness.usable_for_training} / {readiness.required}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className="bg-gradient-to-r from-green-400 to-blue-500 h-4 rounded-full transition-all duration-500"
                style={{ width: `${readiness.progress_percentage}%` }}
              />
            </div>
          </div>

          {/* 統計 */}
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-gray-800">
                {readiness.total_conversations}
              </div>
              <div className="text-sm text-gray-600">総会話数</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                {readiness.high_rated_conversations}
              </div>
              <div className="text-sm text-gray-600">高評価会話</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {readiness.usable_for_training}
              </div>
              <div className="text-sm text-gray-600">使用可能</div>
            </div>
          </div>

          {/* ステータスメッセージ */}
          {!readiness.ready && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-yellow-800">
                ⚠️ あと{readiness.required - readiness.usable_for_training}
                件の高評価会話が必要です
              </p>
              <p className="text-sm text-yellow-700 mt-2">
                会話を続けて、気に入った応答に高評価（⭐⭐⭐以上）をつけてください
              </p>
            </div>
          )}

          {readiness.ready && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-green-800 font-bold">
                ✅ カスタムモデルを作成できます！
              </p>
            </div>
          )}
        </div>
      </div>

      {/* モデル作成 */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold mb-4">🔧 新規モデル作成</h2>

        <div className="space-y-4">
          {/* ベースモデル選択 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ベースモデル
            </label>
            <select
              value={selectedBaseModel}
              onChange={(e) => setSelectedBaseModel(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              disabled={loading}
            >
              <option value="gemma3:4b">Gemma 3 4B (軽量・高速)</option>
              <option value="gemma3:12b">Gemma 3 12B (バランス)</option>
              <option value="qwen2.5:32b">Qwen 2.5 32B (高性能)</option>
            </select>
            <p className="text-sm text-gray-500 mt-1">
              軽量モデルは応答が速く、大型モデルはより高度な理解が可能です
            </p>
          </div>

          {/* 作成ボタン */}
          <button
            onClick={handleFineTune}
            disabled={!readiness.ready || loading}
            className={`w-full py-3 rounded-lg font-bold text-white transition-all ${
              !readiness.ready || loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700'
            }`}
          >
            {loading ? '⏳ 作成中...' : '🚀 カスタムモデルを作成'}
          </button>

          {/* ステータス表示 */}
          {status && (
            <div
              className={`p-4 rounded-lg ${
                status.includes('✅')
                  ? 'bg-green-50 text-green-800'
                  : status.includes('❌')
                  ? 'bg-red-50 text-red-800'
                  : 'bg-blue-50 text-blue-800'
              }`}
            >
              {status}
            </div>
          )}

          {/* 説明 */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-bold text-blue-900 mb-2">💡 カスタムモデルとは？</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• あなたの会話スタイルと好みを学習したAI</li>
              <li>• 高評価の会話から最適な応答パターンを習得</li>
              <li>• より自然で満足度の高い対話が可能に</li>
              <li>• 作成には3〜5分程度かかります</li>
            </ul>
          </div>
        </div>
      </div>

      {/* 既存モデル一覧 */}
      {models.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold mb-4">📦 作成済みモデル</h2>

          <div className="space-y-3">
            {models.map((model) => (
              <div
                key={model.model_name}
                className={`border rounded-lg p-4 ${
                  model.is_active
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-bold text-gray-800">
                        {model.model_name}
                      </h3>
                      {model.is_active && (
                        <span className="px-2 py-1 bg-green-500 text-white text-xs rounded-full">
                          アクティブ
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-gray-600 space-y-1">
                      <p>ベースモデル: {model.base_model}</p>
                      <p>学習データ: {model.training_size}件</p>
                      <p>
                        作成日時:{' '}
                        {new Date(model.created_at).toLocaleString('ja-JP')}
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeleteModel(model.model_name)}
                    className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                  >
                    削除
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FineTunePanel;