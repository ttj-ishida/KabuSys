# Changelog

すべての注目すべき変更をここに記載します。フォーマットは "Keep a Changelog" に準拠します。  

※ 初回リリース（v0.1.0）は、実装された主要機能・CLI・ユーティリティ群の導入をまとめています。

## [0.1.0] - 2026-04-21

### Added
- 基本情報
  - パッケージバージョンを v0.1.0 に設定（src/kabusys/__init__.py）。
  - プロジェクト全体の初期的な自動売買システム基盤を実装。

- 設定管理
  - Settings クラスによる環境変数ラッパーを実装（src/kabusys/config.py）。
    - 自動でプロジェクトルートの .env / .env.local を読み込み（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - 多数の設定プロパティ（J-Quants / kabu API / DB パス / PID / Kill Switch / 監視閾値 等）を提供。
    - env 値や LOG_LEVEL、PAPER_FILL_MODE 等の検証ロジックを実装。
  - 簡易設定ウィザード CLI（python -m kabusys.config_setup）を追加。
    - 対話式で .env を生成・更新。秘密項目はマスクされる。
  - 設定検証 CLI（python -m kabusys.validate_config）を追加。
    - 必須環境変数や DB パス、config/*.yaml の存在・パースチェック、KABUSYS_ENV の安全ガード等を実行。
    - --strict オプションで警告を失敗に扱うことが可能。

- 起動スクリプト
  - 監視プロセス起動スクリプト run_monitoring を追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を初期化してポーリングループを実行。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 停止はプロジェクトの data/stop_requested.flag で検知。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
  - 実行エンジン起動スクリプト run_execution を追加（src/kabusys/run_execution.py）。
    - ExecutionEngine を組み立てて別スレッドで実行。停止フラグで安全に停止。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db など）を使用し、本番 DB と完全分離。
    - BrokerClientFactory 経由で本番/モックブローカーを切り替え、RiskManager / Reconciler / OrderManager 等を組立てて実行。

- ロギング・プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を定義。既存ハンドラは再設定時にクリアする。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して current process の優先度（high/normal/low）を設定。
    - CPU affinity の設定関数も実装。権限不足や未対応 OS の場合は安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順で上位 N 抽出）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、スコアが全て 0 の場合は等金額にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター比率が閾値を超える場合に新規候補を除外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく投下資金乗数。未知値は 1.0 でフォールバック）
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：allocation_method（risk_based / equal / score）をサポート
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer（手数料/スリッページ考慮）等を実装
    - スケールダウン後の余剰を fractional 残差に基づき lot 単位で再配分するロジックを搭載

- Paper Trading 向け検証レポート
  - paper_verification_report ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し、稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）を算出して PASS/FAIL 判定を出力。
    - デフォルトしきい値: uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms。
    - --from/--to/--db オプションで期間・DB 指定可能。

- 研究用ファクター計算（骨格）
  - factor_research モジュール（src/kabusys/research/factor_research.py）にモメンタム等の計算ロジックの骨格と定数を実装（DuckDB を用いた prices_daily / raw_financials 参照を想定）。
    - モメンタム・MA200・ATR・出来高系などを計算する設計方針を反映。

### Changed
- 初回リリースのため、過去バージョンからの変更履歴はありません。

### Fixed
- 初回リリースのため、過去バージョンの修正点はありません。

### Known issues / Notes
- factor_research の実装はファイル末尾で途中（calc_momentum 等の関数実装が途中で切れている可能性あり）。本モジュールは今後の拡張対象。
- position_sizing 内で price が欠損（0.0）の場合のフォールバックは TODO コメントあり（前日終値や取得原価による補完を想定）。
- run_monitoring は監視用 DB として常に settings.sqlite_path（本番パス）を使用するため、paper_trading 環境で監視データを分離したい場合は運用ルールに注意。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでスキップする実装。想定どおりの効果が得られない環境があり得る。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化してコンソールのみで継続する。

### Development / Usage notes
- .env の自動読み込みはプロジェクトルートの検出に依存（.git または pyproject.toml を基準）。パッケージ配布後も CWD に依存せず動作する設計。
- .env のパースは引用符・エスケープ・インラインコメントを考慮した堅牢な実装。
- validate_config と config_setup により、導入時の設定ミスを事前検出・補助するワークフローを提供。
- Paper Trading（モック）と Live は DB を分離して運用する設計（settings.paper_sqlite_path を使用）。
- 実行時は run_monitoring/run_execution のログ出力や PID ファイル、停止フラグ（data/stop_requested.flag）によってプロセス管理を行う。

---

今後の主な予定:
- factor_research の完成・ユニットテスト追加
- ExecutionEngine 周りのさらなる堅牢化とリスク管理ロジックのチューニング
- ドキュメント（README / Usage / Deployment）と CI ワークフローの整備

---