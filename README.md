README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のミニマル実装です。  
主な目的は、戦略の信号生成・ポートフォリオ構築・発注エンジン（本番/ペーパートレード分離）・監視・レポート・研究ツールを提供することです。  
このリポジトリ内のモジュールは可能な限り副作用を抑え、設定は環境変数（.env）で管理します。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（分離された SQLite DB）をサポート
  - RiskManager / OrderManager / Reconciler 等を統合
- Monitoring（監視）
  - CPU / メモリ / ディスク / データ鮮度 / プロセス生存をポーリングしてログ保存
  - Kill Switch（ドローダウンやポジション上限で停止フラグを出す）
  - AlertManager 経由で通知（LINE 等の実装は設定に依存）
- Portfolio construction
  - 候補選定、重み計算、ポジションサイズ計算、セクター制約適用など純粋関数で実装
- Research
  - DuckDB を使ったファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計測、IC 計算、特徴量統計
- AI ユーティリティ
  - ニュース NLP（OpenAI）を用いた銘柄センチメント集計（ai_scores テーブルへ）
  - 市場レジーム判定（MA200 とマクロニュースの LLM センチメントを合成）
- 運用ユーティリティ
  - .env 対話式設定ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - Paper Trading 検証レポート出力ツール

前提・依存
-----------
- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の検証に使用／任意）
- DB: DuckDB（分析用）、SQLite（監視・ペーパートレードログ等）
- 環境変数管理は .env を利用（自動読み込みあり。無効化可）

セットアップ手順
----------------
1. リポジトリをクローンして移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

3. 必要パッケージをインストール
   - （リポジトリに requirements.txt がなければ下記）
   - pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD      （必須）
   - 主なオプション / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live  （default: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - KILL_FLAG_CLEAR_ON_START: 0 | 1  （本番では 0 推奨）
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い:
     - python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - live: 本番（外部ブローカに接続。設定に注意）
  - エンジンは data/execution.pid を作成し、停止は data/stop_requested.flag を作成することでも行える

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用（環境にかかわらず本番 sqlite_path を使用）
  - 停止は data/stop_requested.flag による検知で行う

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。別パス指定可: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（OpenAI）
  - ニュースセンチメント集計:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
    - 実行時には OPENAI_API_KEY 環境変数または api_key 引数が必要
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
    - 同様に OpenAI API キーが必要。API エラー時はフェイルセーフとして中立スコア等で継続

ログ
----
- ログはデフォルトで stdout（コンソール）とファイル（logs/<app_name>.log）に出力されます。日次ローテーション・30日保持です。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して一貫して設定されます。
- 環境変数で LOG_DIR を指定できます。

重要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用 / データ:
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- ログ / デバッグ:
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR
- AI:
  - OPENAI_API_KEY
- その他:
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔、秒。デフォルト 60)
  - PAPER_FILL_MODE (paper_trading の MockBroker の fill 動作: instant|partial|never|reject)
  - KILL_FLAG_CLEAR_ON_START (1 で起動時に kill.flag を自動クリア)

停止・制御
----------
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は検知して正常停止を試みます
- Kill Switch:
  - RiskMonitor 等の評価結果により data/kill.flag を書き込むことで ExecutionEngine に停止を指示できます
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に kill.flag を自動で消すオプションあり（本番では危険）

データベースとマイグレーション
---------------------------
- init_monitoring_db は monitoring 用のテーブルを作成し、実行時に不足カラムの追加マイグレーションを行います（冪等処理）。
- DuckDB は分析向けテーブル（prices_daily, raw_financials, raw_news 等）を参照します。DuckDB のパスは DUCKDB_PATH で指定。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数/設定読み込みと Settings
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 起動前設定チェック CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — Monitoring 起動スクリプト

- ai/
  - news_nlp.py           — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py    — 市場レジーム判定（MA200 + LLM）
  - __init__.py

- monitoring/
  - monitoring_db.py      — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py     — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py      — (該当ファイルがあれば発注ログ監視)
  - risk_monitor.py       — ドローダウン/ポジション制限監視
  - kill_switch.py        — kill.flag の管理
  - monitoring_engine.py  — Monitor の束ねとポーリング
  - alert_manager.py      — アラート管理（LINE 等の通知実装を持つ想定）

- execution/
  - execution_engine.py   — ExecutionEngine 本体
  - broker_factory.py     — ブローカークライアント生成
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

- monitoring/（上記）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

運用上の注意点 / トラブルシューティング
---------------------------------------
- 必須環境変数が未設定だと起動時にエラーになります。まずは config_setup → validate_config で確認してください。
- PyYAML がインストールされていないと config/*.yaml の内容検証はスキップされます（警告のみ）。
- OpenAI を使用する機能は API キー必須。API レート制限やネットワーク障害は指数バックオフでリトライしますが、失敗時はフェイルセーフのデフォルトで継続します（例: macro_sentiment=0.0）。
- psutil によるプロセス優先度設定は権限不足で失敗する場合があります（警告ログ）。
- MONITOR_POLL_INTERVAL に 0 や負数を設定すると無効値扱いでデフォルト 60 秒にフォールバックします。
- DuckDB / SQLite ファイルのパスが指す親ディレクトリが存在しない場合は警告が出ますが、起動時に自動作成される場合があります。

開発メモ
--------
- モジュールはできるだけ副作用を持たない設計（DB 書き込みや OpenAI 呼び出しなどは明示的関数で行う）
- 日付処理はルックアヘッドバイアスを避ける設計（target_date を引数で受け取り内部で date.today() を参照しない）
- ロギングは全アプリケーションで共通の setup_logging を使用して統一

ライセンス・著作権
-----------------
（このセクションは必要に応じてプロジェクトのライセンス情報を追記してください）

以上。質問や README に追加したい詳細（例: 具体的な設定例、logging 設定のカスタマイズ方法など）があれば教えてください。