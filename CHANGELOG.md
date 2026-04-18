# Changelog

すべての変更は「Keep a Changelog」準拠で記載しています。  
各リリースの項目は Added / Changed / Fixed / Removed に分類しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 初期公開
最初のリリース。日本株自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール群を追加。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検出によりループを終了。
    - 監視（monitoring）用 DB は環境にかかわらず本番 sqlite_path を使用する仕様を採用。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（BrokerClientFactory 経由）を使用し、専用の Paper Trading SQLite DB（デフォルト: data/paper_trading.db）で本番 DB と分離して動作。
    - エンジンの PID ファイル管理、停止フラグ監視により安全に停止処理を実行。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境管理
  - config.py
    - 環境変数読み込みと Settings クラスを提供。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。.env と .env.local の読み込み順序を実装（.env.local は上書き）。
    - .env パーサーが export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントをサポート。
    - 各種設定プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/メモリ/ディスク閾値、PAPER_FILL_MODE の検証など）を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。

- 設定ユーティリティ・CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成/更新を支援。
    - 秘匿値は表示時にマスクし、既存値の再利用やデフォルト値の提示を行う。
    - .env 書き込み機能を提供（.env を絶対に Git にコミットしない旨の注記を含むテンプレートで出力）。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を提供。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス（親ディレクトリ存在）チェック、config/*.yaml の存在確認と YAML パース検証（PyYAML が未インストールの場合は警告してスキップ）を実施。
    - --strict フラグで警告を FAIL 扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション、30世代保持）をルートロガーに統一して設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフェールセーフを実装。
    - デフォルトのログディレクトリは logs/、ログレベルは環境変数 LOG_LEVEL で制御可能。
  - utils/process_priority.py
    - Windows と POSIX 系（Linux/Mac 等）の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を設定する set_cpu_affinity 関数を提供（コア数指定で最初の N コアに固定）。権限不足などは警告してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 select_candidates（スコア降順、同点時に signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外）。unknown セクターは除外しない。
    - calc_regime_multiplier: 市場レジーム ("bull", "neutral", "bear") に応じた投下資金乗数を返す。未知レジームは警告のうえ 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に従い銘柄ごとの発注株数を計算。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）・aggregate cap（available_cash）適用、cost_buffer（スリッページ・手数料見積り）考慮のスケーリングロジックを実装。
    - aggregate cap 超過時のスケールダウン時に端数処理を残差（fractional）順で再配分するアルゴリズムを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB（既定: data/paper_trading.db）からシステム安定性・注文成功率・送信率・レイテンシ等を集計してレポート出力する CLI を追加。
    - P95 レイテンシ計算、稼働率・成功率等の判定基準（閾値）を定義し PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間・DB パスを指定可能。

- リサーチ / ファクター計算（部分実装）
  - research/factor_research.py
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いてモメンタム・値等のファクターを計算する設計を追加（モジュール骨子、定数と docstring を含む）。一部実装（calc_momentum の開始部分）を含む。

- パッケージ情報
  - __init__.py によるバージョン定義: __version__ = "0.1.0"

### Changed
- なし（初期リリースのため）

### Fixed
- なし（初期リリースのため）

### Removed
- なし（初期リリースのため）

---

注記・運用上のポイント
- 監視プロセスは監視用の sqlite を環境に依存せず本番パスで開く設計になっているため、意図的に本番 DB を参照してしまう可能性があります。Paper Trading と分離したい場合は設定を確認してください（ExecutionEngine は paper_trading 環境時に専用 DB を使用）。
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。CI/テスト環境ではこれを利用して環境干渉を防いでください。
- ログディレクトリ作成やプロセス優先度設定は権限やプラットフォームに依存します。権限不足時は警告ログを出してスキップする挙動です。
- PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START などの環境変数は挙動に影響するため、.env 作成時に config_setup.py のガイドに従って適切に設定してください。