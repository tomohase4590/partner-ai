/**
 * ファインチューニングUI
 * ユーザー専用モデルの作成と管理
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Sparkles, Loader2, Trash2, CheckCircle, AlertCircle } from 'lucide-react';
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

interface FineTunePanelProps {
  userId: string;
  onModelCreated?: () => void;  // コールバックを追加
}

export default function FineTunePanel({ userId, onModelCreated }: FineTunePanelProps) {
  const [readiness, setReadiness] = useState<ReadinessStatus | null>(null);
  const [models, setModels] = useState<CustomModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string>('');
  const [selectedBaseModel, setSelectedBaseModel] = useState('qwen2.5:7b');
  const [availableBaseModels, setAvailableBaseModels] = useState([
    { value: 'gemma2:2b', label: 'Gemma 2 2B (超軽量・最速)', description: '2GB RAM, 最も高速' },
    { value: 'gemma3:4b', label: 'Gemma 3 4B (軽量・高速)', description: '4GB RAM, バランス良好' },
    { value: 'qwen2.5:7b', label: 'Qwen 2.5 7B (推奨)', description: '8GB RAM, 高品質' },
    { value: 'gemma3:12b', label: 'Gemma 3 12B (高性能)', description: '12GB RAM, より高度' },
    { value: 'qwen2.5:14b', label: 'Qwen 2.5 14B (高性能)', description: '16GB RAM, 高品質' },
    { value: 'qwen2.5:32b', label: 'Qwen 2.5 32B (最高性能)', description: '32GB RAM, 最高品質' },
    { value: 'llama3.1:8b', label: 'Llama 3.1 8B (Meta)', description: '8GB RAM, Meta製' },
    { value: 'phi3:14b', label: 'Phi-3 14B (Microsoft)', description: '16GB RAM, Microsoft製' },
  ]);

  // データ取得
  useEffect(() => {
    loadReadiness();
    loadModels();
    loadAvailableModels();
  }, [userId]);

  const loadAvailableModels = async () => {
    try {
      const response = await api.getModels();
      // インストール済みのモデルから、カスタムモデルを除外
      const installedModels = response.models
        .filter(m => !m.name.includes('_custom_'))  // カスタムモデルを除外
        .map(m => ({
          value: m.name,
          label: `${m.name} (${m.size_gb}GB)`,
          description: `${m.parameter_size || 'Unknown'} パラメータ`,
          installed: true
        }));
      
      console.log('取得したモデル:', installedModels); // デバッグ用
      
      // インストール済みモデルがあればそれを使用
      if (installedModels.length > 0) {
        setAvailableBaseModels(installedModels);
        
        // デフォルトモデルを設定（推奨順）
        const preferredModels = ['qwen2.5:7b', 'gemma3:4b', 'qwen2.5:14b'];
        const defaultModel = installedModels.find(m => 
          preferredModels.includes(m.value)
        ) || installedModels[0];
        
        console.log('デフォルトモデル:', defaultModel.value); // デバッグ用
        setSelectedBaseModel(defaultModel.value);
      } else {
        // フォールバック：固定リスト
        console.warn('インストール済みモデルが見つかりません');
      }
    } catch (error) {
      console.error('利用可能なモデルの取得に失敗:', error);
    }
  };

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
        
        // 親コンポーネントに通知（メインチャットのモデルリストを更新）
        if (onModelCreated) {
          onModelCreated();
        }
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
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
      {/* ヘッダー */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-xl p-6 text-white">
        <div className="flex items-center gap-3 mb-3">
          <Sparkles className="w-8 h-8" />
          <h1 className="text-3xl font-bold">カスタムAIモデル</h1>
        </div>
        <p className="text-purple-100">
          あなたの会話履歴から学習した専用AIモデルを作成できます
        </p>
      </div>

      {/* 準備状況 */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          データ準備状況
        </h2>

        <div className="space-y-4">
          {/* プログレスバー */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-700 font-medium">トレーニング用会話</span>
              <span className="font-bold text-gray-900">
                {readiness.usable_for_training} / {readiness.required}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className="bg-gradient-to-r from-green-400 to-blue-500 h-4 rounded-full transition-all duration-500 flex items-center justify-end pr-2"
                style={{ width: `${readiness.progress_percentage}%` }}
              >
                {readiness.progress_percentage >= 20 && (
                  <span className="text-xs font-bold text-white">
                    {Math.round(readiness.progress_percentage)}%
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* 統計 */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200">
              <div className="text-2xl font-bold text-blue-800">
                {readiness.total_conversations}
              </div>
              <div className="text-sm text-blue-600 font-medium">総会話数</div>
            </div>
            <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
              <div className="text-2xl font-bold text-green-800">
                {readiness.high_rated_conversations}
              </div>
              <div className="text-sm text-green-600 font-medium">高評価会話</div>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg border border-purple-200">
              <div className="text-2xl font-bold text-purple-800">
                {readiness.usable_for_training}
              </div>
              <div className="text-sm text-purple-600 font-medium">使用可能</div>
            </div>
          </div>

          {/* ステータスメッセージ */}
          {!readiness.ready && (
            <div className="bg-yellow-50 border-l-4 border-yellow-400 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-yellow-800 font-medium">
                  あと{readiness.required - readiness.usable_for_training}件の会話が必要です
                </p>
                <p className="text-sm text-yellow-700 mt-1">
                  会話を続けて、気に入った応答に高評価（⭐⭐⭐以上）をつけてください
                </p>
              </div>
            </div>
          )}

          {readiness.ready && (
            <div className="bg-green-50 border-l-4 border-green-400 rounded-lg p-4 flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-green-800 font-bold">
                  カスタムモデルを作成できます！
                </p>
                <p className="text-sm text-green-700 mt-1">
                  十分なデータが集まりました。下のボタンから作成を開始できます。
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* モデル作成 */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-600" />
          新規モデル作成
        </h2>

        <div className="space-y-4">
          {/* ベースモデル選択 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ベースモデル
            </label>
            <select
              value={selectedBaseModel}
              onChange={(e) => setSelectedBaseModel(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm"
              disabled={loading}
            >
              {availableBaseModels.map(model => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
            
            {/* 選択されたモデルの説明 */}
            {selectedBaseModel && (
              <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="text-sm text-blue-800">
                  <span className="font-medium">
                    {availableBaseModels.find(m => m.value === selectedBaseModel)?.label}
                  </span>
                  <br />
                  <span className="text-xs">
                    {availableBaseModels.find(m => m.value === selectedBaseModel)?.description}
                  </span>
                </div>
              </div>
            )}
            
            <div className="mt-3 p-3 bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg">
              <p className="text-xs text-purple-800">
                <span className="font-medium">💡 選び方:</span>
                <br />
                • <strong>軽量モデル (2B-7B)</strong>: 高速、少ないメモリ、日常的な会話
                <br />
                • <strong>中型モデル (12B-14B)</strong>: バランス、複雑なタスク
                <br />
                • <strong>大型モデル (32B)</strong>: 最高品質、専門的なタスク
              </p>
            </div>
          </div>

          {/* 作成ボタン */}
          <button
            onClick={handleFineTune}
            disabled={!readiness.ready || loading}
            className={`w-full py-3 rounded-lg font-bold text-white transition-all flex items-center justify-center gap-2 ${
              !readiness.ready || loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 shadow-lg hover:shadow-xl'
            }`}
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                作成中...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                カスタムモデルを作成
              </>
            )}
          </button>

          {/* ステータス表示 */}
          {status && (
            <div
              className={`p-4 rounded-lg border ${
                status.includes('✅')
                  ? 'bg-green-50 border-green-200 text-green-800'
                  : status.includes('❌')
                  ? 'bg-red-50 border-red-200 text-red-800'
                  : 'bg-blue-50 border-blue-200 text-blue-800'
              }`}
            >
              {status}
            </div>
          )}

          {/* 説明 */}
          <div className="bg-gradient-to-br from-blue-50 to-purple-50 border border-purple-200 rounded-lg p-4">
            <h3 className="font-bold text-purple-900 mb-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              カスタムモデルとは？
            </h3>
            <ul className="text-sm text-purple-800 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-purple-600 mt-0.5">•</span>
                <span>あなたの会話スタイルと好みを学習したAI</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-purple-600 mt-0.5">•</span>
                <span>高評価の会話から最適な応答パターンを習得</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-purple-600 mt-0.5">•</span>
                <span>より自然で満足度の高い対話が可能に</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-purple-600 mt-0.5">•</span>
                <span>作成には3〜5分程度かかります</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* 既存モデル一覧 */}
      {models.length > 0 && (
        <div className="bg-white rounded-xl shadow-md p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            📦 作成済みモデル
          </h2>

          <div className="space-y-3">
            {models.map((model) => (
              <div
                key={model.model_name}
                className={`border rounded-lg p-4 transition-all ${
                  model.is_active
                    ? 'border-green-500 bg-green-50 shadow-md'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-bold text-gray-800">
                        {model.model_name}
                      </h3>
                      {model.is_active && (
                        <span className="px-2 py-1 bg-green-500 text-white text-xs rounded-full font-medium">
                          アクティブ
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-gray-600 space-y-1">
                      <p className="flex items-center gap-2">
                        <span className="font-medium">ベースモデル:</span>
                        <span>{model.base_model}</span>
                      </p>
                      <p className="flex items-center gap-2">
                        <span className="font-medium">学習データ:</span>
                        <span>{model.training_size}件の会話</span>
                      </p>
                      <p className="flex items-center gap-2">
                        <span className="font-medium">作成日時:</span>
                        <span>
                          {new Date(model.created_at).toLocaleString('ja-JP', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </span>
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeleteModel(model.model_name)}
                    className="ml-4 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
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
}

// BarChart3アイコンのインポート忘れを修正
function BarChart3(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 3v18h18" />
      <path d="M18 17V9" />
      <path d="M13 17V5" />
      <path d="M8 17v-3" />
    </svg>
  );
}