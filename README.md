README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコアライブラリです。  
主な目的は以下です:

- 日次・リアルタイムのファクター計算とポートフォリオ構築
- ExecutionEngine による発注（実口座 / ペーパートレード対応）
- 監視（Monitoring）と Kill Switch（安全停止）の実装
- ニュース NLP / レジーム判定のための LLM 連携（OpenAI）
- Paper Trading の検証レポート生成、研究用ユーティリティ

本リポジトリはビジネスロジックとユーティリティ群をモジュール単位で提供します。起動スクリプトや対話型ウィザード、検証ツールも含まれます。

主な機能一覧
--------------
- Execution
  - ExecutionEngine（本番 / ペーパートレード切替）
  - BrokerClientFactory（実ブローカー or Mock を選択）
  - OrderManager / OrderRepository / RiskManager / Reconciler
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック）
  - TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
- Portfolio
  - 候補選定・重み計算（等金額・スコア加重）
  - セクター上限・レジーム乗数（リスク調整）
  - ポジションサイズ計算（単元株丸め・aggregate cap）
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 特徴量探索：将来リターン計算、IC（スピアマン）等
- AI（LLM）連携
  - news_nlp: ニュース記事を OpenAI でセンチメント評価 -> ai_scores へ保存
  - regime_detector: MA200 とマクロニュースを組み合せて市場レジーム判定
- ツール類
  - config_setup: .env を対話的に生成
  - validate_config: 設定の事前チェック
  - paper_verification_report: ペーパートレード検証レポート生成
- ユーティリティ
  - ログ設定（stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定
  - .env パーサ（プロジェクトルート自動ロード）

セットアップ手順
----------------
1. Python 環境（推奨: 3.10+）を用意します。仮想環境を作成してください:
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストールします（requirements.txt があればそれを使用）。本プロジェクトで想定される主要パッケージ:
   - duckdb
   - psutil
   - openai
   - pyyaml（config の YAML 検証に任意で使用）
   例:
   - pip install duckdb psutil openai pyyaml

   ※ 実行環境に応じて追加パッケージ（ブローカークライアント等）が必要になる場合があります。

3. プロジェクトルートに .env を作成します（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   ウィザードは .env を生成します（.env.example を参考にすること）。

4. 設定を検証します:
   - python -m kabusys.validate_config
   - 重要な警告も厳密に扱う場合: python -m kabusys.validate_config --strict

5. ディレクトリ作成（データ・ログ等）:
   - mkdir -p data logs
   実行時に自動作成される場合もありますが、手動で用意しておくと権限等の問題を回避できます。

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 用）
- PAPER_FILL_MODE: ペーパー発注の fill モード（instant|partial|never|reject）（デフォルト: instant）
- LOG_LEVEL: ログレベル（INFO 等）
- OPENAI_API_KEY: OpenAI を使用する機能で必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

停止 / Kill の仕組み:
- data/stop_requested.flag: run_* スクリプトはこのファイルを検知して安全に終了します。
- data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送出します。
- data/execution.pid: ExecutionEngine が PID を書き込むファイル（run_execution が利用）。

使い方（起動・運用）
--------------------

基本的な起動コマンド（モジュール実行形式）:
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を設定 (秒)
- Execution エンジンを起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使い、data/paper_trading.db に記録します。

設定ウィザード / 検証:
- .env を対話式で作成:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として扱います

Paper Trading 検証レポート:
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
- 環境変数 PAPER_TRADING_SQLITE_PATH を使用してデフォルトを上書き可能

AI（OpenAI）関連:
- news_nlp と regime_detector は OPENAI_API_KEY が必要です。API 呼び出しは gpt-4o-mini を想定しています。
- API 失敗時はフェイルセーフ（スコアに 0 を使う等）で継続する設計です。

停止方法:
- 手動で安全停止するにはプロジェクトルート下に data/stop_requested.flag を作成します（ファイルの中身は任意）。
- KillSwitch を発動させたい場合は data/kill.flag を直接作成しても ExecutionEngine は次のポーリングで停止します（ただし本番での運用は注意）。

ログ
---
- ログは stdout（コンソール）に出力され、デフォルトで logs/<app_name>.log に日次ローテーションで出力されます。
- setup_logging が起動時に自動設定します。ログディレクトリは環境変数 LOG_DIR で上書き可能です。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — レジーム判定（MA200 + LLM）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ + 永続化 API
    - system_monitor.py
    - trade_monitor.py        — （トレード監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信ロジック）
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                     — 実行時に生成されることが多い（監視 DB, pid, flags 等）

（実際のファイル一覧はプロジェクトのソースツリーを参照してください）

運用上の注意
------------
- KABUSYS_ENV を live に設定する際は設定値（LINE 通知、API キー、KILL フラグ等）を十分に確認してください。validate_config は live 環境時に追加警告を出します。
- process_priority の設定は OS により権限が必要です。psutil による設定が失敗した場合はロギングしてスキップされます。
- OpenAI を使う機能はコストとレイテンシに注意してください。API エラーはリトライ処理がありますが、過度の自動化は避けてください。
- データベース（DuckDB / SQLite）ファイルは適切にバックアップ・権限設定を行ってください。

開発・拡張
-----------
- research や portfolio モジュールは純粋関数群として設計されており、テストや単体検証が容易です。
- news_nlp / regime_detector の API 呼び出し回りはテストでモック化可能なように分離されています。
- config の .env パーサは複数のクォート・コメント形式に対応した独自実装です。必要に応じて .env.example を用意してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報は本リポジトリの LICENSE ファイルを参照してください（存在しない場合はプロジェクト方針に従って追加してください）。

問い合わせ
----------
不明点や実運用に関する質問があれば開発チームのリポジトリ管理者に問い合わせてください。README に書かれている設定や運用フローを参照のうえ、環境に合わせて適宜カスタマイズしてください。