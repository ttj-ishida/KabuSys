# Changelog

すべての注記は Keep a Changelog の形式に従い、コードベースから推測して作成しています。

全般:
- 日付はリポジトリ内のバージョン情報および現行のスクリプト実装から初期リリースとして記載しています。
- 環境変数やファイルパス、動作仕様はソース内のコメント・実装に基づいて記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-21

### Added
- 基本機能の初期実装（KabuSys v0.1.0）。
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine を起動するエントリ。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、paper_trading 環境では MockBrokerClient 経由での分離された発注動作を想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず production の sqlite_path を使用する実装。
- 設定管理
  - config.py: 環境変数を扱う Settings クラスを提供。自動でプロジェクトルートの .env/.env.local をロードする機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化あり）。.env パースは quoted 値・エスケープ・インラインコメント等に対応。
  - config_setup.py: .env を対話的に生成/更新するウィザード CLI を実装。主要設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）をサポート。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を実装。必須環境変数・パス・YAML のパースチェック・本番環境向けの追加ガードを出力し、--strict モードを提供。
- ロギング・ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定関数 setup_logging を実装。コンソール (stdout) と 日次ローテーション (TimedRotatingFileHandler) をルートロガーに設定。ログディレクトリ作成失敗時にフォールバック。
- プロセス制御ユーティリティ
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定用ユーティリティを実装。設定失敗時は安全にスキップして警告を出力。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選択（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 発注株数算出ロジック（リスクベース、等金額、スコア加重）、単元株丸め、aggregate cap によるスケーリングと残差配分ロジックを実装。
  - portfolio/__init__.py: 上記関数をエクスポート。
- 研究用モジュール（骨子）
  - research/factor_research.py: DuckDB を用いたファクター計算（モメンタム・MA200 乖離・ATR 等）を想定したモジュールの開始（関数シグネチャと設計方針を実装）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の SQLite データベースから稼働率、注文成功率、送信率、レイテンシ指標（平均/最大/P95）を集計してレポート出力するスクリプトを実装。デフォルト閾値（稼働率 99%、成立率 90% 等）とパス指定オプションをサポート。
- パッケージ初期化
  - __init__.py: バージョン情報 __version__ = "0.1.0" を追加。

### Changed
- データベース取り扱い方針（実装上の設計決定）
  - 監視系（run_monitoring）は KABUSYS_ENV にかかわらず monitoring 用の sqlite_path（settings.sqlite_path）を使用する設計（意図的に本番監視 DB を参照する仕様）。
  - 発注系（run_execution）は paper_trading 環境で paper_sqlite_path を使用することで paper_trading と本番 DB を完全に分離。
- ログ出力先の扱い
  - logging_setup は stdout を StreamHandler に使用（stderr ではなく stdout）し、日次ローテーションを file handler で行う。ログディレクトリの作成失敗時はファイル出力をスキップしてコンソールのみで継続する耐障害性を確保。
- .env 自動ロード順序
  - OS 環境変数 > .env.local > .env の優先度で読み込み。既存 OS 環境変数は保護される（protected set）。

### Fixed
- .env パーサーの堅牢化
  - config._parse_env_line は export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱いなどを考慮してより正確に .env をパースするよう実装。
- 監視・実行スクリプトの安全な終了処理
  - run_monitoring.py / run_execution.py は stop flag（data/stop_requested.flag）や PID ファイルの扱いを実装し、KeyboardInterrupt などによる終了時に DB 接続を確実にクローズするよう対応。
- process_priority のフォールバック処理
  - set_process_priority/set_cpu_affinity は権限不足や未対応プラットフォーム時に例外を投げず警告ログを出して処理を続行するよう対応。

### Security
- 秘匿値取り扱い
  - config_setup のウィザードで J-Quants リフレッシュトークンや KABU_API_PASSWORD を secret として扱い、表示時にマスクする仕様。

### Known limitations / Notes
- research/factor_research.py は設計方針と定数、関数の骨格を実装しているが、完全実装（データスキャンの詳細等）は継続作業が必要。
- position_sizing の価格欠損（price が 0.0 の場合）に関する注釈（TODO）が残っており、将来的に価格フォールバック（前日終値等）を導入する余地がある。
- apply_sector_cap は "unknown" セクターを上限チェック対象外とする挙動を採用している点に注意。
- settings.paper_fill_mode は有効値検査を行い、不正値は ValueError を発生させるため環境変数の設定ミスに注意。

---

以上がソースコードの実装内容から推測・整理した CHANGELOG.md です。必要であれば、個別機能（例: position sizing のアルゴリズム詳細や CLI の使用例）を追記できます。