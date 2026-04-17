# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルではコードベースから推測できる追加・改善点・修正点を日本語でまとめています。

## [Unreleased]

### Added
- ニュースNLPモジュールの追加（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング機能を実装するための基盤を追加。
  - タイムウィンドウ算出（calc_news_window）、APIキー解決、バッチ処理／リトライ／クリッピング等の設計を導入。
  - バッチサイズ、最大記事数・文字数、スコア範囲等の定数化によりトークン暴走対策や堅牢化を考慮。
  - （注）score_news の続き処理はコード断片のため本リリースでは部分実装または補完が必要。

### Changed
- run_monitoring のポーリング制御の柔軟化
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能に（デフォルト 60 秒）。
  - ポーリング間隔の不正値はログ警告を出してデフォルトにフォールバックするように改善。
  - 監視ループは data/stop_requested.flag による外部停止を検知して正常終了する仕様。
  - 監視（Monitoring）は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用することを明示（挙動の重要な注意点）。

### Fixed
- 環境変数読み込みの堅牢化（kabusys.config）
  - .env ファイルの自動ロードで export 付きの行、クォート付き値、インラインコメント等に対応するパーサを導入。
  - .env の読み込み順序と上書きロジック（OS 環境変数 > .env.local > .env）を明確化し、既存 OS 環境変数を保護する protected 機構を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能に。

### Security
- 環境変数の取り扱いを改善し、OS 環境変数の上書きを防ぐ仕組み（protected set）を導入。

---

## [0.1.0] - 2026-04-17

### Added
- 全体構成: 初期モジュール群を追加（バージョンを package に定義: __version__ = "0.1.0"）。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用して環境に応じたブローカークライアントを生成。
    - ExecutionEngine の構築に必要な OrderRepository、OrderManager、RiskManager、Reconciler を組み立てる処理を追加。
    - スレッドで engine.run_session を実行し、data/stop_requested.flag を監視して停止命令を反映。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - init_monitoring_db を呼び出して監視用テーブルを確保。
    - duckdb への接続も併用。
    - 停止フラグや KeyboardInterrupt による安全な終了処理を実装。
- 設定管理（kabusys.config）
  - .env 自動読み込み、export対応、クォート処理、protected 上書き禁止等を備えた堅牢な環境変数ローダを実装。
  - Settings クラスを導入し、アプリケーションで使う設定（DB パス、API トークン、監視閾値、環境種別など）をプロパティとして提供。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を追加（不正値時は明確な ValueError）。
  - paper_fill_mode、paper_sqlite_path、pid_file_path、kill_flag_path、各種閾値などの設定プロパティを追加。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: 銘柄選定（select_candidates）や配分重み（calc_equal_weights, calc_score_weights）を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
    - sell_codes を除外してセクターエクスポージャーを計算する機能を提供。
    - 未知セクター（"unknown"）は上限チェック対象外とする仕様を明記。
  - position_sizing: allocation_method（risk_based/equal/score）に応じた株数決定ロジックを実装。lot_size（単元）対応、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリングロジックを搭載。
- ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) により Windows / POSIX を吸収してプロセス優先度を設定するユーティリティを追加。
  - set_cpu_affinity(cpu_count) によりプロセスを先頭 N コアにピン留めする機能を追加。
  - 権限不足や未対応 OS の場合は例外を投げずログ警告でスキップする堅牢化。
- リサーチ（kabusys.research）
  - factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算関数（calc_momentum, calc_volatility, calc_value）を追加。DuckDB の prices_daily / raw_financials を参照して SQL ベースで計算。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付け（rank）を追加。外部ライブラリに依存せず標準ライブラリのみで実装。
- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 検証レポート生成スクリプトを追加。
  - system_status, trade_logs, risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ等をレポート出力。
  - P95 計算、閾値による PASS/FAIL 判定、DB 存在チェック、OperationalError のフォールバック処理等を実装。
- DB 初期化補助（監視用）
  - init_monitoring_db(sqlite_conn) を起動フローに組み込み、監視用テーブルの存在を冪等的に保証。

### Changed / Improvements
- ExecutionEngine / Monitoring 起動時に最初にプロセス優先度を "high" に設定するようにし、重要処理の実行優先度を向上。
- paper_trading 環境の DB を明確に分離し、本番データと競合しないように設計。
- position_sizing の aggregate スケーリングで lot_size 単位での丸めと残余の公平配分（fractional remainder handling）を導入し、実運用での単元制約を考慮。
- risk_adjustment の apply_sector_cap が sell_codes を考慮することで当日売却予定銘柄のエクスポージャー計算から除外可能に。
- research モジュールで SQL スキャン範囲にバッファを設け、週末祝日等の営業日ギャップを吸収する実装に改善。
- utils/process_priority: 対応 OS と未対応 OS の判定を明確化し、例外発生時に警告ログで処理継続するように変更。

### Fixed
- MONITOR_POLL_INTERVAL の不正値（0 / 負数 / 非整数）に対する安全ガードを追加し、問題時は警告ログとデフォルト値の使用でループ継続するように修正。
- .env 読み込み時の I/O エラーに対して warnings.warn を利用してフォールバックするように変更（プロセス停止を回避）。

### Documentation / Comments
- 各モジュールに設計方針や参照ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への言及を追加して、関数の前提や注意点を明記。
- 多くの関数に docstring を充実させ、引数・戻り値・返される型・例外について明記。

### Breaking Changes
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず production 的 sqlite_path（settings.sqlite_path）を使用する仕様になっている点に注意。paper_trading の監視用DB分離を期待する運用者は挙動の差異に注意すること。

---

メモ:
- ai/news_nlp モジュールは API 呼び出しのフローや DB への書き込み戦略（部分更新での保護等）など堅牢な設計が示されていますが、提供されたコードは途中で切れているため実働化のためには残り処理の補完が必要です。
- 上記はソースコードの内容から推測した変更点・設計意図の要約です。実際のコミット履歴や機能追加順序はリポジトリの履歴を参照してください。