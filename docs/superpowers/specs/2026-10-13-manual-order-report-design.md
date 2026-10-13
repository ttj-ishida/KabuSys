# 手動注文候補レポート（前日夜・当日朝）設計

- Issue: #412
- ブランチ: `feature/issue-412-manual-order-report`
- 関連: #410（手動注文メイン運用・助言モード）、`docs/superpowers/specs/2026-09-17-manual-order-main-operation-design.md` §3

ユーザーから「自動で進められる部分は自動で進める」と指示されている。以下の判断はユーザー確認を経ずに決めたもので、PR で確認してもらう。

## 1. 目的

ユーザーが証券画面で手動注文するための判断材料を、前日夜と当日朝の 2 回、ファイルとして出力する。当日朝は LINE でも通知する。KabuSys は発注しない。kabuステーション API と Execution Engine には依存しない。

## 2. 決定事項

### 2.1 構成

- 新規モジュール `src/kabusys/operations/manual_order_report.py`
  - データ収集 `collect_manual_order_report(...)`：DuckDB を読み取り専用で参照する。
  - データクラス `ManualOrderReport`
  - フォーマッタ（Markdown・JSON・CLI サマリー）と、保存関数 `save_manual_order_report`
- 新規スクリプト `scripts/run_manual_order_report.py --phase {evening,morning} [--date YYYY-MM-DD]`。既存の `run_pre_market_report.py` と同じ流れ（process_registry 登録・ログ・job 結果記録・LINE）に従う。
- 既存の `pre_market_report` は統合せず、そのまま残す。`pre_market_report` は「自動執行の起動可否」を判定するものであり、手動運用の注文候補とは目的が異なるため。手動運用中は `pre_market_report` が BLOCKED を返すことが WebManual にすでに記載されているので、新レポートとの関係を WebManual に追記する。

### 2.2 対象シグナル日

- `signal_date` は、`signal_queue` と `signals` のうち、日付が `report_date` 以下で最新のものとする。
  - 前日夜（evening）：`report_date` は当日。通常は同じ日の夜間バッチの結果になる。
  - 当日朝（morning）：`report_date` は当日。通常は前営業日の夜間バッチの結果になる。
- morning で `signal_date` が「`report_date` の前営業日」より古い場合は、夜間バッチが欠落している可能性がある。警告を出し、BUY 候補はすべて見送り扱いにする。営業日判定には既存の `market_calendar` ヘルパーを使い、カレンダーがない場合は土日だけを除外する。

### 2.3 BUY 候補

- 対象は `signal_queue` のうち、`date = signal_date`、`side = 'buy'`、`status = 'pending'` の行。
- 各行に付ける情報：
  - 銘柄名（`stocks`、なければコード）
  - 推奨株数（`size`）
  - 参考価格（`signal_queue.price`。なければ `signal_date` 以前の最新終値）
  - 想定金額（株数 × 参考価格）
  - スコア・順位（`signals`）
  - 現在保有株数（手動保有＋自動保有の `positions`）
  - 買い増しかどうか（保有株数が 0 より大きい場合）
- 買い増しの場合は「保有 X 株 → 目標 X+N 株（差分 N 株を買う）」と表記する。

### 2.4 SELL 候補

- 対象は `signals` のうち、`date = signal_date`、`side = 'sell'` の行。
- `manual_action_queue` があれば、株数・理由・`[手動保有]` を付ける（#410 と同じ JOIN。テーブルがない場合のフォールバックも同じ）。自動分の株数は `positions` の最新値から取る。
- 理由ラベルは `line_reports._SELL_REASON_LABELS` と同じ表記にする。共通化のため、公開定数 `SELL_REASON_LABELS` に改名し、既存の参照先（line_reports・12_Manual_Trades ページ）も揃える。

### 2.5 上限・資金

- `MANUAL_TRADING_ENABLED=true` の場合は `calc_manual_portfolio_value` で総資産・利用可能現金を出す。それ以外の場合は `settings.portfolio_value` を総資産とし、利用可能現金は不明として扱う。
- 1 銘柄上限は、`calc_position_sizes` の既定値（総資産の 10%）を金額で表示する。
- 想定投下額（BUY 候補の想定金額の合計）と、総資産に対する利用率を表示する。

