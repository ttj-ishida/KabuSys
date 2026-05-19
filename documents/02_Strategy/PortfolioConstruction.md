
# PortfolioConstruction.md

## 1. 目的

本ドキュメントは、日本株自動売買システムにおける **ポートフォリオ構築（Portfolio Construction）** の設計仕様を定義する。

ポートフォリオ構築は、以下を決定する重要なプロセスである。

- どの銘柄を採用するか
- 各銘柄にどれだけ資金を配分するか
- セクターや市場全体のリスクをどう分散するか
- 市場環境に応じてポジションをどう調整するか

クオンツ運用では、**戦略シグナルよりもポートフォリオ構築がリターンの安定性を大きく左右する**。

---

# 2. ポートフォリオ構築の基本思想

本システムでは以下の原則を採用する。

1. **分散投資を基本とする**
2. **単一銘柄への過度な集中を避ける**
3. **セクター集中を制限する**
4. **市場レジームに応じてリスク量を調整する**
5. **AIスコアは補助要素として利用する**

---

# 3. 投資ユニバース

投資対象は以下の条件を満たす銘柄とする。

## 基本条件

- 東証プライム / スタンダード
- 最低売買代金
- 最低出来高
- 価格データが安定して取得可能

## フィルタ条件（例）

| 条件 | 値 |
|----|----|
最低売買代金 | 5億円 |
最低株価 | 300円 |
平均出来高 | 10万株以上 |

---

# 4. スコアリング

StrategyModel で生成された **最終スコア（final_score）** をポートフォリオ構築の入力とする。

例

```
final_score =
  0.40 * momentum
+ 0.20 * value
+ 0.15 * volatility
+ 0.15 * liquidity
+ 0.10 * news
```

---

# 5. 銘柄選定

スコア順にランキングを作成する。

## 手順

1. 全銘柄にスコアを計算
2. スコア降順に並べ替え
3. 上位銘柄を選択

例

| Rank | Code | Score |
|-----|------|------|
1 | 8035 | 0.92 |
2 | 1605 | 0.88 |
3 | 5401 | 0.85 |

---

# 6. ポートフォリオサイズ

最大保有銘柄数

```
5〜15銘柄
```

推奨

```
10銘柄
```

理由

- 分散効果
- 管理の容易さ
- 売買コスト抑制

---

# 7. 資金配分方法

`run_backtest` および本番執行系では `allocation_method` パラメータで切り替える。

## 7.1 リスクベースサイジング（推奨デフォルト）

StrategyModel.md Section 6 に基づく方式。ボラティリティ正規化効果があり、
高ボラ銘柄は少なく、低ボラ銘柄は多く購入する。

```
許容損失額 = 総資産 × risk_pct（デフォルト 0.005 = 0.5%）
1株リスク  = エントリー価格 × stop_loss_pct（デフォルト 0.08 = 8%）
購入株数   = floor(許容損失額 / 1株リスク)
           ← ただし「総資産 × max_position_pct（10%）」の上限を超えない
           ← 単元株（100株）単位に切り捨て
```

`run_backtest` のデフォルト: `allocation_method="risk_based"`

## 7.2 等金額配分

最もシンプルな方法。

```
weight_i = 1 / N
alloc_i  = 総資産 × weight_i × max_utilization（0.70）
```

例: 資産 1000万円、銘柄数 10 → 各銘柄 70万円

`allocation_method="equal"` で使用。

## 7.3 スコア加重配分

スコアに応じて資金配分。

```
weight_i = score_i / sum(scores)
alloc_i  = 総資産 × weight_i × max_utilization（0.70）
```

全銘柄のスコアが 0.0 の場合は等金額配分にフォールバック。

`allocation_method="score"` で使用。

## 7.4 共通制約（全方式）

| パラメータ | デフォルト | 説明 |
|------------|------------|------|
| max_position_pct | 0.10 | 1銘柄への投資上限（総資産の10%） |
| max_utilization | 0.70 | 全ポジション合計の投資上限（総資産の70%） |
| lot_size | 100 | 単元株数のデフォルト値。`lot_map` が `None` または当該銘柄の指定がない場合に適用される。 |
| lot_map | None | 銘柄別の単元株数 `{code: lot_size}`。指定した銘柄はこの値を使用し、未指定銘柄は `lot_size` にフォールバックする。`None` の場合は全銘柄に `lot_size` を適用する（Issue #291）。 |

