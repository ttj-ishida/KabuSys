# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、以下の内容は提示されたソースコードから推測して作成しています。

## [Unreleased]

### 追加予定 / 完了予定
- news_nlp モジュールの残り実装（提供されたソースは途中で切れているため、記事集約→API呼び出し→結果書き込みの最終部分が未確認）。
- テスト・ドキュメントの整備、運用時の運用手順（stop フラグ / PID 管理など）の細部検証。

---

## [0.1.0] - 2026-04-16

初回公開リリース。自動売買システム KabuSys のコア機能群を実装。

### 追加
- パッケージ情報
  - パッケージの初期バージョン定義を追加（kabusys.__version__ = "0.1.0"）。

- 環境設定 / 設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env/.env.local の読み込み順（OS 環境 > .env.local > .env）およびオーバーライド保護を実装。
  - .env 行パーサ（コメント・クォート・export 形式に対応）。
  - Settings クラスでアプリケーション設定を公開。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須取得ロジック）
    - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN などのオプション設定
    - データベースパス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - 監視・プロセス制御関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - 閾値設定: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - 環境識別: KABUSYS_ENV（development / paper_trading / live）、is_live / is_paper / is_dev
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）

- 実行・監視用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせ、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID 管理用ファイルの扱い。
    - RiskConfig による初期リスクパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、broker.get_available_cash() を初期ポートフォリオ値として使用。
    - monitoring テーブルの冪等な初期化（init_monitoring_db）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、負値等はデフォルトにフォールバックして警告を出す）。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計（monitoring データは環境に関係なく本番 DB を想定）。
    - stop フラグ検知や例外ハンドリングによりループ継続を安全に行う。

- プロセス優先度 / CPU 設定ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を実装（Windows / POSIX の差分を吸収）。
  - set_cpu_affinity(cpu_count) を実装（必要に応じてプロセスを先頭 N コアに固定）。
  - 実行権限不足や未対応プラットフォーム時は警告ログを出して安全にスキップ。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア正規化配分。全スコア 0 の場合は等分にフォールバックし警告。
  - risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算してセクター上限（max_sector_pct）を超えるセクターの新規候補を除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じて投下資金乗数を返す（デフォルトフォールバックあり）。
  - position_sizing
    - calc_position_sizes: 発注株数決定のコア機能を実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）に丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）でのスケールダウン、cost_buffer による保守的見積を実装。
    - スケールダウン時は端数の優先配分ロジックを実装（fractional remainder に基づく lot_size 単位での追加配分）。
    - TODO コメント: 将来的な銘柄別 lot_size 対応に関する注記。

- 研究・リサーチ機能（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（DuckDB SQL を利用）。
    - calc_volatility: ATR(20), ATR 比率, 20日平均売買代金, 出来高比率を計算（true_range の NULL 処理に注意）。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を算出（prices_daily と結合）。
  - feature_exploration
    - calc_forward_returns: 将来リターン（指定ホライズン）を一度のクエリで取得。
    - calc_ic / rank: スピアマン（ランク相関）ベースの IC 計算、ランク化ユーティリティ（同順位は平均ランク）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
  - research.__init__ で zscore_normalize を kabusys.data.stats から再エクスポート。

- Paper Trading 検証ツール（kabusys.tools.paper_verification_report）
  - Paper Trading の履歴 DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI ツールを実装。
  - 検証指標:
    - 稼働率（uptime_pct）閾値: 99.0%
    - 注文成功率（fill_rate）閾値: 90.0%
    - 送信率（send_rate）閾値: 95.0%
    - P95 レイテンシ閾値: 200 ms
  - system_status, trade_logs, risk_logs 等から各種集計を行い、Pass/Fail 判定ロジックを出力。
  - 日付フィルタ（--from / --to）をサポート、デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能。
  - P95 計算、Null-safe な集計、存在しないテーブルに対するフォールバック処理を実装。

- AI ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - ニュース収集ウィンドウの計算（JST 基準 → UTC への変換ロジック）。
  - OpenAI（gpt-4o-mini）を用いたバッチスコアリング設計：
    - 最大バッチサイズ: 20 銘柄
    - 1 銘柄あたりの記事数 / 文字数制限（トークン肥大化対策）
    - JSON Mode を期待し、結果の検証・スコアクリップ（±1.0）
    - 429 / ネットワーク / 5xx に対する指数バックオフリトライ
    - 部分失敗時に既存のスコアを保護するため、対象コードのみを置換する戦略（DELETE→INSERT の範囲限定）
  - 注意点: 提供されたソースは途中で切れているため、記事集約から API 呼び出し・DB 書き込みの最終部分はソースの続きに依存。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の問題 / TODO
- news_nlp モジュールのファイルが提供スニペットで途中で切れている（記事集約後の処理が完全に確認できず）。実運用前に未確認箇所の完成とレビューが必要。
- position_sizing.calc_position_sizes:
  - price が取得できない（0.0）場合にエクスポージャーが過少見積りされる懸念あり（apply_sector_cap にも同様の注記）。将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO を残している。
  - 単元株の銘柄別対応は未実装（全銘柄共通 lot_size を仮定）。銘柄別 lot_map を受け取る設計への拡張を想定。
- process_priority.set_cpu_affinity / set_process_priority:
  - プラットフォームや権限によっては AccessDenied 等でスキップする設計になっているため、運用環境での権限確認が必要。
- run_monitoring は監視 DB を環境にかかわらず本番 sqlite_path を使う設計になっているため、テスト環境で分離したい場合には注意が必要（設定で paper_trading 用 DB を使う run_execution と動作が異なる点）。
- DuckDB executemany 等の制約に注意（news_nlp 内コメント参照）。

### セキュリティ
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で明示的に渡す必要がある。未設定時は ValueError を送出して処理を停止する設計。

---

今後の予定:
- news_nlp の残実装完了と統合テスト。
- 単体テストの追加（position_sizing の多様なケース、scale-down/端数配分の検証）。
- 運用ドキュメントの充実（stop/kill フラグ、PID 管理、監視の運用手順）。
- 銘柄別 lot_size や価格フォールバック戦略の実装。