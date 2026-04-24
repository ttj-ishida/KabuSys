CHANGELOG
=========

すべての変更は "Keep a Changelog" の書式に従って記載しています。  
セマンティックバージョニングを採用しています。

[Unreleased]
-------------

なし

[0.1.0] - 2026-04-24
--------------------

Added
- 基本パッケージの初期実装を追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 実行・監視系起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用する点を明示。
    - BrokerClientFactory によるブローカークライアント生成を導入（実行環境に応じて MockBroker を利用可能）。
    - 停止フラグ（data/stop_requested.flag）を検出して安全に停止する仕組みを実装。
    - 実行 PID を data/execution.pid に書き出す仕組み（ENGINE に PID ファイルパスを渡す）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明記。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了処理を実装。
    - プロセス優先度を起動時に "high" に設定する呼び出しを追加。
- 設定/環境管理
  - config.py: .env 自動読み込み機能を実装（プロジェクトルートの検出ロジックを含む）。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。
    - 複数の設定プロパティを Settings クラスとして提供（J-Quants / kabu / DB / 監視閾値等）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START、KABUSYS_DISABLE_AUTO_ENV_LOAD 等の環境変数対応。
    - env 値の検証（KABUSYS_ENV, LOG_LEVEL 等）。
  - config_setup.py: 対話式 .env 生成ウィザードを追加。
    - シークレット項目はマスク表示。設定保存時のテンプレート出力を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の値チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が存在する場合）。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティを追加（utils パッケージ）。
  - logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30世代保持）を設定。
    - ログレベル/ログディレクトリは引数・環境変数で上書き可能（LOG_LEVEL / LOG_DIR）。
    - すでにハンドラがある場合は二重設定を避けるため一旦クリア。
  - process_priority.py
    - psutil でプラットフォームを吸収してプロセス優先度 (high/normal/low) を設定。
    - POSIX (Linux/Mac) の nice、Windows の priority class に対応。失敗時は警告でフォールバック。
    - CPU affinity 設定ユーティリティも提供（set_cpu_affinity）。
- ポートフォリオ構築関連の純粋関数群（DB 非依存）。
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレーク実装。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。全スコアが0 の場合は等金額にフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を除外するフィルタ。既存保有のセクター比率計算とブロック処理を実装（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - lot_size 単位で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリング実装。
    - 価格欠損時のログとスキップ、安全弁として上限チェックあり。
- Paper Trading 検証ツールを追加。
  - tools.paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し PASS/FAIL を出力。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）。
    - P95 の計算、日付フィルタ（--from / --to）、閾値定義（稼働率 99%、fill 90%、send 95%、P95 200ms）を実装。
    - DB が存在しない場合のエラーメッセージを追加。
- research.factor_research モジュール（ファクター計算基盤）を追加（モジュール冒頭と一部実装）。
  - DuckDB 接続を受け取り、prices_daily / raw_financials を利用してファクターを計算する方針を明記。
  - モメンタム等の定数・設計方針を実装（calc_momentum の冒頭まで）。

Changed
- ログ出力は stdout を既定として使用するよう方針を統一（logging_setup）。
  - cron/task scheduler 等の出力リダイレクト運用を想定して stderr ではなく stdout を使用。
- .env の読み込み処理を堅牢化。
  - export プレフィックス対応、クォートされた値のバックスラッシュエスケープ対応、行末コメントの取り扱いを実装。
  - OS 環境変数を保護する protected オプションを導入（.env.local の override 時に利用）。
- 実行 & 監視起動時にプロセス優先度を "high" に設定するように変更（set_process_priority 呼び出しを追加）。

Fixed
- DB 初期化時に監視テーブルが存在しない可能性を考慮し、init_monitoring_db を呼び出すことで冪等に初期化するようにした（run_execution / run_monitoring）。

Security
- .env を生成するウィザードからの出力で明確に「.env を Git にコミットしないこと」を注意書きとして追加（config_setup）。

Notes / Migration
- 環境変数の自動読み込みはデフォルトで有効。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading 環境では監視 DB と本番 DB を分離しています。paper_trading 用 DB のパスは PAPER_TRADING_SQLITE_PATH で上書き可能です。
- MONITOR_POLL_INTERVAL は run_monitoring のポーリング間隔（秒）を制御します。不正な値（0 以下や非数）を指定した場合はデフォルト 60 秒にフォールバックします。
- run_execution/run_monitoring の停止フラグはプロジェクトルートの data/stop_requested.flag を判定します。運用上、外部でこのフラグを操作することで安全に停止できます。
- ロギング構成を変更したため、独自にハンドラを追加するスクリプトがある場合は二重ログ出力に注意してください。setup_logging() は既存ハンドラをクリアしてから設定します。

CLI / Usage Examples
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 実行・監視（プロダクション運用ではプロセスマネージャ等で起動してください）:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

その他
- 今後の課題として、portfolio.position_sizing の lot_size を銘柄別に対応する拡張や、価格欠損時のフォールバック（前日終値等）の導入がコメントとして残されています。
- research.factor_research はファクター計算の主要設計を含むが、実装は未完の箇所が存在します（calc_momentum が途中で切れているなど）。将来的に DuckDB を用いた完全実装を予定。

---
配布されたコードベースから推測して作成した変更履歴です。必要であればリリース日付やカテゴリの粒度を調整します。