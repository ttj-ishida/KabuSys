CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードベースから推測できる最新の状態に合わせています。

Unreleased
----------

- ドキュメント化・微修正
  - 内部コメントや docstring の説明を整理、CLI ヘルプやログメッセージをわかりやすく改良しました。
  - 一部モジュール（research/factor_research.py）に対して追加実装・テストが必要である旨を注記しました（実装途中の関数あり）。

0.1.0 - 2026-04-24
-----------------

Added
- 初期リリース: KabuSys 自動売買システムの基盤機能を実装。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine 起動用エントリポイント。KABUSYS_ENV=paper_trading 時は専用の紙トレード用 DB（data/paper_trading.db）を使用し、MockBrokerClient を利用する旨をサポート。
    - run_monitoring.py: SystemMonitor ポーリングループ起動用スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）を監視して安全に終了。
  - 設定管理
    - config.py: .env ファイル自動ロード機能（.env, .env.local、OS 環境変数保護あり）。キー必須チェック用の Settings クラスを提供。PAPER_FILL_MODE 等のバリデーション、paper_trading 用のデータベースパス設定などを実装。
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を実装。
    - validate_config.py: .env と config/*.yaml の検証ツール。--strict オプションで警告をエラー扱いにできる。
  - ログ・ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定関数 setup_logging を実装。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続。
    - utils/process_priority.py: psutil を用いたプロセス優先度設定と CPU affinity 設定のユーティリティ（Windows / POSIX の差分吸収）。
  - 監視・実行の DB 初期化
    - monitoring/monitoring_db の初期化呼び出しを各起動スクリプトから行うことで監視テーブルの存在を保証（冪等に初期化）。
  - 実行コンポーネント（Execution）
    - execution パッケージの依存コンポーネント（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager）を組み立て、ExecutionEngine をスレッドとして起動・停止する仕組みを実装。停止フラグの検出でエンジンを安全停止。
  - ポートフォリオ関連（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウンと残余キャッシュの配分ロジック。
  - 分析ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。稼働率・注文成立率・送信率・API レイテンシ（P95 等）を算出し PASS/FAIL 判定を出力。しきい値を定義（稼働率 >=99%、注文成功率 >=90% など）。
  - Research（ファクター計算）
    - research/factor_research.py: ファクター計算モジュールの骨子を実装（モメンタム、ボラティリティ、流動性などを想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。calc_momentum 等の関数設計と定数を定義（一部実装は継続中）。

Changed
- 環境ロードの優先順位と保護
  - OS 環境変数を保護して .env/.env.local の上書きを制御。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- run_monitoring: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様を明確化（監視データは本番 DB に記録）。
- run_execution: paper_trading モードでは paper_sqlite_path（data/paper_trading.db）を使用し、本番 DB と分離。
- Logging: stdout を使用する StreamHandler を採用（stderr ではなく stdout）。ログレベル解決の優先度を明示（引数 > 環境変数 > デフォルト）。
- process_priority: 起動直後に優先度を high に設定するように起動スクリプト側で呼び出し。プラットフォームごとの差分は内部ユーティリティで吸収。

Fixed
- 環境変数パースの堅牢化
  - .env の行解析で export KEY=val 形式、クォート内のエスケープ、インラインコメント処理等に対応。無効行のスキップや空白処理を改善。
- MONITOR_POLL_INTERVAL の取り扱い
  - 不正（0 以下や数値以外）の入力時に警告を出しデフォルトにフォールバックする挙動を追加（time.sleep に不正値が渡らないよう保護）。
- DB/接続の安全性
  - 起動ループやスレッド終了時に sqlite / duckdb 接続を確実に close するように修正。
- ログディレクトリ作成失敗時のフォールバック
  - ディレクトリの作成に失敗した場合はファイルハンドラをスキップし、コンソール出力のみで継続する。失敗時は stderr へ警告を出力。

Removed
- なし（初期リリース）。

Security
- セキュリティ上の注意点をドキュメント化
  - .env ファイルは絶対に Git にコミットしない旨を config_setup.py のヘッダに記載。
  - 本番（KABUSYS_ENV=live）時の設定チェックで LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険な設定を警告するガードを実装。

Known issues / Notes
- research/factor_research.py の一部関数は実装の継続が必要（calc_momentum 等の計算ロジックが途中で終端している箇所あり）。本モジュールは DuckDB のスキーマ（prices_daily / raw_financials）に依存します。
- 一部外部ライブラリ（psutil, duckdb, PyYAML）が必須または推奨されるため、環境によっては追加インストールが必要。
- run_monitoring/run_execution の起動やプロセス優先度設定は OS 権限に依存するため、アクセス拒否等の例外はログに警告出力してスキップする実装となっています。

開発・運用に関する補足
- 主要な環境変数（デフォルト値）:
  - KABUSYS_ENV (development|paper_trading|live) — default: development
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - LOG_LEVEL — default: INFO
  - MONITOR_POLL_INTERVAL — default: 60 (秒)
  - PAPER_FILL_MODE — default: instant（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START — default: 0
- ログは既定で logs/<app_name>.log に日次ローテーションで保存（最大 30 日分保持）。ログディレクトリ作成に失敗した場合はコンソールのみで動作。

Versioning
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として管理しています。