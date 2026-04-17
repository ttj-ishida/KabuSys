# KabuSys

日本株向け自動売買・リサーチ基盤（軽量プロトタイプ）

このリポジトリは「KabuSys」と呼ばれる日本株の自動売買／リサーチ基盤の一部実装です。
主に以下の機能を持つモジュール群を含みます（監視／発注／ポートフォリオ構築／ファクター計算／AI ニュース評価 等）。

注意: README はソースコードの構成と起動手順を簡潔にまとめたものです。実運用前に必ず設定検証とテストを行ってください。

---

目次
- プロジェクト概要
- 主な機能
- 前提条件（依存パッケージ・Python バージョン）
- セットアップ手順
- 環境変数（主要項目）
- 実行方法（各コンポーネント）
- 使い方の例
- ファイル／ディレクトリ構成（抜粋）
- 注意点・運用メモ

---

プロジェクト概要
- 日本株自動売買システムのコア機能（発注エンジン、監視、リスク監視、ポートフォリオ構築、リサーチ、AI によるニュースセンチメント等）を提供するライブラリ／実行スクリプト群。
- 設定は .env（自動ロードあり）および config/*.yaml で管理。paper_trading（ペーパートレード）モードでは発注はモック化され、本番データベースと分離して動作するよう設計されています。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードの切替、ブローカークライアントの抽象化、Execution エンジン起動
- Monitoring（run_monitoring.py / MonitoringEngine）
  - SystemMonitor（プロセス／CPU／メモリ／ディスク／株価データ鮮度）
  - TradeMonitor（滞留注文、約定異常価格）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件達成で data/kill.flag を書き込み Execution を停止）
- 設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- ポートフォリオ構築ユーティリティ（portfolio モジュール）
  - 候補選定、等金額／スコア加重、セクター制限、ポジションサイズ計算 等
- リサーチ（research モジュール）
  - ファクター計算（momentum / volatility / value）、将来リターン、IC、統計サマリー
- AI 関連（ai モジュール）
  - news_nlp: OpenAI を用いたニュースセンチメント集約・ai_scores 書き込み
  - regime_detector: ETF 200日 MA とマクロニュースから市場レジーム判定

前提条件（推奨）
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合）
- 標準ライブラリ: sqlite3, logging 等

例:
pip install duckdb psutil openai pyyaml

セットアップ手順（ローカル開発用）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参考に）。
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（news_nlp / regime_detector を使う場合）
   - 自動ロードは Settings がプロジェクトルートを検出できる場合に .env/.env.local を読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading: MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（0/1）

実行方法（代表例）
- 環境ウィザード（.env作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB に書き込みます。
- 監視ループ
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視プロセスは .data 停止フラグ（data/stop_requested.flag）を検知するとループを終了します。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI ニューススコアリング（プログラムから呼ぶ）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY を環境変数で指定するか、api_key 引数で渡します。
- レジーム判定（プログラムから呼ぶ）
  - ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

使い方のポイント / 運用メモ
- paper_trading モードは本番 DB と完全分離する設計です。ペーパートレード時は PAPER_TRADING_SQLITE_PATH を確認してください。
- kill.flag / stop_requested.flag:
  - kill.flag (data/kill.flag): Kill Switch による Execution 停止要求（KillSwitch が書き込む）。
  - stop_requested.flag (data/stop_requested.flag): run_* スクリプトが外部停止要求を検知するためのファイル（存在するとループを抜けます）。
- PID ファイル:
  - Execution 起動時に execution.pid（デフォルト data/execution.pid）を使用／生成します。SystemMonitor はこの PID ファイルの存在とプロセス存続をチェックします。
- プロセス優先度設定:
  - run_execution/run_monitoring は起動時に set_process_priority("high") を呼びます。権限がない場合は警告だけ出ます。
- OpenAI 呼び出し:
  - news_nlp と regime_detector は API エラー（429 / ネットワーク / 5xx）に対してリトライを実装しています。APIキーの管理には注意してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対する簡易マイグレーション（カラム追加）を行います。大規模なスキーマ変更には注意。

ディレクトリ構成（src/kabusys 以下の抜粋）
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py  (未表示: 実装参照)
- execution/               — 発注関連コンポーネント（OrderRepository 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py
- data/ (実行時に利用されるファイル群: monitoring DB / duckdb / pid / flags 等)

（注）上記はリポジトリ内の主要ファイルを抜粋した一覧です。実際のツリーはソースを参照してください。

トラブルシューティング（よくある注意点）
- 環境変数の未設定で起動時に ValueError が発生することがあります。validate_config で事前チェックしてください。
- psutil によるプロセス優先度 / CPU affinity の設定は OS 権限に依存します。権限不足の場合は警告を出してスキップします。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合、validate_config が警告しますが実行時に自動作成されることもあります。
- OpenAI の API 使用はコストとレート制限に注意してください。API 呼び出しは retry ロジックを持ちますが、失敗時はフェイルセーフ（スコア=0 等）で継続する設計です。

最後に
- この README はリポジトリ内のコードから抽出した主要情報をまとめたものです。各コンポーネントの詳細な使用法やパラメータは該当 Python モジュールの docstring / コメントを参照してください。
- 実運用前に必ずローカルテスト・ペーパートレードで動作確認を行い、安全対策（kill switch 設定、LINE 通知設定など）を整えてください。

---