
# ResearchEnvironment.md

## 1. 目的

本ドキュメントは、日本株自動売買システムにおける **研究環境（Research Environment）** の設計を定義する。

研究環境とは、以下を安全に実行するための環境である。

- 新しい売買戦略の開発
- ファクターの検証
- AIモデルの評価
- バックテスト
- パラメータチューニング

研究環境は **本番環境と完全に分離**される必要がある。

理由

- 誤発注防止
- 本番システム安定性維持
- 実験の自由度確保

---

# 2. Research環境の役割

Research環境では以下を行う。

| 機能 | 内容 |
|----|----|
データ分析 | 市場データ分析 |
戦略開発 | 新戦略の設計 |
バックテスト | 過去データ検証 |
AIモデル開発 | NLP / レジームモデル |
特徴量生成 | 新ファクター開発 |

Research環境は **Execution環境とは完全に分離する**。

---

# 3. 環境構成

推奨構成

```
Research Server (Linux)
```
または

```
Local Workstation
```

用途

- Python分析
- データ処理
- バックテスト

---

# 4. 使用技術スタック

推奨スタック

| 種類 | 技術 |
|----|----|
言語 | Python |
| 分析 | pandas |
| 数値計算 | numpy |
| 機械学習 | scikit-learn |
| 可視化 | matplotlib |
| ノートブック | Jupyter |
| データ処理 | DuckDB |
| データ保存 | Parquet |

---

# 5. データアクセス

Research環境は DataPlatform にアクセスする。

```
DataPlatform
      ↓
Research
      ↓
Backtest
```

対象データ

- 株価データ
- 財務データ
- AIスコア
- ニュースデータ

---

# 6. 研究プロセス

戦略開発は以下の流れで行う。

```
アイデア
↓
データ分析
↓
特徴量作成
↓
バックテスト
↓
パラメータ調整
↓
アウトオブサンプル検証
↓
本番導入
```

---

# 7. バックテスト連携

Research環境では BacktestFramework を利用する。

処理フロー

```
DataPlatform
↓
Feature Generation
↓
Strategy Simulation
↓
Performance Evaluation
```

---

# 8. 実験管理

研究では実験結果を保存する。

保存内容

- 戦略パラメータ
- 使用データ期間
- 成績指標
- モデルバージョン

推奨

```
experiment_logs
```

---

# 9. 評価指標

戦略評価では以下を使用する。

| 指標 | 内容 |
|----|----|
CAGR | 年率リターン |
Sharpe Ratio | リスク調整後リターン |
Max Drawdown | 最大損失 |
Win Rate | 勝率 |
Turnover | 売買回転率 |

---

# 10. 再現性

研究結果は再現可能である必要がある。

そのため

- データバージョン管理
- コード管理
- 実験ログ保存

を行う。

---

# 11. 本番導入プロセス

Researchで成功した戦略は以下の手順で本番導入する。

```
Research
↓
Backtest
↓
Forward Test
↓
Production
```

Forward Test

- ペーパー運用
- 小額運用

---

# 12. 安全対策

Research環境では以下を禁止する。

- 実取引API呼び出し
- 本番口座アクセス
- 自動発注

Researchは **完全な分析環境**とする。

---

# 13. 将来拡張

将来的には以下を検討する。

- 分散バックテスト
- GPU機械学習
- AutoML
- ハイパーパラメータ最適化

---

# 14. まとめ

Research環境は以下の役割を担う。

```
データ分析
↓
戦略開発
↓
バックテスト
↓
モデル検証
↓
本番導入
```

本環境により、安全かつ効率的な戦略開発を実現する。
