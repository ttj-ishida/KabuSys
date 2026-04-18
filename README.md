README
======

以下はこのリポジトリ（KabuSys）の簡易ドキュメントです。日本株向け自動売買・リサーチ・モニタリングを目的とした Python パッケージで、実行用エンジン、監視、AI ニューススコアリング、ポートフォリオ構築、リサーチ用ユーティリティなどを含みます。

プロジェクト概要
--------------
KabuSys は日本株自動売買システム向けのライブラリ兼実行フレームワークです。本コードベースは以下の主要機能群を提供します。

- ExecutionEngine（発注エンジン）: 実際のブローカー接続またはペーパートレードのモックを用いた発注実行
- Monitoring（監視）: システム稼働状況・データ鮮度・注文挙動・リスクを定期監視し、kill flag による停止やアラート発行を支援
- AI モジュール: OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価（ai/news_nlp）や市場レジーム判定（ai/regime_detector）
- Portfolio（ポートフォリオ構築）: 候補選定・重み付け・ポジションサイズ計算・セクターキャップ等の純粋関数群
- Research（調査）: ファクター計算、forward returns、IC 計算など DuckDB を用いた分析関数群
- Tools: Paper Trading の検証レポート生成スクリプト等ユーティリティ

主な機能一覧
--------------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV により paper_trading / live / development を切替）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定関連 CLI
  - python -m kabusys.config_setup   : .env を対話式に生成・更新
  - python -m kabusys.validate_config: .env と config/*.yaml の事前検証（--strict あり）
- ツール
  - python -m kabusys.tools.paper_verification_report : ペーパートレード DB を用いた検証レポート生成
- AI API 統合
  - kabusys.ai.score_news: raw_news を OpenAI に送信して ai_scores テーブルへ保存
  - kabusys.ai.regime_detector: ETF + マクロニュースで市場レジームを判定して market_regime テーブルに格納
- ロギング・優先度設定・プロセス制御ユーティリティ
  - kabusys.utils.logging_setup.setup_logging
  - kabusys.utils.process_priority.set_process_priority / set_cpu_affinity

前提（依存）
------------
主な依存（バージョンは適宜調整してください）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を有効にする場合）
- sqlite3（標準ライブラリ）

セットアップ手順
----------------
1. リポジトリをチェックアウト / install
   - python 仮想環境を作成して依存を pip install してください（requirements.txt があればそれを使用）。

   例:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb psutil openai pyyaml

2. 初期環境変数 (.env) の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - これによりプロジェクトルートの .env を対話形式で生成できます。

   注意: .env は絶対に Git にコミットしないでください（スクリプトもその旨を表示します）。

3. 設定の検証
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合は --strict を付与

4. DB ディレクトリ/ログディレクトリの確認
   - デフォルトの SQLite / DuckDB / log のパスは .env の値や下記デフォルトに従います。起動時にディレクトリが自動作成されることが多いですが、パーミッション等を確認してください。

主要環境変数（代表）
-------------------
（.env に設定する代表的な値とデフォルト）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- OPENAI_API_KEY: OpenAI を利用する際に必要
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/
- KILL_FLAG_CLEAR_ON_START: 0 | 1（本番では 0 を推奨）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、monitoring 起動時に参照）

例（.env の抜粋）
-----------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

使い方（実行例）
----------------

1) ExecutionEngine の起動
- 本番/ペーパーを使い分ける:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - デバッグ: python -m kabusys.run_execution

- 動作のポイント:
  - paper_trading 環境では MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に発注ログを記録して本番 DB と分離します。
  - 起動時に data/execution.pid（デフォルト）へ PID ファイルを書きます。
  - data/stop_requested.flag が存在すると起動しない / 実行中に検出されると停止します。
  - 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合、kill.flag を自動クリアする挙動があります（本番では 0 推奨）。

2) Monitoring の起動
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL で監視ループ間隔（秒）を指定可能（デフォルト 60 秒）。
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は Settings.sqlite_path（デフォルト data/monitoring.db）へログを残します。
- 停止は data/stop_requested.flag を作成することで行えます（run_monitoring はこのファイルを検出してループを抜けます）。

3) .env / 設定検証
- 対話式作成: python -m kabusys.config_setup
- 検証: python -m kabusys.validate_config [--strict]

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db で DB パスを指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を使用

AI 機能の利用
--------------
- news_nlp.score_news と regime_detector.score_regime は OpenAI API キー（環境変数 OPENAI_API_KEY または引数）を必要とします。
- AI 呼び出しでのリトライ・エラーハンドリングが組み込まれていますが、API 使用量や料金には注意してください。
- AI モジュールは DuckDB のテーブル（raw_news / news_symbols / ai_scores / market_regime 等）を読み書きします。

停止・Kill Switch
-----------------
- ExecutionEngine の強制停止用フラグ: data/kill.flag を作成すると実行エンジンを停止するためのシグナルとして使えます（KillSwitch 実装）。
- run_execution / run_monitoring 系は data/stop_requested.flag を検出して安全に停止します。

ログ
----
- ログはデフォルトで logs/ 以下にアプリケーション毎に出力されます（例: logs/execution.log, logs/monitoring.log）。
- setup_logging() により標準出力（stdout）と日次ローテートされたファイルハンドラの両方を設定します。
- ログディレクトリは LOG_DIR 環境変数または setup_logging の引数で上書きできます。

ディレクトリ構成（主要ファイル）
------------------------------
以下はコードベース内の主要モジュールのツリー（src/kabusys 配下を抜粋）です。実際のファイル数はこれより多く存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py              # .env 対話型ウィザード
  - validate_config.py           # 設定検証スクリプト
  - run_execution.py             # ExecutionEngine 起動スクリプト
  - run_monitoring.py            # SystemMonitor ポーリング起動スクリプト
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
    - alert_manager.py
  - execution/                    # 発注関連（Engine, BrokerFactory, OrderManager 等）
    - ...
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
  - data/                         # 実行時に生成される想定のディレクトリ（DB, pid, flags 等）
  - config/                       # YAML 構成ファイル群（system_config.yaml など）

補足・運用上の注意
-----------------
- .env の自動読み込みはデフォルトで有効です。テスト時等に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番環境（KABUSYS_ENV=live）では kill flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨します。
- Monitoring は monitoring 用のテーブル（SQLite）を用いて動作します。monitoring は KABUSYS_ENV に関係なく Settings.sqlite_path（本番監視 DB）を使用しますので注意してください。
- Paper Trading は production DB と分離された PAPER_TRADING_SQLITE_PATH を使用します（テスト/検証での安全な切り離し）。

貢献・拡張
-----------
- new strategy / execution ブローカーの追加は execution パッケージに BrokerClientFactory を拡張してください。
- AI モデルの切替やプロンプト調整は ai/* 内の定数を編集して行います。
- CSV からのデータ取り込みやバックフィルは data/pipeline レイヤを拡張してください。

ライセンス・著作権
-----------------
- 本リポジトリに含まれるライセンス情報をリポジトリルート（LICENSE 等）で確認してください。

以上。必要であれば各モジュール（ExecutionEngine の起動方法、Execution の設定項目、DB スキーマ詳細、API 呼び出しの単体使い方等）について、より詳しい README の追加・分割を作成します。どの項目を詳細化したいか教えてください。