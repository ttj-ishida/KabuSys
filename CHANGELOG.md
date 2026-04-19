CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。主なカテゴリ: Added, Changed, Fixed, Removed, Security。

Unreleased
----------

（次のリリースに向けた保留中の変更やメモをここに記載してください。）

0.1.0 - 2026-04-19
------------------

Initial release — 基本機能の導入

Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するメインエントリ。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離する動作を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag によるフラグ検知で行う。
- 設定と環境管理
  - config.py: 環境変数の読み込み・解釈と Settings クラスを実装。.env 自動読み込み（.env と .env.local、OS 環境変数の保護付き）と、値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
  - validate_config.py: 起動前の設定検証 CLI。必須環境変数・ファイル（config/*.yaml）・パスの存在などを検査。--strict モードで警告もエラー扱いにできる。
- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト logs/、30 日保持）を設定する共通ユーティリティを追加。ログ出力先ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続する。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。権限不足時は安全にフォールバック。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選択（select_candidates）・等金額配分（calc_equal_weights）・スコア加重配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数を決定する calc_position_sizes を実装（risk_based / equal / score の割当方式対応、lot_size・cost_buffer・aggregate cap の考慮、スケーリングロジックを含む）。
  - portfolio/__init__.py: 上記 API を公開するパッケージエントリポイントを用意。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレードの SQLite データを解析して稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）などを出力するレポート生成ツールを追加（閾値による PASS/FAIL 判定を含む）。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB 指定可能。
- リサーチ（骨組み）
  - research/factor_research.py: DuckDB 接続を受け取り、モメンタム等のファクターを計算するモジュールの骨組み（定数と関数のインタフェース、コメントによる設計方針）。※実装の続きあり（ファイル末尾で途切れた形）。

Changed / Improvements
- .env 読み込みの堅牢化
  - config._parse_env_line: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などを実装し .env の多様な書式に対応。
  - 自動ロードの順序: OS 環境 > .env.local (override) > .env（保護付きオーバーライド実装）。
- DB 初期化の冪等化
  - run_execution / run_monitoring で init_monitoring_db を呼び、監視テーブルの存在を保証（何度呼んでも安全）。
- ログ出力の標準化
  - 全起動スクリプトで setup_logging(app_name=...) を呼ぶことでログの命名・ローテーションを統一。
  - StreamHandler は stdout を利用（cron 等での stdout/stderr リダイレクトを考慮）。
- エラーハンドリングの改善
  - run_monitoring のポーリングループで monitor.check_once() の例外を捕捉し、ループ継続（堅牢化）。
  - process_priority の権限不足や未対応プラットフォームでの失敗を警告ログとして安全にスキップ。
- ExecutionEngine 起動制御
  - data/stop_requested.flag の存在をチェックして起動抑止・停止する安全機構を実装。エンジンはスレッドで実行され、停止フラグ検知で engine.stop() を呼ぶ。
- 設定検証の柔軟化
  - validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出す（環境による依存性に配慮）。

Fixed / Behavior fixes
- MONITOR_POLL_INTERVAL の検証とフォールバック
  - run_monitoring._get_poll_interval で 1 未満や非数値入力を警告し、デフォルト（60 秒）へフォールバックするように変更。time.sleep に無効な値が渡らないよう安全化。
- PAPER_FILL_MODE 検証
  - Settings.paper_fill_mode で有効値チェックを行い、不正な値は ValueError を返す。既定値は "instant"。
- ログディレクトリ作成失敗時の挙動
  - logging_setup.setup_logging はディレクトリ作成に失敗した場合、ファイルハンドラ作成をスキップしてコンソール出力のみで継続するよう変更（起動失敗を避ける）。

Known limitations / TODO（ソースコメントより）
- portfolio/risk_adjustment.apply_sector_cap
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる懸念あり。将来的には前日終値や取得原価などのフォールバック価格を用いる検討が必要。
- portfolio/position_sizing
  - 将来的に銘柄毎の lot_size をサポートするための拡張案あり（現在は共通 lot_size）。
- research/factor_research.py
  - ファイル末尾で実装が途中で終わっている（calc_momentum の定義途中）。追加実装が必要。

Configuration / Migration notes
- 環境変数の既定値と名前
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用、KABUSYS_ENV=paper_trading 時に使用）
  - LOG_LEVEL, LOG_DIR, PID_FILE_PATH 等が利用可能
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード挙動）
- .env を自動生成/更新する場合は config_setup.py を利用すると安全（.env は機密情報を含むため Git にコミットしないこと）。

Security
- .env ファイルに API トークン等の機密情報を保存する仕様のため、.env をリポジトリにコミットしない旨の注意喚起を config_setup のヘッダで明記。
- process_priority / cpu_affinity での権限問題はログで通知して安全にスキップする実装。

その他
- パッケージバージョンは kabusys.__version__ = "0.1.0" を設定。
- ドキュメント断片（コメント、PortfolioConstruction.md 等の参照）がコード内に豊富にあり、今後の機能拡張・テスト作成の指針として利用可能。

もし特に重要な変更点や、リリースノートに追加したい細部（例: 主要 CLI の使用例、既知の重大なバグ修正履歴など）があれば教えてください。追記して更新します。