### 銘柄別売買単位（lot_map）

東証プライム・スタンダードの銘柄は通常 100 株単位だが、一部銘柄では売買単位が異なる場合がある。`lot_map` を使用することで銘柄ごとに正しい単位で数量計算が行える。

```python
# 例: 銘柄 1234 のみ 1000 株単位、他は 100 株単位
calc_position_sizes(
    ...,
    lot_size=100,
    lot_map={"1234": 1000},
)
```

`lot_map` が渡されない場合（`None`）は従来どおり全銘柄に `lot_size` を適用する。

実装モジュール: `src/kabusys/portfolio/position_sizing.py`

---

# 8. セクター制御

## 8.1 セクター集中制限（`apply_sector_cap`）

| 制限 | 値 |
|----|----|
| 同一セクター最大 | 30% |
| 単一銘柄最大 | 10% |

セクターデータ: J-Quants `/listed/info` → `stocks` テーブル（DataSchema.md Section 4参照）。
セクター不明銘柄は制限なし（"unknown" 扱い）。

### 価格欠損・不正値の扱い

既存保有のセクター別エクスポージャーを集計する際、`price_map` に存在しない銘柄・不正値を持つ銘柄は **保守的ブロック** とする。

対象とする不正値:

| ケース | 理由 |
|--------|------|
| `price_map` にキーが存在しない | 価格未取得 |
| 値が `None` | 価格未取得 |
| 値が `0.0` または負値 | 価格として無効 |
| 値が `NaN` / `inf` / `-inf` | 数値として無効 |

不正値が検出されたセクターは `price_missing_sectors` に追加し、最終的に `blocked_sectors` へマージする（`blocked_sectors |= price_missing_sectors`）。不正値検出時は `logger.warning` で銘柄コード・不正値・セクター名を記録する。

> **設計方針**: 価格不明の既存保有を 0 円として扱うと、エクスポージャーが過少見積りされ、本来ブロックすべきセクターに新規 BUY が通過するリスクがある。保守的ブロックにより、このリスクを排除する（Issue #287）。

実装モジュール: `src/kabusys/portfolio/risk_adjustment.py`

## 8.2 セクター相対強弱フィルタ（Issue #172 実装済み）

銘柄選定段階で、弱含みセクターの銘柄を除外する。セクター集中制限（8.1）とは独立して動作する。

| ルール | 内容 |
|-------|------|
| 下位25%セクター | 新規 BUY を禁止（SELL は対象外） |
| 上位25%セクター | `final_score +0.03` のスコア補正 |
| 中立帯セクター | 補正なし |

判定基準: セクター内銘柄の20営業日リターン**等加重平均**を使用してセクターをランキング。

実装モジュール: `src/kabusys/strategy/signal_generator.py`（`generate_signals()` 内のフィルタ処理）

---

# 9. 市場レジーム制御

市場レジームに応じてリスク量を調整する。`market_regime.regime_label` の値（小文字）を参照する。

| regime_label | 投下資金乗数 | 説明 |
|-------------|------------|------|
| "bull" | 1.0（100%） | 通常運用 |
| "neutral" | 0.7（70%） | やや縮小 |
| "bear" | 0.3（30%） | 大幅縮小 |

**Bear レジームでの BUY シグナル:**
`generate_signals()` が Bear 相場では BUY シグナルを一切生成しない（StrategyModel.md Section 5.1）。
乗数 0.3 は Bear とは別に "neutral" 等の中間局面向けの追加セーフガード。

実装モジュール: `src/kabusys/portfolio/risk_adjustment.py`（`calc_regime_multiplier`）

## 9.2 TOPIX MA クロスベアガード（Issue #257 実装済み、Issue #349 で MA クロス判定に改訂）

