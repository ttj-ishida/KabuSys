# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
安定版リリース毎にセクションを追加してください。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（後方互換性があるもの）
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて追加

## [Unreleased]

（次回リリース用の未リリース項目をここに記載）

---

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。

### Added
- 実行用スクリプト・監視用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。KABUSYS_ENV に応じて実行環境を切替え（paper_trading では MockBroker を使用し、paper_trading 用の SQLite を使用）。
    - エンジン用 PID ファイル管理、停止フラグ（data/stop_requested.flag）に対応。スレッドで engine.run_session を実行し、フラグ検知で安全に停止する仕組みを実装。
  - run_monitoring.py
    - SystemMonitor をポーリングで実行するデーモン風スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は本番用の sqlite_path を環境にかかわらず使用する挙動を明示。

- 設定関連
  - config.py
    - Settings クラスを実装し、環境変数から各種設定を取得する抽象化を提供。
    - .env の自動ロード機能（プロジェクトルートを特定して .env / .env.local を読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 複数の便利プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 各種閾値、env/log_level 判定等）。
    - PAPER_FILL_MODE 等の入力値検証（有効値チェック）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。シークレット扱いの項目（トークン等）はマスク表示。
  - validate_config.py
    - 起動前チェック CLI を実装。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML 未インストール時はスキップ）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（"unknown" セクターは除外扱い）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier（'bull','neutral','bear' をサポート、未知値は警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に基づき発注株数を決定する calc_position_sizes を実装。
    - 単元（lot_size）丸め、1 銘柄上限・総投下上限（aggregate cap）、cost_buffer を考慮したスケーリング、および残余キャッシュを利用した再配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの初期化ユーティリティを実装。stdout への StreamHandler と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を設定。既存ハンドラをクリアして二重設定を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定と CPU affinity 設定を提供。アクセス権限等で失敗した場合は警告を出してスキップ。
- モニタリング DB 初期化フック
  - monitoring/monitoring_db.init_monitoring_db を使用して起動時に監視テーブルを冪等に初期化（run_monitoring / run_execution 両方で呼び出し）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・レイテンシ等の指標を算出してレポートを標準出力に出力する CLI を実装。P95 計算、閾値に基づく PASS/FAIL 判定を含む。
- 研究用ファクターモジュール（research）
  - research/factor_research.py
    - DuckDB を使ったモメンタム等ファクター計算の骨組みを追加（prices_daily / raw_financials に依存）。（実装は継続中、設計ドキュメントへの準拠を明記）

### Changed
- ロギング挙動
  - logging_setup: stderr ではなく stdout に StreamHandler を出力するようにし、cron / Task Scheduler 等でのリダイレクト運用に配慮。
  - ハンドラ再設定時に既存ハンドラを flush/close してから削除する安全措置を追加。
- .env 読み込みの優先度と保護
  - config.py: デフォルトロード順を OS 環境 > .env.local > .env とし、OS 環境のキーは .env により上書きされないよう protected set を導入。
- フォールバック・安全性の強化
  - MONITOR_POLL_INTERVAL の値が 0 以下または不正な場合、警告を出してデフォルト（60 秒）にフォールバックする処理を追加。
  - Settings の PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等に対して入力値検証（不正値で ValueError）を追加して誤設定を早期検出。
  - position_sizing 等で価格欠損時に skip する挙動やログ出力でデバッグしやすくした。

### Fixed
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い（クォートありとなしでの挙動差異）に対応。無効行の無視と空キーの除外を適切に処理。
- validate_config の挙動
  - PyYAML が未インストールの場合に YAML 内容検証をスキップして警告出力するようにして起動失敗を防止。

### Security
- 機密値取扱い
  - config_setup の対話 UI ではシークレット項目をマスク表示（表示時は ****）。.env のテンプレートにコメントで「.env は Git にコミットしないこと」を明記。

### Notes / Usage highlights
- 実行例:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数の主なオーバーライド:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
  - KABUSYS_ENV: 実行環境 (development / paper_trading / live)
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading 時のみ使用）
  - DUCKDB_PATH / SQLITE_PATH / LOG_LEVEL / LOG_DIR 等

---

（今後のリリースでは Unreleased セクションに追加の変更点を記載し、リリース時にバージョン見出しへ移動してください。）