# パートナーAI テストシステム

RAG、プロファイル学習、ファインチューニングの効果を検証するテストシステム

## 📁 ファイル構成

```
tests/
├── README.md              # このファイル
├── baseline_system.py     # ベースライン比較システム（標準Ollama）
├── test_system.py         # 統合テストシステム（RAG + プロファイル + FT）
├── run_all_tests.py       # 全テスト実行スクリプト（Python版）
└── run_all_tests.sh       # 全テスト実行スクリプト（Bash版）
```

## 🎯 テストの目的

1. **ベースライン測定**: 標準的なOllamaチャットの性能
2. **RAG効果検証**: 関連する過去の会話を参照することによる改善
3. **プロファイル学習**: ユーザーの興味・好みを学習することによる改善
4. **ファインチューニング**: ユーザー専用モデルの効果

## 🚀 実行方法

### クイックスタート

```bash
# testsディレクトリに移動
cd tests

# Python版（推奨）
python3 run_all_tests.py

# または Bash版
chmod +x run_all_tests.sh
./run_all_tests.sh
```

### 個別実行

```bash
# ベースラインテストのみ
python3 baseline_system.py

# 統合テストのみ
python3 test_system.py
```

## 📊 テストフロー

### 1. ベースラインテスト（baseline_system.py）

標準的なOllamaチャットをテスト：

```
[ユーザー] → [Ollama] → [応答]
              ↑
         標準プロンプトのみ
         記憶・学習なし
```

**実行内容:**
- 8件の会話を実行
- コンテキストありなしの比較
- 統計情報の収集

**出力:**
- `baseline_report_YYYYMMDD_HHMMSS.json`

### 2. 統合テスト（test_system.py）

拡張機能の効果を検証：

```
[ユーザー] → [RAG検索] → [プロファイル] → [Ollama] → [応答]
              ↓              ↓
          関連記憶        興味・好み
```

**実行内容:**

#### Phase 1: データベースリセット
- 既存のDBとChromaDBを削除
- 新規データベースを初期化

#### Phase 2: 学習フェーズ
- 15件のテスト会話を生成
- 各会話をAIで処理
- RAGに記憶を保存
- プロファイルを更新

#### Phase 3: 比較テスト
1. **ベースライン**: 標準モデルでの応答
2. **RAG + プロファイル**: 記憶と学習を活用した応答
3. **ファインチューニング**: カスタムモデルでの応答

**出力:**
- `test_report_YYYYMMDD_HHMMSS.json`

## 📋 テストデータ

### 会話カテゴリ

1. **興味・趣味** (5件)
   - 機械学習への興味
   - プログラミングの話題
   - 技術書のおすすめ

2. **個人情報** (2件)
   - 職業（エンジニア）
   - 趣味（カフェでコーディング）

3. **技術的質問** (8件)
   - Transformer, BERT, GPT
   - PyTorch vs TensorFlow
   - ハイパーパラメータチューニング

### テストクエリ

```python
test_queries = [
    "機械学習の勉強方法でおすすめを教えて",
    "私の趣味に合ったプロジェクトのアイデアある？",
    "Python機械学習ライブラリについて教えて"
]
```

## 📈 評価指標

### 1. 応答の長さ
```json
{
  "baseline": 150,
  "enhanced": 250,
  "improvement": "+66.7%"
}
```

### 2. 学習内容
```json
{
  "interests_learned": ["機械学習", "Python", "ディープラーニング"],
  "memories_count": 15,
  "relevant_memories_used": 3
}
```

### 3. ファインチューニング
```json
{
  "model_name": "test_user_001_custom_20250115_143022",
  "training_size": 15,
  "evaluation_success_rate": 100.0
}
```

## 📄 レポート形式

### baseline_report_*.json

```json
{
  "timestamp": "2025-01-15T14:30:00",
  "model": "gemma3:4b",
  "conversation_results": {
    "results": [...],
    "stats": {
      "total_conversations": 8,
      "avg_response_length": 145.5,
      "total_characters": 1164
    }
  },
  "context_comparison": {
    "no_context": {...},
    "with_context": {...}
  }
}
```

