KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システムの内部モジュール群をまとめたものです。取引エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI（ニュースNLP / レジーム判定）などの機能を含みます。本 README はローカルセットアップ、主要スクリプトの使い方、構成の概観を説明します。

要点
----
- 実行スクリプト:
  - ExecutionEngine 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- 設定は .env（または環境変数）で管理。config_setup で対話式に生成可能。
- ログは logs/<app_name>.log（デフォルト）へ日次ローテートで出力。
- データベース既定:
  - DuckDB: data/kabusys.duckdb
  - SQLite（監視）: data/monitoring.db
  - Paper Trading SQLite（paper_trading のとき）: data/paper_trading.db

プロジェクト概要
----------------
KabuSys は以下の主要な役割を持つサブシステムを含みます。

- Execution (発注エンジン)
  - Broker クライアント（本番 / paper_trading 用の mock を切替）
  - ExecutionEngine / OrderManager / RiskManager / Reconciler 等
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - 監視ログは SQLite に永続化（monitoring_db.py）
  - Kill Switch 機構により自動停止（data/kill.flag）
- Portfolio
  - 候補選定、重み算出、ポジションサイズ計算、セクター上限処理
- Research
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索、IC 計算など
- AI
  - ニュースを LLM でスコアリングして ai_scores テーブルへ書き込み
  - 市場レジーム判定（MA と LLM センチメントの合成）
- ユーティリティ
  - ログ設定（logs 配下, 日次ローテート）
  - プロセス優先度設定（High/Normal/Low）
  - 環境読み込み / .env ウィザード / 設定検証

機能一覧
---------
- 実行環境ごとの DB 分離（paper_trading は専用 SQLite を使用）
- 設定ウィザード（.env の対話式作成）
- 設定検証 CLI（必須環境変数・DB パス・YAML ファイル等のチェック）
- システム監視: CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度確認
- リスク監視: ドローダウン通知、ポジション上限監視、リスクログ格納（dedup 機能）
- Kill Switch: 重大リスク発生時に data/kill.flag を出力して ExecutionEngine を停止
- Paper Trading 検証レポート生成（稼働率・成功率・レイテンシなど）
- ニュース NLP（OpenAI）連携による銘柄別センチメント得点化（ai_scores）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価の合成）

セットアップ手順（ローカル開発向け）
-------------------------------
1. リポジトリをクローンし Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - もし requirements.txt がある場合:
     - pip install -r requirements.txt
   - なければ最低限のライブラリを入れてください（例）:
     - pip install duckdb psutil openai

3. データ/ログ用ディレクトリ作成（通常は自動生成されますが事前作成しておくと安心）
   - mkdir -p data logs

4. .env を作成（推奨: ウィザードで作成）
   - python -m kabusys.config_setup
   - もしくは .env を手動で作成。必要な主な環境変数は下記参照。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります。

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution モード。development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使い記録先 DB は PAPER_TRADING_SQLITE_PATH
- OPENAI_API_KEY: OpenAI API 利用時に必要（AI モジュール / レジーム判定 / ニュース）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定動作（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイルディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（"1" でクリア）

サンプル .env（最小例）
---------------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

使い方（主要コマンド）
---------------------
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（デーモン的に起動）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は paper_trading DB に記録し、本番 DB と分離されます。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60）
  - Monitoring は環境に依らず sqlite_path（本番監視 DB）を使用します（設計上の仕様）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH を優先的に参照

停止・制御
---------
- 停止フラグ（手動で監視ループやエンジンを停止する）
  - 停止要求ファイル: data/stop_requested.flag
    - run_monitoring / run_execution はこのファイルの存在を見てループを終了します。
  - Kill Switch: data/kill.flag
    - Monitoring の KillSwitch が自動的に書き込むことで ExecutionEngine に停止を促します。
    - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動でクリアされます（本番では注意）。

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一。
- デフォルト: logs/<app_name>.log を日次ローテート（30日分保持）
- コンソール出力は stdout を使用

主要ディレクトリ構成（src/kabusys の抜粋）
-----------------------------------------
- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度設定ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル定義 / API）
    - system_monitor.py       — システム監視（CPU / メモリ / データ鮮度）
    - risk_monitor.py         — ドローダウン / ポジション数監視
    - trade_monitor.py        — (注文関連監視: ソース内に実装)
    - monitoring_engine.py    — 各 Monitor を束ねる
    - kill_switch.py          — kill.flag 書込みロジック
    - alert_manager.py        — (通知管理: LINE など、実装あり)
  - execution/
    - execution_engine.py     — 発注エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 連携）
    - regime_detector.py      — レジーム判定
  - tools/
    - paper_verification_report.py

補足 / 運用上の注意
------------------
- 本番運用時は KABUSYS_ENV=live を設定し、各設定値（API トークン・LINE 通知先等）を慎重に管理してください。validate_config は live に関する追加警告チェックを行います。
- OpenAI 等外部 API 呼び出しは失敗時にフェイルセーフで継続する設計（デフォルトでスコア=0 などにフォールバック）。しかし本番では API キーやレート制限に注意してください。
- Paper Trading モードは本番発注とは独立しており、記録先 DB が分離されています（PAPER_TRADING_SQLITE_PATH）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみ有効になります（ログハンドラ生成時に警告）。

開発 / テスト
--------------
- モジュール単体のテストや、MonitoringEngine.run_once を使った単体呼び出しで各 Monitor を検証できます。
- AI モジュール（news_nlp / regime_detector）は外部 API 呼び出し部分を差し替え可能（テスト用に _call_openai_api をモックするなど）。

最後に
------
この README はコードベースの主要な利用方法・設定項目・構成を簡潔にまとめたものです。機能拡張や詳細な設計（PortfolioConstruction.md、StrategyModel.md 等の設計文書）が別途存在する想定です。運用上の重要項目（Kill Switch、DB の分離、paper_trading の挙動など）を特に注意して扱ってください。ご不明点があれば個別に質問してください。