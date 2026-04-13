CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
この CHANGELOG は、与えられたコードベースの内容から推測して作成したものであり、実際の開発履歴とは差異がある可能性があります。

Unreleased
----------

Added
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する旨を明示。
  - 起動時にプロセス優先度を "high" に設定する処理を実行。
  - monitoring DB 初期化（init_monitoring_db）を行い、duckdb も接続して監視インスタンスを生成・運用。

- run_execution.py: 実際の ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合は Paper Trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH／data/paper_trading.db）を使用して本番 DB と分離。
  - 起動時にプロセス優先度を "high" に設定。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager 組み立て、ExecutionEngine の run_session 呼び出しを実装。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を初期化し、初期ポートフォリオ値を broker.get_available_cash() から取得して設定。

- config.py: 環境変数/.env 読み込みと設定管理を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード（.env → .env.local、OS 環境変数優先）。
  - .env パーサで以下に対応:
    - export KEY=val 形式
    - シングル／ダブルクォート内のバックスラッシュエスケープ
    - クォートなしでのインラインコメント取り扱い（'#' の直前が空白/タブのとき）
  - 設定ラッパー Settings を提供し、各種プロパティ（DB パス、PID ファイル、kill flag、閾値、env/log_level 検証、paper trading 関連など）を型付きで取得可能に。
  - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
  - KABUSYS_ENV の検証（development|paper_trading|live）、LOG_LEVEL の検証。

- utils/process_priority.py:
  - クロスプラットフォームなプロセス優先度設定ユーティリティを追加。
  - Windows（psutil の優先度定数）、POSIX（nice 値）を吸収して set_process_priority(level) を提供。
  - CPU affinity を固定する set_cpu_affinity(cpu_count) も実装（権限や未対応環境では警告ログを出して無害にスキップ）。

- portfolio/*:
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全てが0の際は等金額にフォールバックして警告。
  - risk_adjustment: セクター集中制限を適用する apply_sector_cap、相場レジームに基づく投下資金乗数 calc_regime_multiplier を実装。
  - position_sizing: 各銘柄の発注株数を計算する calc_position_sizes を実装（risk_based / equal / score の配分方式、lot_size 単位丸め、aggregate cap スケーリング、cost_buffer の考慮など）。
  - portfolio パッケージのエクスポートを整備。

- research/*:
  - factor_research: DuckDB を使ったファクター計算（calc_momentum, calc_volatility, calc_value）を実装。
    - モメンタム（1M/3M/6M、MA200乖離）、ATR/相対ATR、20日平均売買代金・出来高比率、raw_financials に基づく PER/ROE 等。
    - 欠損データに対する慎重な取り扱い（必要な窓幅未満で None を返す等）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）・ランク関数（rank）、ファクター統計サマリ（factor_summary）を実装。
    - 外部ライブラリ非依存（標準ライブラリのみ）で実装。
  - research パッケージのエクスポート整備（zscore_normalize を kabusys.data.stats から再エクスポート）。

- ai/news_nlp.py:
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し ai_scores に書き込む機能を追加。
  - バッチ処理（最大 20 銘柄/コール）、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
  - OpenAI クライアント利用、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコア ±1.0 のクリップ、安全な書込み（affected codes に限定した DELETE → INSERT）などの堅牢化。
  - ニュース収集ウィンドウ計算（JST ベースで前日 15:00 ～ 当日 08:30 を UTC に変換）ユーティリティを提供。
  - API キー未設定時には ValueError を投げる明示的な挙動。

- tools/paper_verification_report.py:
  - Paper Trading 検証レポート生成 CLI を追加。
  - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。
  - データが欠けている場合のフォールバック/メッセージ出力を用意。
  - 日付フィルタ (--from / --to) や --db オプションでの DB 指定をサポート。

Changed
- monitoring DB 初期化（init_monitoring_db）を実行して、監視テーブルが存在することを保証（冪等）。
- ExecutionEngine 起動フローを整理し、paper_trading 環境では DB 分離と MockBroker の使用を明文化。
- 環境変数自動ロードの優先順位を OS 環境 > .env.local > .env に明確化、かつ既存 OS 環境を保護する実装に。

Fixed
- .env のパースに関する複数ケース（export プレフィックス、クォート内のバックスラッシュ、インラインコメント）に対応して誤読を低減。
- calc_score_weights: 全スコアが 0 の場合の除算エラー/不正な重み化を防止して等金額配分にフォールバックするように修正。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得し、未指定時は明示エラーを出すことで不正な呼び出しを防止。

0.1.0 - 2026-04-13
------------------

This release aggregates the initial feature set inferred from the code base.

Added
- 初期リリース相当の主要機能を追加:
  - 自動売買エンジン起動スクリプト（run_execution.py）、監視ループ起動スクリプト（run_monitoring.py）。
  - 環境設定管理と .env 自動ロード（config.Settings）。
  - プロセス優先度・CPU affinity 設定ユーティリティ（utils.process_priority）。
  - ポートフォリオ構築ライブラリ（portfolio）: 候補選定、重み計算、単元丸め、リスク調整、レジーム乗数。
  - 銘柄サイズ計算（position_sizing）: リスクベース / 等配分の実装、aggregate cap スケーリング。
  - DuckDB を用いたリサーチ機能（research）: ファクター計算（momentum/volatility/value）、将来リターン、IC、統計要約。
  - ニュース NLP モジュール（ai.news_nlp）: OpenAI を用いた銘柄別センチメントスコアリング（バッチ・リトライ・検証・書込保護）。
  - Paper Trading 検証ツール（tools.paper_verification_report）: CSV/DB 集計による PASS/FAIL レポート出力。
  - パッケージ初期化と __version__ = "0.1.0"。

Changed
- 各コンポーネントは DuckDB/SQLite を用途に応じて使い分け（リサーチは DuckDB、監視・paper_trading は SQLite）する設計を採用。
- paper_trading 環境用にデータ隔離（PAPER_TRADING_SQLITE_PATH）を確保。

Notes / Known limitations (推測)
- process_priority や CPU affinity は権限不足や未対応プラットフォームでは警告ログを出してスキップするため、環境によっては効果が限定される可能性がある。
- position_sizing の price 欠損時のフォールバック（コメント内 TODO）は未実装であり、価格欠損があるとエクスポージャー判断が過少評価されるリスクがある。
- ai/news_nlp の実行は OpenAI API 利用料およびレスポンス可用性に依存するため、運用時はコストとレート制限に留意すること。

脚注
- 本 CHANGELOG はコードの内容を解析して記載した「推測による変更履歴」です。実際のコミット履歴やリリースノートがある場合はそちらを正としてください。