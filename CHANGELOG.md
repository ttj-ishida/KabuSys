# Changelog

すべての notable な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
このプロジェクトのバージョンは src/kabusys/__init__.py の __version__ に従います。

なお、以下の変更点はソースコードの内容から推測して記載しています。

## [Unreleased]
- （なし）

## [0.1.0] - 初回リリース
リリース日: 不明（ソースベースから推測）

### Added
- 基本アーキテクチャ
  - KabuSys パッケージの初期実装を追加。
  - モジュール構成: execution, monitoring, portfolio, utils, research, tools, config 関連の CLI/ユーティリティを追加。

- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV によって paper_trading 時は専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用する仕組みを追加。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を実装。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う制御を追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
    - 停止フラグ検知および例外ログと安全な DB クローズ処理を実装。

- 設定管理・セットアップ
  - config.py: 環境変数/.env の取り扱いを実装。
    - プロジェクトルート自動検出（.git / pyproject.toml 基準）。
    - 自動 .env ロード（.env → .env.local、OS 環境変数を保護する仕組み）。
    - .env のパース強化（export 形式、クォートされた値のバックスラッシュエスケープ、インラインコメント処理）。
    - 各種設定プロパティ（DB パス、PAPER_FILL_MODE、閾値、PID/kill flag パス、環境判定メソッド等）を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止機能を追加。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 各設定項目の対話的入力、既存 .env の読み込み、シークレットのマスク表示、保存機能を提供。
    - 保存時のテンプレート出力（.env に書き込む形式）を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向け追加ガードを実装。
    - --strict オプションで警告も FAIL 扱いに可能。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的ロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30 日保持）をルートロガーに設定。
    - LOG_DIR / app_name / LOG_LEVEL の解決順を実装。ファイル出力失敗時はコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity のユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）差分を吸収して優先度設定を行う。
    - set_cpu_affinity() によるコアピン留め機能を提供（権限や未対応プラットフォームでは警告を出してスキップ）。
    - 失敗時の AccessDenied 等を考慮して安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定および重み計算（等配分 / スコア加重）。
    - select_candidates: スコア降順で上位 N を選択、同点時の tie-break を実装。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合のフォールバック警告を実装。
  - portfolio/risk_adjustment.py: セクターキャップ・レジーム乗数の実装。
    - apply_sector_cap: 既存保有を考慮したセクター集中除外ロジック、"unknown" セクターの扱いを明示。
    - calc_regime_multiplier: bull/neutral/bear に基づく乗数（不明レジームは警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）による安全側見積り、スケーリングと端数配分アルゴリズムを実装。

- 監視・検証ツール
  - monitoring: SystemMonitor 関連（run_monitoring から利用） — monitoring_db の初期化呼び出しを組み込む（冪等）。
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime_pct）, 注文成功率（fill_rate）, 送信率（send_rate）, レイテンシ（avg/max/P95）など。
    - Pass/Fail 基準値を定義（デフォルト: uptime >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200 ms）。
    - 日付範囲指定（--from / --to）や DB パス指定（--db / 環境変数）をサポート。
    - P95 計算、SQL クエリの安全なフォールバック（テーブル未存在や OperationalError をハンドリング）を実装。

- research/factor_research.py
  - DuckDB ベースのファクター計算モジュールの骨格を追加（Momentum, Value, Volatility, Liquidity の計算を想定）。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計方針を明記。実装は途中（ファイル末尾が切れているため未完の関数あり）。

### Changed
- ログ出力の扱い
  - StreamHandler を stdout へ出力するように統一。cron/Task Scheduler との併用を意識した設計。
  - ログハンドラが既に存在する場合は一度 flush/close してから再設定し、二重出力を防止。

- DB パスの挙動
  - run_monitoring は環境にかかわらず production sqlite_path を使用する明示的な方針を採用（監視が本番 DB を参照する設計）。
  - run_execution は paper_trading の場合に専用 DB を使用して本番 DB とデータを分離。

### Fixed / Robustness
- .env のパースや読み込みの堅牢化
  - export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮して .env を正しく読み込むよう改善。
  - .env の読み込みが失敗した場合に warnings.warn を出して続行する（ファイル I/O エラーの保護）。

- CLI の安全性向上
  - validate_config の実行結果出力で warnings/errors/infos を分離。--strict オプションで厳格モードをサポート。
  - config_setup の対話入力で EOF/KeyboardInterrupt を適切に扱い、途中キャンセル時に既存値を保持して終了。

- エラー耐性
  - run_monitoring / run_execution で例外発生時にログを残してループ継続または安全停止するように設計（例: monitor.check_once() の例外を catch して次回ポーリングへ）。

### Documentation / Messages
- 各スクリプトや関数に日本語ドキュメンテーション文字列を充実させ、使用方法や環境変数、デフォルト値、設計上の注意点を明記。

### Notes / Known issues
- research/factor_research.py の calc_momentum 関数等がファイル末尾で途中になっており、ファクター計算モジュールの一部が未完。
- 一部 TODO コメントあり（例: position_sizing の銘柄ごとの lot_size 対応、risk_adjustment の price フォールバック等）。
- 実行権限や OS 権限によって process priority / cpu affinity の設定が失敗する可能性があるため、その場合は警告でスキップする設計になっている。

---

以上が、ソースコードから推測して作成した CHANGELOG.md です。必要であれば各項目をより詳細な説明（該当ファイル名や関数名、環境変数の一覧）に展開できます。どの程度詳細にするか指示してください。