KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の小規模なコードベースです。  
本リポジトリには以下の主要機能群が含まれます。

- ExecutionEngine（注文実行エンジン）と Broker 抽象化（実口座 / ペーパートレード両対応）
- Monitoring（システム稼働監視、データ鮮度、リスク監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制約）
- リサーチ（ファクター計算、将来リターン・IC 計算、特徴量探索）
- AI ユーティリティ（ニュースの NLP スコアリング、レジーム判定） — OpenAI API を使用
- ユーティリティ / CLI（.env ウィザード、設定検証、検証レポート生成 等）

バージョン
----------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

主な機能一覧
-------------
- run_execution.py: 実行エンジンを起動（KABUSYS_ENV によって paper_trading モードで MockBroker を使用）
- run_monitoring.py: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を記録
- config_setup.py: 対話式ウィザードで .env を生成・更新
- validate_config.py: .env と config/*.yaml を起動前に検証（--strict オプションあり）
- tools/paper_verification_report.py: ペーパートレード DB から検証レポートを作成
- portfolio モジュール: 候補選定・重み付け・ポジションサイジング等の純粋関数
- research モジュール: ファクター計算（momentum / value / volatility 等）と統計ユーティリティ
- ai モジュール: news_nlp, regime_detector（OpenAI を用いたスコアリング）

セットアップ手順
----------------

1. リポジトリをクローン／チェックアウト
   - Python パッケージとして動かせる状態（src を PYTHONPATH に載せるかパッケージインストール）にします。

2. Python 環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必須（主に実行時に必要となるもの）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
   - オプション:
     - PyYAML（validate_config が config YAML を検証する場合に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用してください）

4. 初期設定 (.env) の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 生成された .env は絶対にリポジトリにコミットしないでください（API キー等を含みます）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗として扱いたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの作成（通常は自動作成されますが手動で準備する場合）
   - data/（SQLite / PID / flag 等がここに置かれます）
   - logs/（ログ出力先。LOG_DIR で変更可能）

主要な環境変数（要点）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
  - paper_trading: MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB を使う
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 時の DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

使い方（コマンド例）
--------------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動しません
    - ExecutionEngine の PID は data/execution.pid に記録されます（デフォルト）

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は常に本番向けの sqlite_path（Settings.sqlite_path）を使用して監視ログを永続化します
  - 停止は data/stop_requested.flag を作るか、CTRL+C（KeyboardInterrupt）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パス指定可能（未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- AI 機能（ニュース NLP / レジーム判定）
  - 環境変数 OPENAI_API_KEY を設定し、該当関数を呼び出す（score_news / score_regime）
  - 実行例（スクリプト化されていないため、python REPL などから import して使用）

監視・停止 / Kill Switch
------------------------
- Kill Switch 用フラグ: Settings.kill_flag_path（デフォルト data/kill.flag）
  - KillSwitch はリスクアラート（ドローダウンやポジション上限）等の条件で kill.flag を書き込み、ExecutionEngine に停止信号を送ります
  - ExecutionEngine は起動時・実行中に kill.flag の存在を確認して停止処理を行う設計です
- 手動でシステムを止めたい場合は data/stop_requested.flag を作成してください（run_monitoring / run_execution が検知して終了します）
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動で削除します（本番では 0 を推奨）

ログ
---
- ログは setup_logging を通して統一的に出力されます:
  - コンソール出力（stdout）
  - 日次ローテートされたファイル: <LOG_DIR>/<app_name>.log（デフォルト logs/<app>.log）
- LOG_LEVEL / LOG_DIR は環境変数で調整可能

ディレクトリ構成
----------------
（主要ファイルのみ抜粋、パッケージは src/kabusys 以下に配置）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理（自動 .env ロードロジック含む）
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py            — ニュース NLP（OpenAI）
      - regime_detector.py     — レジーム判定（OpenAI + ETF MA）
    - monitoring/
      - monitoring_db.py       — SQLite 永続化レイヤ
      - system_monitor.py
      - trade_monitor.py       — （trade 関連の監視: ※省略ファイルは実装あり）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py       —（アラート送信ロジック、LINE など）
    - execution/               — ExecutionEngine 関連（Engine, BrokerFactory, OrderManager 等）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py
      - process_priority.py

データ / デフォルトファイル
--------------------------
- data/monitoring.db           — デフォルトの監視 SQLite（Settings.sqlite_path）
- data/paper_trading.db        — paper_trading 用 SQLite（Settings.paper_sqlite_path）
- data/kabusys.duckdb (または path は DUCKDB_PATH) — DuckDB（分析用）
- data/execution.pid           — ExecutionEngine の PID（実行時生成）
- data/kill.flag               — Kill Switch 用フラグ（生成されると ExecutionEngine に停止シグナル）
- data/stop_requested.flag     — run_* スクリプトを終了させるためのフラグ（手動で作成して停止）

開発上の注意 / ベストプラクティス
---------------------------------
- .env ファイルは機密情報を含むため絶対に Git へコミットしないこと
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にし、LINE 通知等の設定を必ず確認する
- OpenAI の呼び出しは失敗耐性とリトライロジックが組み込まれていますが、API キーと料金に注意してください
- monitoring は本番の監視 DB を参照して動作します。テスト・検証は paper_trading 用 DB を利用して実施することを推奨します

よく使うコマンド例
------------------
- .env を作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動（ポーリング間隔を 30 秒にする例）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 責任
-----------------
本 README はコードベースの要点をまとめたもので、実運用に入れる場合は追加の安全対策・監査・テストが必要です。特に実際の発注（live モード）を行う場合は十分に注意してください。

補足
----
不明点や実装に関する詳細は該当モジュール（kabusys/*）のドキュメント文字列やコードコメントを参照してください。README に含めていない細かな設定や内部仕様（例: ポジションサイジングのパラメータ等）は各モジュールの docstring に設計意図が記載されています。