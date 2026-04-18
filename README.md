README
======

概要
----
KabuSys は日本株自動売買システム（バックテスト／ペーパートレード／本番運用を想定）を構成する Python パッケージです。  
本リポジトリは以下の主要機能群を提供します。

- 注文実行エンジン（ExecutionEngine）とブローカー抽象化（本番 / ペーパートレード切替）
- 監視コンポーネント（System / Trade / Risk のチェック、Kill Switch）
- ポートフォリオ構築・ポジションサイズ計算・リスク調整の純粋関数群
- リサーチ用のファクター計算・特徴量探索
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading 検証レポート 等）
- ロギング設定・プロセス優先度ユーティリティなどのユーティリティ群

主な機能一覧
--------------
- 環境設定ウィザード: python -m kabusys.config_setup により .env を対話的に作成
- 設定検証 CLI: python -m kabusys.validate_config（--strict オプションあり）
- 注文実行起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録
- 監視起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を参照（環境に依らず）
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report
  - 期間指定 --from / --to によりフィルタ可能
- AI モジュール:
  - kabusys.ai.news_nlp.score_news(...) — ニュースを集約して OpenAI に送信、ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime(...) — マクロセンチメント＋ETF MA200 乖離でレジーム判定
- ポートフォリオ構築:
  - 候補選定・等重 / スコア重み計算・ポジションサイズ計算・セクターキャップ適用など（純粋関数）

前提（依存パッケージ）
--------------------
主要な実行時依存:
- Python 3.9+（型ヒントや機能に依存）
- duckdb
- psutil
- openai（AI 機能を利用する場合）
- sqlite3（標準ライブラリ）
- PyYAML（config/*.yaml の構文チェック時。必須ではない）

（requirements.txt はプロジェクトに応じて生成してください）

環境変数（主要）
----------------
主要な設定値は .env に記載します。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須（稼働に必要な主要項目）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 重要なもの
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- LOG_DIR: ログファイル保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を利用する場合必須
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant, partial, never, reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag を自動クリアするか（0/1。production では 0 推奨）

その他運用フラグ
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- KILL_FLAG_PATH / PID_FILE_PATH: Settings 経由で変更可能（デフォルト data/kill.flag, data/execution.pid）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を準備
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （開発用）pip install PyYAML

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話に従って入力し .env を生成します
   - 既存の OS 環境変数が優先されます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定検証（必須項目やファイルの存在チェック）
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合: python -m kabusys.validate_config --strict

5. 必要なディレクトリの作成（ログや data ディレクトリ）
   - mkdir -p data logs

使い方（運用・開発向け）
----------------------

起動（Execution エンジン）
- 本番 / ペーパートレードを切り替えるには KABUSYS_ENV を変更します
- 実行:
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在する場合は起動しません
  - 起動中は data/execution.pid が作成されます（Settings.pid_file_path で変更可）
  - 停止は data/stop_requested.flag を作成するか、実行中に KeyboardInterrupt（Ctrl+C）

監視プロセス起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に sqlite_path（data/monitoring.db）を使用してログを記録
  - 停止は data/stop_requested.flag を作成、または Ctrl+C

Kill Switch（自動停止）
- RiskMonitor 等の判定により KillSwitch がトリガーされると、data/kill.flag に理由を書き込みます
- ExecutionEngine は起動時や実行中に kill.flag を検出すると安全に停止または起動拒否します
- Settings.kill_flag_clear_on_start = 1 の場合は起動時に kill.flag を自動クリアしますが、production では 0 を推奨

ログ
- setup_logging がログディレクトリ（デフォルト logs/）に <app_name>.log を日次ローテーションで出力します
- コンソール出力は stdout に書かれます（cron 等でのリダイレクトに配慮）

ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 稼働率・約定/送信率・レイテンシ等を集計し PASS/FAIL を判定します

API / ライブラリとしての利用
- 設定取得: from kabusys.config import settings
- ポートフォリオ計算:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- 研究用:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- AI:
  - from kabusys.ai import score_news
  - OpenAI API キーは OPENAI_API_KEY 環境変数か引数で渡す

ディレクトリ構成（概要）
--------------------
以下はソースツリー（src/kabusys）にある主要ファイル／パッケージの抜粋です。実際のツリーはリポジトリ内を参照してください。

- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数・Settings 管理、.env 自動ロード
  - config_setup.py            # .env 対話式ウィザード CLI
  - validate_config.py         # 設定検証 CLI
  - run_execution.py           # ExecutionEngine 起動スクリプト
  - run_monitoring.py          # SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (※実コードに依存)
  - execution/                  # ExecutionEngine 関連（ブローカー工場・注文管理等）
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                       # 実行時に作成されることを想定: monitoring DB / paper_trading DB / pid / flags / logs など

開発メモ / 運用上の注意
---------------------
- .env は絶対に Git にコミットしないでください（config_setup でも警告を出します）。
- KABUSYS_ENV=live のときは特に LINE 通知設定や Kill Switch 設定を慎重に確認してください。
- run_monitoring は監視用 DB（SQLITE_PATH）へ常に書き込みます。テスト時に本番 DB を汚したくない場合は設定を切り替えてください。
- OpenAI を使った処理は API レート制限・エラー耐性（リトライ）を組み込んでいますが、API キーの管理とコストに注意してください。
- process_priority.set_process_priority を呼んで高優先度にするため、実行環境の権限（nice 設定等）に注意が必要です。

付録: よく使うコマンド例
----------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

質問・拡張
---------
- 追加の CLI、詳細な ExecutionEngine の運用手順やブローカープラグインの実装方法、CI 用のモック設定などが必要でしたら、目的に応じた README の追加節を作成します。必要な情報（使用するブローカーの仕様、CI の要件など）を教えてください。