### test_report_*.json

```json
{
  "test_query": "機械学習の勉強方法でおすすめを教えて",
  "timestamp": "2025-01-15T14:35:00",
  "baseline": {
    "response": "...",
    "length": 150
  },
  "enhanced": {
    "response": "...",
    "length": 250,
    "interests_learned": ["機械学習", "Python"],
    "memories_count": 3,
    "system_prompt": "..."
  },
  "finetuning": {
    "status": "success",
    "model_name": "test_user_001_custom_...",
    "evaluation": {...}
  }
}
```

## 🔍 結果の分析

### 期待される改善

1. **RAG効果**
   - 過去の関連会話を参照 → より具体的な応答
   - コンテキストを維持 → 一貫性の向上

2. **プロファイル学習**
   - ユーザーの興味を考慮 → パーソナライズされた応答
   - 記憶を活用 → 自然な会話

3. **ファインチューニング**
   - ユーザー固有のスタイル学習 → 好みに合った応答
   - 高評価会話から学習 → 品質向上

### 比較ポイント

| 項目 | ベースライン | 拡張機能 | ファインチューニング |
|------|--------------|----------|----------------------|
| 記憶の活用 | ❌ | ✅ | ✅ |
| プロファイル | ❌ | ✅ | ✅ |
| カスタム学習 | ❌ | ❌ | ✅ |
| 応答速度 | 🟢 速い | 🟡 普通 | 🟡 普通 |
| セットアップ | 🟢 簡単 | 🟡 中程度 | 🔴 複雑 |

## 🛠️ トラブルシューティング

### Ollamaが見つからない

```bash
# Ollamaのインストール確認
ollama --version

# モデルの確認
ollama list
```

### データ不足エラー

```
⚠️ データ不足のためファインチューニングをスキップ
```

→ テスト会話数を増やす（`generate_test_conversations()`を編集）

### ChromaDBエラー

```bash
# ChromaDBディレクトリを削除
rm -rf test_chroma_db/
```

### メモリ不足

```python
# より軽量なモデルを使用
self.base_model = "gemma3:4b"  # または "phi:latest"
```

## 📝 カスタマイズ

### テスト会話の追加

```python
# test_system.py の generate_test_conversations() を編集
conversations.append({
    "user": "新しいテスト会話",
    "rating": 5,
    "category": "custom"
})
```

### テストクエリの変更

```python
# run_all_tests.py または test_system.py の最後を編集
test_queries = [
    "あなたのカスタムクエリ1",
    "あなたのカスタムクエリ2",
]
```

### モデルの変更

```python
# test_system.py
self.base_model = "qwen2.5:32b"  # より大きなモデル
```

## 🎓 使用例

### 実際の出力例

```
==================================================================
🔬 比較テスト開始
==================================================================

テストクエリ: 機械学習の勉強方法でおすすめを教えて

==================================================================
🗑️  データベースリセット
==================================================================
✅ test_partner_ai.db を削除
✅ test_chroma_db を削除
✅ 新しいデータベースを初期化

==================================================================
📊 ベースライン測定（RAG/プロファイルなし）
==================================================================

応答:
機械学習の勉強は、まず基礎から始めることをお勧めします...

==================================================================
🚀 拡張機能テスト（RAG + プロファイル学習）
==================================================================

📝 15件の会話を学習中...
✅ 学習完了

📊 学習したプロファイル:
  興味: ['機械学習', 'Python', 'ディープラーニング', 'プログラミング']
  記憶: 15件

🔍 関連する記憶: 3件
  - 最近、機械学習の勉強を始めたんだ
  - PythonでNeuralNetworkを実装したいんだけど
  - ディープラーニングの本でおすすめある？

応答:
あなたが最近機械学習の勉強を始めたとのことですが、
Pythonを使ったプログラミングがお好きなようですね...
```

## 📚 参考

- [Ollama Documentation](https://github.com/ollama/ollama)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [パートナーAI メインドキュメント](../README.md)