### 2.6 見送り条件・当日朝チェック

- 共通：ギャップ見送りルールを表示する。閾値は `config/strategy_config.yaml` の `gap_up_threshold` / `gap_down_threshold` を既存の strategy config ローダーで読み込む。表示文は「寄り付きが前日終値比 +5% 超 / −3% 以下なら見送り」。寄り前の気配は取得できないため、ギャップ率は計算しない。代わりに、各 BUY 候補の見送り上限価格・下限価格（参考価格 × (1+閾値)）を表示する。
- morning のみ、次をチェックする。
  - データ鮮度：`pre_market_collector.check_data_freshness` を再利用する。
  - 停止フラグ：`data/stop_requested.flag`。`check_stop_flag` を再利用する。
  - DD 停止：SQLite の監視ダッシュボードに `dd_stop_blocked_since` があるかどうか。SQLite を読めない場合は「不明」とする。
- 停止フラグまたは DD 停止があるとき、およびシグナルが古いときは、BUY 候補をすべて「見送り候補」に移し、理由を書く。SELL 候補は常に表示する。
- morning の出力は「今日注文すべき候補（BUY・SELL）」と「見送り候補（理由付き）」に分ける。

### 2.7 出力

- `artifacts/manual_orders/{report_date}/{phase}.md` と `{phase}.json`、および CLI サマリー（標準出力）。
- LINE：morning のみ送信する（evening は既存の portfolio_construction の夜 LINE に BUY/SELL 詳細が出るため）。内容は、ステータス（OK／警告あり／BUY 見送り）、BUY 件数と上位 10 件（コード・銘柄名・株数・想定金額・買い増し表示）、SELL 件数と一覧（株数・理由・手動保有表示）、警告。送信の失敗は握りつぶす（既存方針）。

### 2.8 スケジュール

- `scripts/run_scheduler.py`
  - evening：`JobSpec("manual_order_report_evening", "run_manual_order_report.py", ["--phase", "evening"], 21, 10, True)`
  - morning：`JobSpec("manual_order_report_morning", "run_manual_order_report.py", ["--phase", "morning"], 8, 5, False)`
- `scripts/setup_task_scheduler.ps1` にも同じ 2 タスクを登録する（既存の書式に合わせ、21:10 と 08:05）。
- `documents/10_Runtime/RuntimeJobSchedule.md` と `documents/WebManual/C_ManualOrderOperation.md` を更新する。

## 3. エラー処理

- 必要なテーブル（`signal_queue`、`signals`、`stocks`、`positions`、`manual_action_queue`、`prices_daily`）がない場合は、それぞれ空として扱い、警告を出す（読み取り専用の DuckDB では CatalogException になる）。
- シグナルが 1 件もない場合も、「候補なし」のレポートを出力する。
- 例外が出た場合はジョブ失敗（exit 1）とする。LINE 送信の失敗は無視する。

## 4. テスト

- evening：BUY 候補（銘柄名・株数・想定金額・買い増し判定）、SELL 候補（手動分の理由・株数、自動分）、上限・利用率。
- morning：前営業日のシグナルを拾う。シグナルが古い場合の警告と BUY 全件見送り。停止フラグありで BUY 全件見送り。
- テーブル欠落（読み取り専用ファイル DB）でも落ちない。
- Markdown・JSON・LINE メッセージのフォーマット。
- 保存先のパスとファイル名。
- `SELL_REASON_LABELS` の改名後も、既存の LINE・ダッシュボードのテストが通る。
- スケジューラの JobSpec に 2 ジョブが含まれる（既存のスケジューラテストがあれば、その書式に合わせる）。

## 5. 対象外

- 寄り前の気配値の取得とギャップ率の計算（データソースがない）
- Streamlit への表示（今回はファイルと LINE のみ）
- 発注・承認フロー
