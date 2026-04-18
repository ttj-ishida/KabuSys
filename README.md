README
=====

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームのコードベースです。  
このリポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）: 発注・約定処理・リスク制御を行うランタイム
- 監視（Monitoring）: システム状態、注文状況、リスク監視、Kill Switch を実装したポーリング監視
- ポートフォリオ構築ロジック: 候補選定、重み付け、ポジションサイズ算出、セクター上限等
- リサーチ / ファクター計算: DuckDB を用いたファクター計算・特徴量探索
- AI 補助: ニュースの NLP スコアリング（OpenAI）と市場レジーム判定
- 運用ユーティリティ: .env 対話式セットアップ、設定検証、ペーパートレード検証レポート等

主な特徴
--------
- 環境変数 + .env による設定管理（自動ロード。必要なら無効化可）
- 実行/監視それぞれのプロセス優先度を high に設定するランタイム処理
- DuckDB（分析用）と SQLite（監視/発注ログ）を併用
- Paper trading モード時は発注をモック化し、本番 DB と分離
- OpenAI を利用したニュースセンチメント（バッチ処理、エラーハンドリング・リトライ実装）
- Kill Switch（フラグファイル）で安全に ExecutionEngine を停止可能

必要要件（主なライブラリ）
-------------------------
- Python 3.8+
- duckdb
- psutil
- openai
- （オプション）PyYAML — validate_config が config/*.yaml を検証するときに使用

セットアップ手順
----------------

1. リポジトリをクローンしてワークディレクトリに入る

   - 例:
     python -m pip install --upgrade pip
     pip install -r requirements.txt
     （requirements.txt が無い場合は上の必須ライブラリを個別にインストール）

2. .env を生成（対話式ウィザード）

   - 実行:
     python -m kabusys.config_setup

   - 画面の指示に従い J-Quants トークン、kabuAPI パスワード、DB パス、KABUSYS_ENV 等を入力します。
   - 生成される .env はデフォルトでプロジェクトルートの .env に保存されます。
   - 注意: .env は絶対に Git にコミットしないでください。

3. 設定検証

   - 実行:
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict  # 警告も失敗扱いにする

   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

4. データディレクトリ等の準備（任意）

   - デフォルト DB/ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

   - 必要なら事前に directories を作成するか、プログラム起動時に自動生成されます。

主要な環境変数（代表）
--------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring)（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 実行時に kill.flag を自動クリアするか (0/1)

自動 .env ロード
----------------
- .env 自動ロードはデフォルトで有効です（プロジェクトルートに .env/.env.local があると読み込みます）。  
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

実行方法（CLI）
---------------

- Execution（エンジン起動）
  - 本番/ペーパーを区別して起動:
    python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録する
    - 起動前に data/stop_requested.flag が存在すると起動せず終了
    - 起動中は data/execution.pid を書き、停止フラグ検知で安全停止

- Monitoring（監視ループ起動）
  - 実行:
    python -m kabusys.run_monitoring
  - オプション・挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書き可能（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルに記録する
    - data/stop_requested.flag を検知するとループを終了

- 設定ウィザード（.env 生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）扱い

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定

- AI 機能（Python API）
  - OpenAI を使ったニューススコアリング:
    from kabusys.ai import score_news
    import duckdb
    from datetime import date
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 11), api_key="sk-...")
  - 市場レジーム判定は kabusys.ai.regime_detector.score_regime を直接呼び出して使用できます（DuckDB 接続と api_key を渡す）
  - これらは内部で OpenAI クライアントを生成するため OPENAI_API_KEY（または api_key 引数）を用意してください

運用上のポイント
----------------
- 監視/実行はデーモン化して systemd / Supervisor 等で管理するのがよいです。ログは logs/<app>.log に日次ローテーションで保存されます。
- Kill Switch:
  - RiskMonitor 等から KillSwitch.evaluate() により data/kill.flag が書き込まれると ExecutionEngine 側で停止シグナルとして扱われる仕組みです。
  - kill.flag の既存は上書きされません（冪等）。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされますが、本番では 0 を推奨します。
- 停止フラグ:
  - プロセスを外部から即時停止させたい場合は data/stop_requested.flag を作成してください。run_monitoring/run_execution はこれを検知して安全に終了します。
- Paper trading は本番 DB と分離されるため、挙動確認用に推奨されます。

ディレクトリ構成（抜粋）
-----------------------
以下は主要ファイル/モジュールのツリー（src/kabusys 内）です。細かいサブモジュールは省略しています。

- src/kabusys/
  - __init__.py
  - config.py                   # 環境変数/.env ロードと Settings クラス
  - config_setup.py             # .env 対話式ウィザード
  - validate_config.py          # 設定検証 CLI
  - run_execution.py            # ExecutionEngine 起動スクリプト
  - run_monitoring.py           # Monitoring 起動スクリプト
  - utils/
    - logging_setup.py          # ログ設定ユーティリティ
    - process_priority.py       # プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py          # SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                # ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        # 市場レジーム判定（OpenAI + ETF MA）
  - tools/
    - paper_verification_report.py

よくある質問（FAQ）
-----------------
Q. 監視が別 DB を使うように見えますが、paper_trading モードではどうなりますか？  
A. Monitoring は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。Execution は KABUSYS_ENV=paper_trading の場合 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使い、本番 DB と分離されます。

Q. .env を編集したらアプリは自動で再読み込みしますか？  
A. 既に起動しているプロセスは環境変数の変更を自動反映しません。変更時はプロセス再起動が必要です。

Q. OpenAI API のキーをコードに埋める必要がありますか？  
A. 可能なら環境変数 OPENAI_API_KEY を .env に設定してください。呼び出し時に api_key 引数で渡すこともできます。

追加メモ
--------
- validate_config は PyYAML がインストールされていない場合、config/*.yaml の内容検証をスキップします（警告）。
- logging_setup は logs ディレクトリが作れない場合はファイル出力をスキップしてコンソール出力のみで継続します。
- 各モジュールの詳細な仕様はソース内の docstring とコメントを参照してください。

以上。必要であれば README にコマンド例や .env.example の具体例を追加します。どの程度の詳細（例: サンプル .env 中身）を追記するか教えてください。