# CHANGELOG

すべての重要な変更をここに記載します。本ファイルは「Keep a Changelog」準拠の書式を目指しています。

最新: 0.1.0 (初期リリース)

## [0.1.0] - 2026-04-23

### Added
- 初期リリース。
- コア機能
  - kabusys パッケージの骨格を追加。バージョンは __version__ = "0.1.0"。
  - 起動スクリプト:
    - run_execution.py — ExecutionEngine 起動用。プロセス優先度を「high」に設定し、BrokerClientFactory を通して実ブローカーまたは MockBrokerClient を起動可能（KABUSYS_ENV に依存）。ペーパートレード時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - run_monitoring.py — SystemMonitor のポーリングループ起動用。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視（monitoring）処理は環境にかかわらず本番 sqlite_path を使用。
  - CLI / ユーティリティ:
    - config_setup.py — 対話式 .env ウィザード。多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を対話的に作成/更新して .env に保存。
    - validate_config.py — 起動前チェックツール。.env と config/*.yaml の存在・妥当性を検証。--strict オプションで警告も失敗（exit(1)）として扱う。
    - tools/paper_verification_report.py — Paper Trading 用検証レポート生成。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力。デフォルト DB: data/paper_trading.db。閾値はソース内定義（例: 稼働率 >= 99% 等）。
- 設定管理
  - config.py — Settings クラスを導入。環境変数の読み取り、必須変数チェック、デフォルト値、KABUSYS_ENV の妥当性検証などを実装。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込み。OS 環境変数は保護され、.env.local は上書き可能。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパースはシングル/ダブルクォート、export プレフィックス、インラインコメント等に対応。
  - Settings で利用可能な主な環境変数/デフォルト:
    - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
    - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
    - LOG_LEVEL, KILL_FLAG_CLEAR_ON_START, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値 等
- DB / 分析
  - duckdb 接続を導入（duckdb_path 経由）。分析用途と高速集計に使用。
  - 監視用 SQLite（monitoring.db）初期化ユーティリティを導入（init_monitoring_db を使用）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates — BUY シグナルをスコア降順でソートし上位 N を選択。
    - calc_equal_weights — 等金額配分。
    - calc_score_weights — スコア比率に基づく配分（全スコアが 0 の場合は等分にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap — セクター集中制限を適用（既存ポジションのセクター比率が閾値を超える場合、新規候補を除外）。"unknown" セクターは除外対象としない。
    - calc_regime_multiplier — 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3、未知の値は 1.0 にフォールバックして警告）。
  - portfolio.position_sizing:
    - calc_position_sizes — リスクベース / equal / score の各配分方式に対応。単元株（lot_size）丸め、1銘柄上限（max_position_pct）、総投下上限（max_utilization）、コストバッファを考慮した aggregate cap スケーリングを実装。スケーリング後の端数は lot_size 単位で再配分するロジックあり。
- 実行/監視ユーティリティ
  - utils.logging_setup — 統一ログ設定関数を提供。StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。LOG_DIR/LOG_LEVEL 環境変数で制御。既存ハンドラをクリアして二重設定を防止。
  - utils.process_priority — psutil を用いたプロセス優先度設定（Windows と POSIX を吸収）。set_process_priority("high"|"normal"|"low") と set_cpu_affinity を提供。権限不足等は警告でスキップ。
- 研究/分析
  - research.factor_research — ファクター計算の枠組みを追加（Momentum / Value / Volatility / Liquidity の計算ポリシーを定義）。DuckDB を利用し prices_daily / raw_financials を参照する設計（実装はモジュール内で段階的に実装予定）。
- その他
  - パッケージエクスポート: kabusys.portfolio の主要関数を __all__ で公開。
  - tools モジュールを追加（paper_verification_report を含む）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- シークレット系設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）は .env で管理する前提。config_setup で生成される .env に注意喚起を明記（.env を Git にコミットしないことを推奨）。

### Notes / Usage highlights
- 起動/停止フロー:
  - run_execution や run_monitoring はプロジェクトルート直下の data/stop_requested.flag を監視して安全に停止できる。ExecutionEngine は起動時に同フラグが既に立っている場合は起動を中止する。
  - ExecutionEngine は実行中に stop フラグを検知すると engine.stop() を呼んでワークスレッドを停止する。
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を整数秒で指定可能。無効値はデフォルト 60 秒にフォールバック（警告ログ出力）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading 時は BrokerClientFactory が MockBrokerClient を返し、発注ログなどは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録される。
  - paper_fill_mode（PAPER_FILL_MODE）で約定挙動（instant/partial/never/reject）を制御。
- validate_config.py:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定を検出。
  - config/*.yaml の存在チェックと、PyYAML があればパース検証を行う（未インストール時は検証をスキップして警告）。
  - KABUSYS_ENV=live の場合は本番向けの追加ワーニングを出力（LINE 設定の未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）。

---

注: 本 CHANGELOG はソースコードの内容から推測して作成したものであり、実際のリリースノートやユーザー向けドキュメントとして用いる際は、実装状況・動作確認に基づいて追記・修正してください。