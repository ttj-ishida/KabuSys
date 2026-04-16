CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 初期リリース。
- 基本パッケージ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
- 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動ロード機構（プロジェクトルート検出は .git または pyproject.toml を参照）。
  - export 形式やクォート、インラインコメントなどを考慮した柔軟な .env パース実装。
  - OS 環境変数の保護（protected set）とオーバーライド制御。
  - 必須環境変数の検証ヘルパー _require。
  - 各種設定プロパティを提供（DBパス、Paper Trading のパス・モード、監視閾値、環境種別チェックなど）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
- 実行/起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine 起動フロー、paper_trading 環境では専用 SQLite を使用（data/paper_trading.db デフォルト）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler の組み立てと EngineConfig に基づく起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用した安全な停止処理。
    - 先頭でプロセス優先度を "high" に設定。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor を定期実行するポーリングループを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop フラグ検出でループを終了。KeyboardInterrupt による終了もハンドル。
    - 起動時にプロセス優先度を "high" に設定。
- 監視 DB 初期化フック（src/kabusys/monitoring/monitoring_db.py を参照して利用）
  - run 系スクリプト起動時に監視用テーブルが存在することを保証（冪等 init）。
- ポートフォリオ構築モジュール（src/kabusys/portfolio/*
 ）
  - portfolio_builder
    - select_candidates: スコア降順 + signal_rank による tiebreak。
    - calc_equal_weights / calc_score_weights（スコア全0 の場合は等配分にフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター別上限チェック（sell_candidates 除外、"unknown" セクターは免除）。
    - calc_regime_multiplier: レジーム ("bull"/"neutral"/"bear") に基づく資金乗数（未知レジームは警告して 1.0 にフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した発注株数算出。
    - 単元株（lot_size）丸め、最大ポジション上限、aggregate cap（available_cash）に応じたスケーリング。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積り。
    - ロギングによる価格欠損等の情報提供。
- リサーチ & ファクター計算（src/kabusys/research/*）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（200日未満は None）。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比など。
    - calc_value: raw_financials と prices_daily を組み合わせた PER/ROE 算出（target_date 以前の最新財務データを参照）。
    - DuckDB を用いた効率的な SQL 実装。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21）での将来リターン算出（入力検証・スキャン範囲の最適化あり）。
    - calc_ic, rank, factor_summary: IC（Spearman）計算、同順位処理、統計サマリー等を標準ライブラリのみで実装。
  - research パッケージのエクスポート最適化（zscore_normalize を含む）。
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores に書き込む処理を実装。
  - バッチ処理（最大 20 銘柄 / API コール）、トークン肥大化対策（記事・文字数トリム）、JSON Mode と出力バリデーション、スコアクリップ（±1.0）。
  - 429 / ネットワーク断 / 5xx に対する指数バックオフ付き再試行、部分書き込みによる既存スコア保護（DELETE→INSERT の範囲限定）。
  - ニュース収集ウィンドウ計算ユーティリティ（JST→UTC の変換を含む）。
  - 注意: ファイル末尾が途中で切れている可能性があり、一部処理が継続実装を要する（後述の Known issues を参照）。
- ユーティリティ（src/kabusys/utils/*）
  - process_priority
    - set_process_priority: Windows / POSIX を吸収して優先度設定。AccessDenied 等は警告してスキップ。
    - set_cpu_affinity: 指定コア数に固定するユーティリティ（検証・例外ハンドリングあり）。
- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用検証レポート生成スクリプト。
  - 各種閾値を定義（稼働率、注文成功率、送信率、P95 レイテンシ等）。
  - P95 計算、期間フィルタ、DB 存在チェック、テーブルがない場合のフォールバック処理。
  - CLI オプション --from/--to/--db をサポート。出力は標準出力へ整形済みレポート。

Changed
- 初期リリースにつき該当なし（New）。

Fixed
- 初期リリースにつき該当なし（New）。

Deprecated
- なし

Removed
- なし

Security
- なし

Known issues / Notes
- src/kabusys/ai/news_nlp.py の末尾が途中で切れている（score_news 内で記事取得処理の途中で終端しているように見える）。動作確認時は当該ファイルの完成状態を確認してください。
- position_sizing や apply_sector_cap の価格欠損（price が 0.0 や未取得）の場合、現在はログ出力でスキップする設計。将来的には前日終値や取得原価などのフォールバック価格導入を検討。
- .env のパースは多くのケースをカバーするが、極端に複雑なエスケープや改行を含む値は未検証のため注意。
- DuckDB / SQLite のスキーマ依存（prices_daily / raw_financials / trade_logs 等）。デプロイ前に必要テーブルが存在することを確認してください。

Acknowledgements
- 本リリースは、ローカル DB（SQLite / DuckDB）主体で研究・バックテスト・Paper Trading を分離して実行できる設計を目標としています。API キー等の機密情報は環境変数で管理してください。