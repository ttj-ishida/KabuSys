# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記述しています。

※日付はこの CHANGELOG 作成時点のものを設定しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初回リリース。基本的な自動売買フレームワークのコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、および検証ツールを追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動用スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループを終了。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する仕様を明示。
    - duckdb と sqlite の接続初期化、プロセス優先度設定を行う。
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 MockBrokerClient と専用 DB（data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用した安全停止処理。
    - スレッドでエンジンを実行し、定期的に停止フラグを確認して graceful shutdown を実行。

- 設定管理
  - Settings クラスを実装して環境変数（.env/.env.local を自動読み込み）を一元管理（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）を実装し、CWD に依存しない .env 自動読み込みを実現。
    - .env のパースはクォートやエスケープ、コメント（#）などに柔軟に対応。
    - 各種設定プロパティ（DB パス、LINE トークン、監視閾値、実行環境判定など）を提供。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式に .env を作成 / 更新するウィザード。秘密項目はマスクして表示。
    - デフォルト値、選択肢、説明文を備える。保存前の確認プロンプトを実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在確認、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境時の追加ガード等を実施。
    - `--strict` オプションで警告をエラー扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout へ StreamHandler、日次ローテーション（TimedRotatingFileHandler）でファイル出力（logs/<app_name>.log）を設定。既存ハンドラは上書きして重複防止。
    - LOG_DIR / LOG_LEVEL からの解決およびフォールバック処理を実装。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収して優先度を設定。
    - CPU affinity を最初の N コアにピン留めする機能を追加。
    - 権限不足や未対応環境では警告ログを出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - 銘柄候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates：スコア降順で上位 N を選択。
    - calc_equal_weights、calc_score_weights：等配分およびスコア加重（スコア全0 の場合は等配分にフォールバック）。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：既存保有のセクターエクスポージャーが上限を超える場合に候補を除外するロジック。
    - calc_regime_multiplier：market レジーム（bull/neutral/bear）に基づく投下資金乗数を提供。未知レジームはフォールバック（1.0）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：risk_based / equal / score に対応した発注株数計算（単元株丸め、per-stock 上限、aggregate cap スケーリング、コストバッファ考慮）。
  - これらをパッケージエクスポート（src/kabusys/portfolio/__init__.py）で公開。

- Paper Trading 検証ツール
  - paper_verification_report: Paper Trading ログ（SQLite）から稼働率、注文成功率、送信率、レイテンシ等を集計してレポートを出力する CLI を追加（src/kabusys/tools/paper_verification_report.py）。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - 日付レンジ指定（--from / --to）と DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - レイテンシの P95 計算、NULL 考慮、データ欠損時の N/A 表示などに対応。

- リサーチ / ファクター計算（初期実装）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 等のファクター設計方針をドキュメント化し、DuckDB を用いた計算を想定。
    - モメンタム計算（calc_momentum）等の実装開始（コード末尾は一部未完の状態で追加）。

### Changed
- なし（初回リリースのため変更履歴はありません）。

### Fixed
- なし（初回リリースのため修正履歴はありません）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注:
- DB 周りは sqlite3（監視・paper_trading）と DuckDB（分析用）の二層構成を採用。paper_trading モードでは本番 DB と完全分離されるよう注意が払われています。
- .env の自動読み込みは OS 環境変数を優先し、.env → .env.local（上書き）という順序を持ち、テスト時に自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を備えています。
- いくつかの関数・モジュールに TODO / 将来的な拡張コメントがあり、今後の改良点（銘柄別 lot_size、価格フォールバックなど）が示されています。