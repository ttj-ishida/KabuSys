# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

注: この CHANGELOG はリポジトリ内のソースコードから推測して作成したものです（実装内容に基づく要約）。

## [0.1.0] - 2026-04-19

### Added
- 初期リリース（0.1.0）。
- 実行用・監視用エントリポイントスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を利用して本番 DB と分離可能。
    - エンジンはスレッドで実行され、data/execution.pid に PID を書き込み、data/stop_requested.flag による外部停止を監視。
    - 起動時にプロセス優先度を "high" に設定。
    - RiskManager に対するデフォルト RiskConfig を設定して起動。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず（KABUSYS_ENV に依らず）本番 sqlite_path を使用して DB に記録。
    - 起動時にプロセス優先度を "high" に設定し、stop フラグファイルでループを終了する。
- 環境設定・管理
  - config.py
    - Settings クラスを追加。環境変数から設定値を取得する一元化インタフェースを提供。
    - .env 自動読み込み機能を追加（プロジェクトルートに .git または pyproject.toml がある場合）。優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースの強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなど）。
    - PAPER_FILL_MODE（paper trading の約定挙動）を導入。許容値: "instant" | "partial" | "never" | "reject"。デフォルト "instant"。
    - 各種閾値・パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）をプロパティで提供。
- 設定支援 CLI
  - config_setup.py
    - 対話式ウィザードにより .env の初期作成・更新を支援。
    - デフォルト値・選択肢・シークレット項目表示（保存時はマスク）に対応。
    - 出力フォーマット・テンプレートで .env を安全に生成。
  - validate_config.py
    - .env および config/*.yaml の設定不備を起動前に検出する CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - --strict オプションで警告を FAIL 扱いにして exit(1) で終了可能。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。
    - コンソール出力（stdout）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリの自動作成（LOG_DIR 環境変数で上書き可）。ファイルハンドラ作成失敗時はコンソールのみで継続。
    - ログレベル解決順: 引数 level > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順で上位 N 件を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（全スコア 0 の場合は等配分にフォールバックし警告）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中を抑えるフィルタ機能（sell_codes を除外可能、"unknown" セクターは制限対象外）。
      - calc_regime_multiplier: market レジームに応じた資金乗数（bull/neutral/bear）を提供。未知のレジームは警告を出して 1.0 でフォールバック。
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算を提供。単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料等の保守的見積り）に対応。aggregate cap 超過時はスケーリングと余剰配分ロジックを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH 指定可）から各種指標を集計して検証レポートを生成する CLI を追加。
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。閾値を定義して PASS/FAIL を判定。
    - --from / --to オプションによる期間絞り込み、--db で DB パス指定可能。
- research モジュールの一部
  - research/factor_research.py（モメンタム等のファクター計算の骨格を追加）。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。

### Changed
- DB 初期化の堅牢化
  - run_execution.run() と run_monitoring.main() で init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB とファイルを分離するよう動作。

### Fixed
- .env パースと読み込みの堅牢化
  - export プレフィックス、クォート付き値のエスケープ、インラインコメント処理、既存 OS 環境変数の保護（protected）を実装。ファイル読み込み失敗時は警告を出す。

### Notes / Known limitations
- research/factor_research.py は現状で関数の骨格があり、実装途中の箇所（例: 一部変数の定義途中など）が見受けられます。製品利用時は追加実装・テストが必要です。
- apply_sector_cap: price_map に欠損（price が 0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格（前日終値等）を導入する予定の旨の TODO コメントあり。
- process_priority / set_cpu_affinity は権限不足や未対応環境で安全にスキップされるが、意図通りに動作しない場合は OS 権限の確認が必要。
- ロガー初期化: ログディレクトリ作成に失敗するとファイル出力が無効化されコンソールのみになる点に注意。

### Security
- .env は絶対に Git にコミットしない旨を config_setup のテンプレートに明示。

---

（以降の変更は Unreleased セクションに追記してください）