TOPIX の MA クロス状況に応じて新規 BUY の `size_multiplier` を縮小する。判定は MA25/MA75/MA200 の位置関係で 3 段階に行い、強ベア判定（MA75 < MA200）が弱ベア（MA25 < MA75）に常に優先する。MA 列は `feature_engineering.py::update_topix_ma()` で事前計算し `topix_daily` に保存する。

| 条件 | `topix_multiplier` | 設定キー | 説明 |
|------|--------------------|---------|------|
| MA75 < MA200 | 0.0（デフォルト） | `topix_size_multiplier_strong_bear` | 強ベア：新規 BUY 完全停止 |
| MA25 < MA75（かつ MA75 ≥ MA200） | 0.5（デフォルト） | `topix_size_multiplier_weak_bear` | 弱ベア：サイズ半減 |
| それ以外 | 1.0 | — | ブル：通常サイズ |

- `strong_bear ≤ weak_bear` を強制（逆転時は ValueError）
- AI レジーム乗数・breadth_stop とは独立して動作し、最も小さい `size_multiplier` が採用される
- MA 計算に必要な件数不足時（初期運用開始直後など）は 1.0 を返して無効化する
- CLI オプション `--topix-size-multiplier-weak-bear` / `--topix-size-multiplier-strong-bear` でオーバーライド可能
- 実装: `src/kabusys/strategy/signal_generator.py::_get_topix_size_multiplier()`

---

# 10. AIスコアの利用

AIスコアは以下に利用する。

- 銘柄ランキング補正
- セクター補正
- 市場リスク検知

例

```
adjusted_score =
  base_score * (1 + news_score * 0.1)
```

---

# 11. リバランス

本システムは **日次シグナル生成・翌営業日寄付き執行** のスイング戦略である。リバランスは固定周期ではなく、毎営業日夜間バッチで `generate_signals()` が実行され、スコア変化に応じてポジションが動的に入れ替わる。

## リバランス方針

| 項目 | 内容 |
|-----|-----|
| シグナル生成頻度 | 毎営業日（夜間バッチ） |
| 執行タイミング | 翌営業日の寄付き |
| 想定保有期間 | 数営業日〜数週間（最大 60 営業日） |
| 最低保有日数 | 5営業日（ストップロス・決算回避を除く） |
| 再エントリー制限 | SELL 後 5営業日は同一銘柄の再 BUY を禁止 |

## イベント前のサイズ縮小

翌営業日が FOMC・日銀決定会合・米CPI 等の主要イベント日の場合、新規 BUY の発注サイズを 50% に縮小する（`signals.size_multiplier=0.5`）。`execution_engine` および `simulator` は `size_multiplier` を参照して株数を計算する。

---

# 12. 売却ルール

以下の条件で売却。

- スコアランキング外
- 損切り条件
- 利確条件
- 市場レジーム変化

---

# 13. 取引コスト考慮

売買時には以下を考慮する。

- 手数料
- スリッページ
- 税金

バックテストでは必ず反映する。

---

# 14. ポートフォリオ監視

監視項目

- 総資産
- 銘柄数
- セクター配分
- ドローダウン

---

# 15. 将来拡張

将来的には以下の高度化を検討する。

- Mean-Variance Optimization
- Risk Parity
- Black-Litterman
- マルチ戦略ポートフォリオ

---

# 16. まとめ

ポートフォリオ構築は以下のプロセスで行う。

```
generate_signals() → signals テーブル
      ↓
select_candidates()        # 銘柄選定（上位 max_positions 銘柄）
      ↓
apply_sector_cap()         # セクター集中チェック
      ↓
calc_*_weights()           # 配分重み計算（allocation_method に応じて選択）
      ↓
calc_position_sizes()      # 株数決定（リスク制限・単元株丸め）
      ↓
apply_regime_multiplier()  # レジーム乗数適用
      ↓
{code: shares} → 発注
```

実装: `src/kabusys/portfolio/`（portfolio_builder.py / position_sizing.py / risk_adjustment.py）

この仕組みにより、分散された安定的なポートフォリオを構築し、
戦略のパフォーマンスを最大化する。
