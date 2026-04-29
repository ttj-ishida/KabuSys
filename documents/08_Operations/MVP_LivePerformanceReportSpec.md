# MVP: 運用成績サマリーレポート最小仕様

- ステータス: 設計完了（Issue #195、仕様書: `docs/superpowers/specs/2026-04-29-performance-report-design.md`）
- 目的: 最初に実装する運用成績サマリーレポートの最小仕様を 1 ページで定義する
- 対象: `production` / `paper_trading` 共通
- 出力形式: Markdown
- 集計単位: 日次 / 週次 / 月次

---

## 1. この仕様で実装するもの

最初の実装では、以下だけを対象とする。

- 日次 Markdown レポート
- 週次 Markdown レポート
- 月次 Markdown レポート

この段階では、JSON 出力、HTML 出力、Slack 通知、グラフ埋め込み、ダッシュボード統合は実装対象外とする。

---

## 2. 基本方針

- 本番口座用と `paper_trading` 用は同一の章立てと指標で共通化する
- 差分は `environment` などのメタ情報で表現する
- まずは「短時間で振り返れるサマリー」を優先し、詳細分析は後続フェーズに回す

---

## 3. 出力対象

### 日次

目的:

- 当日の損益と状態を確認する

### 週次

目的:

- 1 週間の成績推移を振り返る

### 月次

目的:

- 月単位の成績を評価する

---

## 4. 出力先

保存先は本番口座用と `paper_trading` 用で共通構造を使う。

```text
artifacts/performance/{env}/daily/{yyyy-mm-dd}/report.md
artifacts/performance/{env}/weekly/{yyyy}-W{ww}/report.md
artifacts/performance/{env}/monthly/{yyyy-mm}/report.md
```

例:

```text
artifacts/performance/live/daily/2026-04-21/report.md
artifacts/performance/paper_trading/weekly/2026-W17/report.md
```

---

## 5. 共通で必ず出す項目

日次 / 週次 / 月次のすべてで、最低限以下を表示する。

### 5.1 メタ情報

- `environment`
- レポート種別
  - `daily`
  - `weekly`
  - `monthly`
- 集計期間
- レポート生成日時

### 5.2 資産サマリ

- 期首資産
- 期末資産
- 損益額
- 損益率
- 現金残高

### 5.3 リスクサマリ

- 期間末ドローダウン
- 期間中最大ドローダウン

### 5.4 取引サマリ

- 売買件数
- BUY 件数
- SELL 件数
- 約定件数
- 期末保有銘柄数

### 5.5 warning

- warning 一覧

---

## 6. 日次レポートの最小追加項目

日次では、以下を追加する。

- 当日日次リターン
- 当日損益額
- 当日終了時点の保有銘柄一覧

この段階では、注文明細全文や全トレード一覧はレポートに含めない。

---

## 7. 週次レポートの最小追加項目

週次では、以下を追加する。

- 日別損益一覧
- 日別リターン一覧
- 勝ち日数
- 負け日数

この段階では、セクター分析やシグナル分析は含めない。

---

## 8. 月次レポートの最小追加項目

月次では、以下を追加する。

- 月間勝率
- 平均利益
- 平均損失
- 月末保有銘柄一覧

この段階では、本番 / paper の比較欄は必須にしない。  
ただし、同じ形式で出力されるため、並べて比較可能にする。

---

## 9. Markdown の最小章立て

すべてのレポートは、最低限以下の章立てを持つ。

1. Overview
2. Asset Summary
3. Risk Summary
4. Trade Summary
5. Positions
6. Warnings

### 日次で追加

- Daily Highlights

### 週次で追加

- Daily Breakdown

### 月次で追加

- Monthly Highlights

---

## 10. データソースの共通化方針

本番口座用と `paper_trading` 用で、同じレポート生成器を使う。

切り替えるのは以下のみとする。

- `--env live|paper_trading`（CLI オプション）

共通データソース（すべて同一 DuckDB）:

- `portfolio_performance`（`env` 列でフィルタ）
- `market_calendar`（JPX 営業日数の算出に使用）

`portfolio_performance` の `env` 列に書き込まれた環境名でデータを分離する。
既存レコードは `env = 'live'` としてバックフィル済み。

レポート生成ロジックは共通コードにまとめる。

---

## 11. warning の最小仕様

最初の実装では、以下だけを warning 対象とする。

### 日次

- 当日 DD が閾値超過
- 約定 0 件

### 週次

- 週間 DD が閾値超過
- 週間売買件数 0

### 月次

- 月間 DD が閾値超過
- 月間損益が大幅悪化

閾値は初期実装では固定値または暫定設定値でよい。

---

## 12. 生成タイミング

### 日次

- Market Close 後
- `portfolio_performance` の当日記録完了後

### 週次

- 金曜引け後、または週末夜間バッチ後

### 月次

- 月末最終営業日引け後、または翌月初営業日前

---

## 13. 今回は実装しないもの

以下は後続フェーズに回す。

- JSON 出力
- HTML 出力
- Slack 通知
- グラフ埋め込み
- セクター分析
- シグナル分析
- 本番 / paper 比較セクションの自動生成
- 注文明細全文
- トレード一覧全文
- 累積 Sharpe / CAGR など中長期指標

---

## 14. 実装完了の条件

以下を満たせば、この MVP は完了とする。

1. `production` / `paper_trading` の両方で同じ形式の Markdown レポートが出力される
2. 日次レポートが出力される
3. 週次レポートが出力される
4. 月次レポートが出力される
5. 資産、リスク、取引、保有、warning の最低限サマリーが確認できる
