KabuSys
=======

日本株向けの自動売買 / リサーチ基盤ライブラリ群です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ファクター計算・リサーチ、AI を使ったニュース解析などの主要コンポーネントを含みます。

概要
----
KabuSys は以下の目的を持つコンポーネント群で構成されています。

- 発注エンジン（ExecutionEngine）：ブローカークライアントを介した注文管理、リスク管理、リコンシリエーションなどを行います。paper_trading モードでは MockBrokerClient を使用し、本番 DB と分離された paper_trading DB（data/paper_trading.db など）へ記録します。
- 監視（Monitoring）：システム状態や注文状況、リスク指標を定期的にポーリングして監視し、必要に応じて Kill Switch（data/kill.flag）を発行します。
- ポートフォリオ構築（portfolio）：候補銘柄選定、重み計算、ポジションサイズ計算、セクター制限などを純粋関数群として提供します。
- リサーチ（research）：DuckDB 上の時系列データ（prices_daily, raw_financials 等）からファクターや将来リターン、IC、統計サマリを計算します。
- AI モジュール（ai）：OpenAI を用いたニュースのセンチメント評価や市場レジーム判定を行い、結果を DuckDB に書き込みます。
- ユーティリティ（utils）：ログ設定、プロセス優先度設定、環境変数ロード等の共通処理。

主な機能一覧
--------------
- 環境設定ウィザード（python -m kabusys.config_setup）による .env 作成支援
- 設定検証 CLI（python -m kabusys.validate_config）で起動前のチェック
- ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い DB を分離
- Monitoring の起動スクリプト（python -m kabusys.run_monitoring）
  - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
  - 期間指定 (--from, --to) や DB パス指定 (--db) に対応
- DuckDB を使ったファクター計算（momentum / volatility / value 等）
- OpenAI 経由のニュース NLP スコアリング（ai.news_nlp）およびレジーム判定（ai.regime_detector）
- ログ出力の統合（logs/<app_name>.log、日次ローテーション）
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
- 監視用 SQLite DB（monitoring_db）による永続化

前提 / 必要なパッケージ
---------------------
推奨 Python バージョン: 3.9+（実装は型ヒントで近年の仕様を想定しています）

主な外部依存:
- duckdb
- psutil
- openai（AI 機能を使う場合）
- sqlite3（標準ライブラリ）
- PyYAML（config ファイル検証は任意。未インストール時は YAML のパース検証をスキップ）

pip 等でインストールする例（requirements.txt が無い場合の目安）:
pip install duckdb psutil openai pyyaml

注意: 実際の運用環境では依存バージョンを固定した requirements.txt を用意することを推奨します。

セットアップ手順
----------------

1. リポジトリをクローン / 展開

2. Python 環境を準備（仮想環境推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. パッケージをインストール
   pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザードを実行:
     python -m kabusys.config_setup
   - または .env.example を参照して手動で作成
   主要な環境変数例:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development   # development | paper_trading | live
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     OPENAI_API_KEY=sk-xxxx    # AI 機能を使う場合
     LOG_LEVEL=INFO

   セキュリティ: .env は絶対にソース管理にコミットしないでください。

5. 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   厳格モード（警告も失敗扱い）:
   python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------

- ExecutionEngine 起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV に依存
  - 起動:
    python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID が書き込まれます（設定に依存）。

- Monitoring 起動
  - 起動:
    python -m kabusys.run_monitoring
  - 設定:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。例: export MONITOR_POLL_INTERVAL=30
    - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境に依存しません）。
  - 停止:
    - プロセスに対する KeyboardInterrupt、またはプロジェクトルートの data/stop_requested.flag を作成するとループを抜けて終了します。

- Paper Trading 検証レポート
  - 実行:
    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB パスは --db、環境変数 PAPER_TRADING_SQLITE_PATH、デフォルトの順で解決されます。

- AI 関連
  - ai.news_nlp.score_news / ai.regime_detector.score_regime を呼ぶか、該当スクリプトを組み込み
  - OPENAI_API_KEY が必要（引数で渡すことも可能）
  - 実行中の API エラーはリトライやフェイルセーフ（デフォルトスコア）で処理される実装になっていますが、APIキーの設定と利用制限には注意してください。

環境変数（主なもの）
-------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（実行時に kill.flag を自動クリアするか。1=クリア、0=クリアしない。生産環境では 0 推奨）

監視 / 停止フロー
-----------------
- Kill Switch: kabusys.monitoring.kill_switch が risk_monitor 等の結果を評価し、必要なら data/kill.flag を書き込みます。ExecutionEngine はこの kill.flag の存在を検出して安全に停止します。
- stop_requested.flag（data/stop_requested.flag）: run_monitoring/run_execution の外部停止トリガーとして使用されます（起動スクリプトが存在を検出して終了します）。
- PID ファイル: data/execution.pid に実行中の PID を書き込みます（Engine 側で管理）。

ログ
----
- 共通のログ設定ユーティリティ（kabusys.utils.logging_setup）を使用して、コンソール出力（stdout）と日次ローテートファイル出力（logs/<app_name>.log）を行います。
- デフォルトログディレクトリ: logs/
- LOG_LEVEL 環境変数でログレベルを制御可能。

ディレクトリ構成（抜粋）
---------------------
以下は主要なソースツリー（実際のファイル数は増える可能性があります）。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数/.env ロード、Settings
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 起動前設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        # （実装あり）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        # （実装あり）
  - utils/
    - logging_setup.py
    - process_priority.py

- data/                      # デフォルト DB / flag ファイル置場（実行時自動作成される）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - kill.flag
  - stop_requested.flag
  - execution.pid

設計上の注意点 / 運用上のヒント
-------------------------------
- .env ファイルは機密情報を含むため、絶対に Git 等へコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすること、LINE 通知（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の設定を確認することを強く推奨します（validate_config で警告が出ます）。
- AI 機能は OpenAI API を利用します。API キーと利用量に注意してください。APIの一時エラーは内部でリトライされますが、失敗時はフェイルセーフ（スコア 0 など）で継続する実装です。
- プロセス優先度の設定（set_process_priority）は OS 権限の制約を受けます。PermissionError / AccessDenied の場合は警告が出て処理は継続します。
- DuckDB / SQLite のファイルパスの親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、アクセス権やファイルシステムの状態には注意してください。
- ログディレクトリ作成に失敗した場合も標準出力のみで動作します（警告が出ます）。

トラブルシューティング
---------------------
- 設定検証でエラーが出る場合: .env の必須項目 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等) を確認してください。
- OpenAI 関連で失敗する場合: OPENAI_API_KEY の値、ネットワーク、APIレート制限を確認。ログにリトライ情報が残ります。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB に対する軽微なカラム追加（例: latency_ms, peak_value）を行います。大きなスキーマ変更時はバックアップを推奨します。

ライセンス / バージョン
-----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

最後に
-----
この README はコードベースからの抜粋説明です。実際の運用や拡張時は各モジュールの docstring（各 .py の冒頭）や関数コメントを参照してください。追加のセットアップ手順（サービス化、systemd / supervisor 設定、監視・アラートの外部連携等）は運用環境に応じて別途整備してください。