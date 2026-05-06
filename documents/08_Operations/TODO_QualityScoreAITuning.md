# TODO: `quality_score` の AI 対話チューニング対応

> **ステータス（2026-05-06時点）**: 未実装  
> - `quality_score` 特徴量・スコア計算: 未実装 → Issue 登録予定  
> - AI 提案 JSON の受け取り・バリデーション: 未実装  
> - Streamlit AI ウィザード連携: Issue #233（OPEN）に依存  

## 背景

Issue [#233](https://github.com/ttj-ishida/KabuSys/issues/233) では、Streamlit 上の AI 対話ウィザードで戦略・リスクパラメータを調整する構想がある。

今後 `quality_score` を導入する場合、単に固定ロジックを実装するだけでなく、**J-Quants から取得した財務品質データをもとに、AI との対話で quality_score の構成や重みを調整できるようにしたい**。

ただし、AI に毎日自由記述で個別銘柄の `quality_score` を決めさせるのは避ける。
KabuSys では以下を守る。

- 再現性
- 監査可能性
- バックテスト可能性
- 本番運用での説明可能性

そのため、AI の役割は **`quality_score` の設計案・重み案・閾値案を提案すること** に限定し、最終的な日次スコア計算自体は決定論的ロジックで実行する。

---

## 目標

AI 対話ウィザード上で、以下のループを回せるようにする。

1. 最新のバックテスト結果と品質指標分布を AI に渡す
2. AI が `quality_score` の構成案を提案する
3. 提案内容を構造化設定として保存する
4. その設定でバックテストを再実行する
5. 結果を AI とユーザーが比較し、採否を決める

---

## 非目標

以下は今回の対象外とする。

- AI が毎日個別銘柄ごとに自由文で `quality_score` を直接出力する
- AI の提案を無条件で本番戦略へ反映する
- バックテストを経ずに `quality_score` 設定を live に自動反映する

---

## 前提となる考え方

`quality_score` は以下の 2 層に分ける。

### 1. 品質特徴量層

J-Quants から取得した財務データから、決定論的に特徴量を作る。

例:

- 営業CF
- フリーCF
- 自己資本比率
- 営業利益率
- 売上成長率
- 利益成長率
- ROE
- BPS 成長率

### 2. スコア合成層

特徴量をどのような重み・正規化・閾値で `quality_score` にまとめるかを定義する。

AI が調整対象とするのは主にこちら。

---

## AI に任せる対象

- `quality_score` に採用する指標の選定
- 各指標の重み案
- 正規化方法の提案
- 外れ値クリップ方針
- 低品質銘柄を除外する閾値案
- quality と value のバランス案
- 相場局面ごとの quality 重視度変更案

---

## AI に任せない対象

- J-Quants 生データの直接解釈を毎回その場で変えること
- 個別銘柄の裁量採点
- バックテスト結果を見ずに本番へ即時反映すること
- 不明確な自由文だけで設定を保存すること

---

## 必要な追加コンポーネント

### A. Quality 特徴量の構造化

- [ ] `quality_score` 候補となる財務指標一覧を確定する
- [ ] `raw_financials` / `fundamentals` のスキーマ拡張案を作る
- [ ] 品質特徴量を `features` に格納するか、別テーブルに持つか決める
- [ ] `quality_features` または `feature_quality_snapshot` のような保持先を設計する

### B. Quality Score 設定の外部化

- [ ] `quality_score` の構成をコード内ハードコードではなく設定として外出しする
- [ ] 保存先を `config/strategy.toml` / `strategy_config.yaml` / DB テーブルのどれにするか決める
- [ ] 1 つの quality 設定プロファイルをバージョン管理できるようにする

### C. AI 提案の構造化

- [ ] AI の出力を自由文ではなく JSON で受ける
- [ ] 例: `quality_profile` のスキーマを定義する
- [ ] 指標名・重み・正規化・閾値・提案理由を分けて保存する
- [ ] 不正値や未知キーを reject するバリデーションを実装する

### D. バックテスト連携

- [ ] AI 提案した `quality_profile` を指定してバックテストを回せるようにする
- [ ] `backtest_runs` にどの `quality_profile` を使ったか記録する
- [ ] quality 有無・weight 差分ごとの比較結果を保存する

### E. Streamlit UI

- [ ] AI ウィザードから `quality_score` のチューニングモードを選べるようにする
- [ ] 現在の quality 設定を UI で確認できるようにする
- [ ] AI 提案を承認 / 却下 / 再提案できる UI を作る
- [ ] 提案前後のバックテスト KPI 差分を表で表示する

---

## `quality_profile` の候補スキーマ

AI 提案は最低限、以下の構造を持つべき。

```json
{
  "profile_name": "quality_v1",
  "factors": [
    {"name": "roe", "weight": 0.20, "transform": "higher_better"},
    {"name": "equity_ratio", "weight": 0.20, "transform": "higher_better"},
    {"name": "operating_margin", "weight": 0.15, "transform": "higher_better"},
    {"name": "sales_growth", "weight": 0.15, "transform": "higher_better"},
    {"name": "profit_growth", "weight": 0.15, "transform": "higher_better"},
    {"name": "free_cf_margin", "weight": 0.15, "transform": "higher_better"}
  ],
  "normalization": {
    "method": "cross_sectional_rank",
    "winsorize_pct": 0.02
  },
  "gates": {
    "min_equity_ratio": 0.20,
    "min_roe": 0.05
  },
  "notes": "低レバレッジ・高収益性を重視"
}
```

---

## バックテストで見るべき指標

AI に単に CAGR を最大化させるのでは不十分。
`quality_score` チューニング時は以下を比較対象に含める。

- CAGR
- Max Drawdown
- Sharpe
- Sortino
- 勝率
- 平均保有日数
- turnover
- sector 偏り
- regime 別成績
- stop_loss / trailing_stop / time_exit の発動内訳

---

## AI へのコンテキスト注入候補

AI に渡すべき情報は以下。

- 直近バックテスト結果
- 現在の `quality_profile`
- quality 特徴量の欠損率
- quality 特徴量の分布サマリ
- 上位採用銘柄の共通特徴
- 大きく負けた銘柄の共通特徴
- Bear / Bull 別の成績差

---

## 採用フロー

`quality_score` の AI 提案は以下のフローを通す。

1. AI が構造化提案を出す
2. バリデーションで形式チェックする
3. 仮プロファイルとして保存する
4. バックテストを自動実行する
5. 現行プロファイルとの差分を表示する
6. ユーザーが採用 / 却下を決める
7. 採用時のみ active profile を更新する

---

## 安全策

- [ ] AI 提案の重み合計が 1.0 でなければ自動補正または reject する
- [ ] 未知の特徴量名は reject する
- [ ] Gate 条件が過剰に厳しい場合は warning を出す
- [ ] バックテスト未実行の profile は本番で使えないようにする
- [ ] `paper_trading` 通過前に `live` へ反映できないようにする

---

## 実装順

1. `quality_score` 候補特徴量の定義
2. `quality_profile` の設定スキーマ設計
3. 決定論的 `quality_score` 計算ロジックの実装
4. バックテストで `quality_profile` を切替可能にする
5. AI ウィザードで提案 JSON を生成する
6. Streamlit 上で承認 / 比較 / 再実行ループを作る

---

## この機能で期待すること

- `quality_score` を属人的な思いつきではなく、対話と検証のループで改善できる
- AI の提案を監査可能な設定に落とし込める
- KabuSys のスコア判定を、価格系 + 簡易 value から、品質を含む多面的評価へ進化させられる
- Streamlit 上で「提案 → 検証 → 採否」のワークフローを閉じられる
