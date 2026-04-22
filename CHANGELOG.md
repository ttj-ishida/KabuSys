CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています。

Unreleased
----------

（今後の変更はここに記載します）

v0.1.0 - 2026-04-22
------------------

Added
- 初回リリース。KabuSys - 日本株自動売買システムのコア機能を実装。
- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - data/stop_requested.flag による停止制御、PID ファイル書き込み機構（data/execution.pid）。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用し、停止フラグでループ終了。
- 設定関連 CLI / ユーティリティ
  - config_setup.py：.env の対話式ウィザード（.env の初期作成・更新）。
  - validate_config.py：.env および config/*.yaml の起動前検証ツール（--strict オプションあり）。
  - config.py：環境変数読み込みと Settings クラスを実装。
    - プロジェクトルート検出（.git/pyproject.toml 基準）により .env/.env.local の自動読み込みをサポート。
    - export 形式やクォート・インラインコメントに対応した .env パーサ実装。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連等）を提供。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder：候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）。
  - portfolio.risk_adjustment：セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
  - portfolio.position_sizing：単元株丸め、リスクベース／等分配／スコアベースの発注株数計算（calc_position_sizes）。
    - aggregate cap のスケーリング、lot_size 単位での丸め、cost_buffer による保守的見積りを実装。
- ログ・プロセスユーティリティ
  - utils.logging_setup：StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）の統合設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils.process_priority：Windows/Linux/macOS でプロセス優先度（nice/HIGH_PRIORITY_CLASS）と CPU affinity の設定を提供。実行環境に応じたフォールバックと権限制御に対応。
- research/factor_research：ファクター計算モジュールの骨組み（モメンタム等の計算設計、定数、calc_momentum の開始実装）。
- tools.paper_verification_report：Paper Trading 用検証レポート生成スクリプトを実装。
  - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを算出して判定（PASS/FAIL）。
  - CLI オプション --from/--to/--db、環境変数 PAPER_TRADING_SQLITE_PATH をサポート。
  - 判定基準（稼働率 99%、成立率 90% 等）と P95 計算ロジックを実装。

Changed
- ログ出力は stdout を利用する設計を採用（cron/Task Scheduler 実行時のリダイレクトを想定）。
- .env 自動読み込みの優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを抑止可能。
- Settings により実行環境（KABUSYS_ENV）とログレベルのバリデーションを厳格化。無効値は ValueError を送出して早期検出。

Fixed
- .env パーサの強化
  - export プレフィックス対応、シングル/ダブルクォート内部のバックスラッシュエスケープ処理、インラインコメントの扱い等を適切に処理するよう改良。
- process_priority / set_cpu_affinity の失敗時にワーニングを出してスキップする堅牢性を実装（権限不足や未対応プラットフォーム対応）。
- run_monitoring / run_execution で使用する DB 初期化（init_monitoring_db）を起動時に実行し、監視テーブルが存在しない場合でも冪等的に初期化するようにした。

Security
- シークレット値（J-Quants トークン、kabu API パスワード等）は .env に明記されるため、config_setup にて .env を絶対に Git にコミットしない旨の注記を追加。

Notes / Known limitations
- research/factor_research モジュールは計算方針とユーティリティを実装済みだが、ファクター計算関数群（全指標の最終実装）は一部未完（calc_momentum 以下が途中）。
- position_sizing の価格フォールバックは未実装。price_map/open_prices に欠損（0.0）がある場合は保守的にスキップする仕様のため、将来的に前日終値等のフォールバックを導入することを想定。
- PAPER_FILL_MODE は有効値チェックを行い、不正値は ValueError を送出する（運用時は .env を適切に設定してください）。
- config/*.yaml の内容検証は PyYAML がインストールされていない場合スキップされる（validate_config.py が警告を出します）。
- ログディレクトリの作成に失敗した場合、ファイル出力が無効化されログは標準出力のみになる点に注意。

Acknowledgments
- 本リリースではプロジェクトの基盤機能（起動スクリプト、設定管理、ログ、プロセス制御、ポートフォリオ構築、簡易検証ツール）を優先的に実装しました。今後はファクター計算、戦略本体、ブローカー実装、テストカバレッジ拡充を予定しています。