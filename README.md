KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買システムのコンポーネント群です。本リポジトリには以下の主要領域が含まれます:

- Execution: 発注エンジン（ExecutionEngine）と発注周りのユーティリティ
- Monitoring: システム監視・リスク監視・Kill Switch 等の監視基盤
- Research / Portfolio: ファクター計算、特徴量解析、ポートフォリオ構築（候補選定、配分、株数決定）
- AI: ニュース NLP（OpenAI でのセンチメント評価）や市場レジーム判定
- Tools: ペーパートレード検証レポート作成などのユーティリティスクリプト
- Utils / Config: ロギング設定、プロセス優先度制御、環境設定ウィザード／検証

この README はコードベースの主要な使い方・セットアップ方法・ディレクトリ構成を説明します。

主な機能
--------
- ExecutionEngine の起動（本番 / ペーパートレード切替）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を用い、本番 DB と分離して data/paper_trading.db に記録
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
  - CPU / メモリ / ディスク / プロセス死活・データ鮮度監視
  - ドローダウンやポジション上限の検知、Kill Switch 発動（data/kill.flag）
  - 監視データは SQLite（デフォルト data/monitoring.db）に永続化
- Research
  - ファクター計算（モメンタム・バリュー・ボラティリティなど）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計要約
- Portfolio construction
  - 候補選定、等金額・スコア加重配分、セクター上限、レジーム乗数、単元株丸めを考慮した株数計算
- AI（OpenAI）
  - ニュースを LLM でセンチメント評価して ai_scores に保存
  - マクロニュースを基に市場レジーム判定（regime_detector）
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成
- 設定管理
  - 対話式 .env 作成ツール（python -m kabusys.config_setup）
  - 設定検証ツール（python -m kabusys.validate_config）

前提（推奨）
------------
- Python 3.10+
- 開発環境: 仮想環境（venv, pipx, poetry 等）
- 必須外部パッケージ（実行する機能に依存）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定 YAML の検証を有効にする場合）
  - （その他、requirements.txt がある場合はそちらを参照してください）

セットアップ手順
----------------
1. リポジトリをクローンし仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトがパッケージ化されていれば）pip install -e .

3. .env を生成・編集（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他（デフォルトを使えるものも多い）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - DUCKDB_PATH: data/kabusys.duckdb（分析用）
     - SQLITE_PATH: data/monitoring.db（監視 DB）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（紙トレード用）
     - OPENAI_API_KEY: OpenAI を使う場合
     - LOG_LEVEL, LOG_DIR, など

4. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit 1）

基本的な使い方
--------------
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で切替:
    - paper_trading: MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - live / development: 実ブローカークライアント（設定に依存）
  - 停止方法:
    - 上位プロセスの割り込み（Ctrl+C）
    - 監視側が Kill Switch を発動すると data/kill.flag が書かれ ExecutionEngine 停止のトリガーになる
    - run_execution は data/stop_requested.flag の存在も監視して起動／停止判断を行う

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔の調整:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き（デフォルト 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用（環境に関係なく）
  - 停止方法:
    - data/stop_requested.flag を作成すると監視ループが終了する

- ロギング
  - 各アプリケーションは kabusys.utils.logging_setup.setup_logging を使用
  - デフォルトログディレクトリ: logs/
  - 環境変数 LOG_DIR で変更可能
  - ログレベルは環境変数 LOG_LEVEL（または .env）で設定

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で指定可能）

運用に関する注意
----------------
- Kill Switch と Stop Flag:
  - KillSwitch（リスク条件達成時）は data/kill.flag に理由テキストを書き込み、ExecutionEngine の停止を促します。
  - run_* スクリプトは data/stop_requested.flag の存在を確認して終了します（運用側で停止指示を出す用途）。
- データベース:
  - 監視用 DB（SQLite）は init_monitoring_db によりスキーマを冪等に作成します。既存スキーマへのマイグレーション（列追加）にも対応する箇所があります。
  - Paper Trading は本番 DB と分離して data/paper_trading.db に記録することが推奨されています。
- OpenAI 利用:
  - NEWS NLP や regime_detector は OPENAI_API_KEY を必要とします。API 呼び出しはリトライとフォールバック（失敗時はスコア 0 等）を備えていますが、料金・レートに注意して運用してください。
- プロセス優先度:
  - 実行開始時にプロセス優先度を高く設定する仕組み（psutil を利用）があります。ただしアクセス権限やプラットフォーム制限で設定ができない場合は警告が出ます。

主要ファイル / ディレクトリ構成
------------------------------
（src/kabusys 配下の主な構成を抜粋）

- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト
- config.py                — Settings クラス（環境変数/.env 読み込みと提供）
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 起動前設定チェック CLI

- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）

- monitoring/
  - monitoring_db.py       — monitoring SQLite の初期化・永続化 API（MonitoringDB）
  - system_monitor.py      — システム状態・データ鮮度監視
  - risk_monitor.py        — ドローダウン・ポジション上限チェック
  - kill_switch.py         — kill.flag 書き込みロジック
  - monitoring_engine.py   — 各 Monitor を束ねる（ポーリング実行）
  - alert_manager.py       — （存在する想定）アラート配信管理

- execution/
  - execution_engine.py    — ExecutionEngine（起動ロジック・セッション）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - portfolio_builder.py   — 候補選定・配分関数
  - position_sizing.py     — 株数決定・集約キャップロジック
  - risk_adjustment.py     — セクターキャップ・レジーム乗数

- research/
  - factor_research.py     — モメンタム/バリュー/ボラティリティ等の計算（DuckDB）
  - feature_exploration.py — 将来リターン/IC/統計サマリ

- data/                    — 実行時に使用するファイル群（デフォルト）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - kill.flag / stop_requested.flag

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

ユーティリティ
--------------
- kabusys.utils.logging_setup.setup_logging(app_name, log_dir, level)
  - 日次ローテーションのファイルハンドラと stdout のハンドラを設定
- kabusys.utils.process_priority.set_process_priority(level)
  - Windows/Linux の差分を吸収してプロセス優先度を設定

よく使うコマンド例
------------------
- .env を作る（対話式）
  - python -m kabusys.config_setup

- 設定を検証する
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジンを起動する
  - python -m kabusys.run_execution

- 監視プロセスを起動する
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 指定 DB を使う: python -m kabusys.tools.paper_verification_report --db /path/to/db

補足・開発者向けメモ
-------------------
- .env は決して Git にコミットしないでください（config_setup.py のヘッダにも警告あり）。
- DuckDB の接続は多数の research モジュールで前提になっています。データスキーマ（prices_daily, raw_financials, raw_news 等）に合うデータを投入してから解析してください。
- OpenAI を利用するコードはリトライ・フォールバックの保護がありますが、API キーとコスト管理を忘れずに。
- 監視 DB のスキーマは init_monitoring_db() で冪等に作成され、古い DB への簡易マイグレーションも一部実装されています。

ライセンス・貢献
----------------
本リポジトリのライセンスや貢献ガイドラインはここでは省略しています。必要に応じてプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

--- 
必要であれば、README に含めるコマンド実行例や .env の具体的なテンプレート（秘匿値はマスク）を追記します。どの情報をより詳しく載せたいか教えてください。