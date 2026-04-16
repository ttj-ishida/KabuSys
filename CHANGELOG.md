CHANGELOG
=========

すべての変更は「Keep a Changelog」規約に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-04-16
------------------

Added
- 基本構成
  - パッケージ初期バージョンを追加（kabusys/__init__.py: __version__ = "0.1.0"）。
- 設定管理（kabusys.config）
  - Settings クラスを導入し、環境変数経由で各種設定値を取得する仕組みを実装。
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - 多数の環境変数とデフォルト値を定義:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV, LOG_LEVEL
  - 入力検証（有効な KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）と未設定時のエラーを実装。
- 実行／監視エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。設定に応じて BrokerClientFactory を用いてブローカークライアントを生成。
    - paper_trading 環境では paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
    - デフォルトでプロセス優先度を "high" に設定（utils.process_priority.set_process_priority）。
    - 停止フラグ data/stop_requested.flag の検知で安全に停止する仕組みを実装。
    - デフォルトの PID ファイル path 管理。
    - RiskManager の既定値（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定し、初期ポートフォリオ値を broker.get_available_cash() から取得。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視系は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループ終了、KeyboardInterrupt のハンドリング、DB 接続のクローズを保証。
- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を追加。Windows / POSIX 系を吸収して優先度を設定（失敗時は警告してスキップ）。
  - set_cpu_affinity(cpu_count) を追加。指定コア数へのピンニングを実施（失敗時は警告してスキップ）。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）と上位 N 選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全スコア合計が 0 の場合は警告を出して等金額配分にフォールバック。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限を適用し、上限を超えるセクターの新規候補を除外（"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックして警告）。
  - position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき銘柄ごとの発注株数を計算。
    - 単元（lot_size）で丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮。
    - cost_buffer を導入してスリッページ・手数料を保守的に見積もる。
    - aggregate cap 超過時はスケールダウンと残余キャッシュの再配分ロジックを実装。
- 研究／ファクター計算（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算（DuckDB 上で SQL により実装）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比などを計算。
    - calc_value: prices_daily と raw_financials から PER/ROE を算出（target_date 以前の最新財務データを参照）。
    - 全関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照。メモリ外部 API 非依存。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None を返す。
    - rank, factor_summary: ランク変換と基本統計量（count/mean/std/min/max/median）計算を提供。
  - research パッケージから必要関数群をエクスポート。
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いて raw_news から銘柄ごとのセンチメント（ai_score）を生成し、ai_scores テーブルへ書き込む設計を追加。
  - 特徴:
    - 収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
    - 1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ送信（最大 20 銘柄）、429/ネットワーク断/5xx に対する指数バックオフ・リトライ、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ、部分成功時に既存スコア保護（対象コードに限定した DELETE→INSERT）等の安全策を設計。
    - API キー未指定時は例外を送出する挙動を定義。
  - 注意: 実装は堅牢化を意図した設計が盛り込まれている（送信/リトライ/検証ロジック等）。ファイル末尾に処理の続きがある想定（スクリプトは長く大きな処理フローを持つ）。
- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用検証レポート生成スクリプトを追加。
  - CLI オプション: --from, --to, --db。環境変数 PAPER_TRADING_SQLITE_PATH を優先的に参照。
  - 指標と既定の合否基準を導入:
    - 稼働率 (uptime) >= 99.0%
    - 注文成功率 (fill rate) >= 90.0%
    - 送信率 (send rate) >= 95.0%
    - P95 レイテンシ <= 200 ms
  - system_status / trade_logs / risk_logs テーブルを参照して各種集計（P95 計算、NULL ハンドリング等）を行い、判定を標準出力へ表示。
- DB 初期化（monitoring）
  - init_monitoring_db を監視・実行スクリプトから呼び出し、監視用テーブルの存在を保証（冪等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの取り扱いは明示的に引数または環境変数 OPENAI_API_KEY を要求。未設定時は ValueError を発生させる安全設計を採用。

Migration / 注意事項
- 監視（run_monitoring）は設計上、常に Settings.sqlite_path（本番パス）を使用します。テスト用に監視を分離したい場合は設定を見直してください。
- Paper Trading 実行（KABUSYS_ENV=paper_trading）は PAPER_TRADING_SQLITE_PATH を使用して本番 DB とデータを完全分離します。Paper 環境を利用する場合は環境変数を設定してください。
- .env/.env.local の自動ロードはプロジェクトルートが特定できない場合はスキップされます。CI/テスト環境で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring のポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で制御できます。不正値（非整数や 0 以下）は警告後 60 秒にフォールバックします。
- ai/news_nlp の処理は OpenAI API の利用を前提とするため、API 利用時はコストやレート制限に注意してください。429 等の一時エラーに対してはリトライ処理が組み込まれていますが、適切な API キーと権限が必要です。

今後の予定（短期）
- ai/news_nlp の処理系の完全実装・単体テスト強化。
- position_sizing の lot_size を銘柄別設定に拡張（stocks マスタからの取得）。
- 価格欠損時のフォールバック（前日終値や取得原価）を apply_sector_cap / position_sizing に導入。
- DuckDB を用いた研究モジュールの最適化と単体テスト追加。

---