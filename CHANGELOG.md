# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
注: 以下の内容はリポジトリ内のコードから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 初期リリース: KabuSys パッケージを追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。
- 設定関連
  - Settings クラスを実装（環境変数をラップし、デフォルト値・検証を提供）。
    - 各種プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_*、DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値（CPU/MEM/DISK）など。
    - KABUSYS_ENV 値検証（development / paper_trading / live）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
  - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索し、`.env` / `.env.local` をロード）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env パース実装: export プレフィックス対応、クォート文字列のエスケープ対応、コメント扱いのルール等をサポート。

- 起動・運用用スクリプト
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine 起動ラッパーを実装。
    - プロセス優先度を High に設定。
    - Paper trading 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期 available_cash を broker.get_available_cash() で取得。
    - デーモンスレッドで engine.run_session を実行、data/stop_requested.flag による停止検知、実行 PID ファイル管理。
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - data/stop_requested.flag による停止制御。

- CLI / ユーティリティ
  - config_setup（src/kabusys/config_setup.py）
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 必須・任意項目、シークレット入力、選択肢表示、既存値の再利用などをサポート。
    - .env のテンプレート書き出しを実装（.env に絶対にコミットしない旨のヘッダ付き）。
  - validate_config（src/kabusys/validate_config.py）
    - .env と config/*.yaml の起動前検証ツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML の存在とパース検査（PyYAML が存在する場合）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定未整備や KILL_FLAG_CLEAR_ON_START の危険設定の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - tools.paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを計算し PASS/FAIL 判定を出力。
    - デフォルト DB パス: data/paper_trading.db。--db で上書き可能。
    - 期間フィルタ (--from / --to) に対応。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder
    - select_candidates（スコアでソートして上位 N を選択）、calc_equal_weights、calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap（既存保有をもとにセクター集中制限を適用）、calc_regime_multiplier（market regime に基づく投下資金乗数: bull/neutral/bear をマッピング）。
  - portfolio.position_sizing
    - calc_position_sizes（allocation_method: risk_based / equal / score をサポート）。
    - lot_size（単元）で丸め、per-position と aggregate のキャップ適用、cost_buffer による保守的コスト見積もり、スケールダウンと残余配分ロジックを実装。

- ユーティリティ
  - utils.logging_setup（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30 日保持）を設定。
    - ログレベルは引数 > 環境変数 > デフォルト の順で解決。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - StreamHandler は stdout を使用（cron 等でリダイレクトしやすくするため）。
  - utils.process_priority（src/kabusys/utils/process_priority.py）
    - クロスプラットフォームでプロセス優先度を設定（Windows の priority class、POSIX の nice 値）。
    - set_cpu_affinity を提供（最初の N コアに固定、アクセス拒否等は警告でスキップ）。

- 研究用モジュール（基盤）
  - research.factor_research（src/kabusys/research/factor_research.py）
    - ファクター計算の基盤を追加（モメンタム、MA200、ATR、流動性等の計算を意図）。DuckDB の prices_daily テーブルを参照する設計。モジュールは関数 calc_momentum の導入を含む（実装の一部が含まれる）。

- DB 初期化
  - monitoring_db の初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring で実行し、監視テーブルの存在を保証（冪等処理）。

### Changed
- （初版のため該当なし）

### Fixed
- 各所で実行時の障害に対してフォールトトレラントな挙動を追加:
  - .env 読み込み失敗時に警告を出して続行。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時はコンソール出力にフォールバック。
  - process priority / cpu affinity 設定時の AccessDenied 等を捕捉して警告でスキップ。
  - run_monitoring の MONITOR_POLL_INTERVAL が不正な値だった場合にデフォルトを使用し警告を出す。

### Security
- config_setup に .env を作成するテンプレートを含め、ファイルに「絶対に Git にコミットしないこと」を明示。
- Settings._require にて必須環境変数が未設定の場合に ValueError を投げて明示的な失敗を誘導。

### Notes / Migration
- Paper Trading 実行時はデータベースが本番と分離される（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。運用時は環境変数の設定を確認してください。
- 起動前に python -m kabusys.validate_config で設定検証を行うことを推奨します。
- ログの出力先は LOG_DIR 環境変数で変更可能。デフォルトは logs/。
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を変更可能（秒）。1 未満や非整数の指定は無視されるので注意。

---

（必要に応じて今後のリリースでは "Changed" / "Fixed" セクションを詳細化してください。）