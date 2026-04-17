# Changelog

すべての変更は Keep a Changelog のルールに準拠して記載しています。  
主な機能追加・設計方針・重要な挙動はコード内のコメント・ドキュメント文字列から推測してまとめています。

## [Unreleased]

- ai/news_nlp モジュールの処理フロー実装が進行中（バッチ処理・API リトライ・レスポンス検証・DB 書き込み戦略などの設計が含まれる）。一部実装が途中でトランケートされているため、安定化・エラーハンドリングの追加が予定。
- 小さなログ出力・警告文言の改善、テスト補助のための env ロード制御（KABUSYS_DISABLE_AUTO_ENV_LOAD）周りの追加検討。

---

## [0.1.0] - 2026-04-17

### Added
- パッケージ初期リリース（__version__ = 0.1.0）。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 専用 SQLite（data/paper_trading.db）を用いる分離設計を導入。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、ExecutionEngine.run_session を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）・PID ファイル（data/execution.pid）によるプロセス制御を実装。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を組み込み、初期ポートフォリオ値を broker.get_available_cash() から取得する仕組みを導入。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）に対応。0 以下の不正値はデフォルトへフォールバック。
    - 監視は本番 sqlite_path を環境にかかわらず使用する（設計上の注意点）。
    - 停止フラグ検知でループを終了する制御を実装。

- 設定管理
  - config.py を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env → .env.local の順、OS 環境変数を保護）。
    - .env ファイルのパース機能強化（export KEY= 形式、引用符付き値内のバックスラッシュエスケープ、インラインコメントの扱い等）。
    - Settings クラスでアプリケーション設定をプロパティとして公開（DB パス、paper_trading 用パス、PAPER_FILL_MODE 検証、PID/kill flag パス、しきい値、env/log_level の検証など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止機能を追加（テスト時の互換性確保）。
- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio.portfolio_builder
    - シグナルの候補選定（スコア降順、signal_rank によるタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合は等金額へフォールバック）。
  - portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap（既存保有を加味したセクター露出算出、"unknown" セクターは除外しない挙動）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear にマップ、未知レジームは警告を出して 1.0 でフォールバック）。
  - portfolio.position_sizing
    - 各銘柄の発注株数計算 calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株(lot_size)、stop_loss、risk_pct、max_position_pct、max_utilization、cost_buffer を考慮した計算ロジック。
    - aggregate cap 超過時のスケールダウンと lot_size 単位での再配分アルゴリズム（remainder 分配）。
    - 価格欠損時のスキップ挙動、上限チェックなどの防御的実装。
- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームなプロセス優先度設定 set_process_priority（Windows, POSIX を吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity。
    - 権限不足や未対応 OS の場合は警告を出して処理をスキップする安全策を実装。
- 研究 / リサーチ
  - research.factor_research
    - DuckDB を用いたファクター計算（calc_momentum, calc_volatility, calc_value）。各ファクターは prices_daily / raw_financials テーブルに依存。
    - MA200, ATR20, リターンホライズン等をウィンドウ関数で計算し、データ不足時の None 返却を保証。
  - research.feature_exploration
    - 将来リターン計算 calc_forward_returns（任意 horizon をサポート、入力検証あり）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の rank 相関を純粋 Python で実装）。
    - ランク変換 rank、統計サマリー factor_summary を実装（外部ライブラリに依存せず）。
  - research.__init__ に主要関数をエクスポート（zscore_normalize は kabusys.data.stats から取得）。
- ツール
  - tools.paper_verification_report
    - Paper Trading 検証用レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計。
    - 基準値（稼働率≥99%、注文成功率≥90%、送信率≥95%、P95≤200ms）に基づく PASS/FAIL 判定ロジックを実装。
    - CLI オプション --from / --to / --db をサポート。DB の存在チェックや DuckDB のテーブル欠如に対する例外吸収ロジックを実装。
- AI ニュース NLP（初期実装）
  - ai.news_nlp
    - raw_news と news_symbols を用いた銘柄別ニュース集約と OpenAI API（gpt-4o-mini）へのバッチ送信設計を導入。
    - タイムウィンドウ計算（JST ベース → UTC 変換）、記事トリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)、API キー解決、クリップ、リトライ（429/5xx/ネットワーク）などの設計を記述。
    - 出力の JSON バリデーションと部分更新（該当コードのみ DELETE→INSERT）戦略を想定。
    - 実装途中でファイルがトランケートされている箇所あり（今後の完成予定）。

### Changed
- DB/監視初期化の防御的設計
  - run_execution/run_monitoring 内で init_monitoring_db を呼び出し（冪等化）して監視テーブル存在を保証するようになった。
- .env 読み込みの優先順位を明確化（OS 環境 > .env.local > .env）し、.env.local を override=True で適用する挙動に統一。
- 設定バリデーションの追加
  - Settings.paper_fill_mode の有効値検証（instant/partial/never/reject）。
  - Settings.env / log_level の許容値チェックを追加し、不正値時に明示的な ValueError を送出。

### Fixed
- ポーリング間隔の入力検証改善
  - MONITOR_POLL_INTERVAL の 0 以下や非整数入力を検知してデフォルトへフォールバックし、不正な値による time.sleep の例外発生を防止。
- calc_score_weights: 全銘柄のスコアが 0 の場合にゼロ除算・不正比率を回避して等金額配分へフォールバックするよう修正。
- calc_momentum / calc_volatility / calc_value: データ不足時の None ハンドリングと window 行数チェックを追加し、不完全データからの誤った算出を防止。
- paper_verification_report: DB テーブルが存在しない場合に sqlite3.OperationalError を捕捉して安全にレポートを生成するフォールバックを追加。

### Security
- OpenAI API キーの取り扱いに関する注意を明記（api_key 引数または環境変数 OPENAI_API_KEY を必須にし、未設定時は ValueError を発生させることで不慮のキー漏洩や未設定を検出）。

---

注記:
- 一部モジュール（monitoring.monitoring_db、monitoring.system_monitor、execution.* の内部実装や kabusys.data.stats）は本差分に含まれていませんが、各スクリプト／ライブラリはそれらの存在を前提として設計されています。
- ai.news_nlp は設計が詳細に書かれているものの、ファイル末尾が途中で切れており完全実装は未完了です。実運用前に完全実装と統合テストを推奨します。