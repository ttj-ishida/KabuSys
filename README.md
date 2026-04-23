# KabuSys

日本株自動売買システムのサブセット実装（ライブラリ + 起動スクリプト群）。  
このリポジトリには、実行エンジン、監視機構、ポートフォリオ構築、リサーチ/ファクター計算、AI を使ったニュース解析などの主要コンポーネントが含まれます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は以下です：

- ExecutionEngine：発注ロジック・ブローカークライアント連携・リスク管理
- Monitoring：システム状態、注文状態、リスク指標の定期監視とアラート / Kill Switch
- Portfolio：銘柄選定・重み計算・ポジションサイズ計算（純関数群）
- Research：DuckDB 上のファクター計算・特徴量探索ユーティリティ
- AI：ニュースを LLM（OpenAI）で評価してスコア化 / 市場レジーム判定
- CLI ツール：.env ウィザード、設定検証、ペーパートレード検証レポート 等

コードは "src/kabusys" 配下にまとまっています。実行スクリプトはモジュールとして実行できます（例: python -m kabusys.run_execution）。

---

## 主な機能一覧

- 環境設定ウィザード（kabusys.config_setup）
  - 対話式に .env を生成・更新
- 設定検証ツール（kabusys.validate_config）
  - .env や config/*.yaml の不足や不整合を事前チェック
- Execution 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV により本番 / ペーパートレード切替
  - paper_trading では MockBroker を使用し DB を分離
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - システム/注文/リスクを定期ポーリングしてログ保存・Kill Switch 評価
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可（デフォルト 60 秒）
- MonitoringDB（SQLite）永続化層（monitoring.monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理
- RiskMonitor / TradeMonitor / SystemMonitor / MonitoringEngine：監視ロジック
- Portfolio モジュール（candidate 選定、重み計算、ポジションサイズ計算）
- Research（DuckDB を用いたファクター算出、IC 計算、統計サマリー）
- AI モジュール
  - news_nlp: ニュースを LLM でセンチメントスコア化して ai_scores に書き込み
  - regime_detector: マクロ記事 + ETF ma200 乖離で市場レジーム判定
- ユーティリティ
  - logging_setup: 一貫したロギング設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
- ツール
  - paper_verification_report: ペーパートレード結果の検証レポート生成

---

## 前提 / 依存パッケージ（参考）

最低限の外部依存（代表）：
- Python 3.9+
- psutil
- duckdb
- openai (AI 機能を使う場合)
- PyYAML（config YAML の内容検証を行う場合）
- sqlite3（標準ライブラリ）

インストール例（pip）:
pip install psutil duckdb openai PyYAML

※ 実プロジェクトでは requirements.txt / Poetry 等を使って依存管理してください。

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を準備
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt もしくは上記の個別インストール

3. .env を作成
   - 対話式ウィザードを利用（推奨）
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な設定とデフォルト値（抜粋）:
     - KABUSYS_ENV = development | paper_trading | live  (default: development)
     - DUCKDB_PATH = data/kabusys.duckdb
     - SQLITE_PATH = data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH = data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL = INFO
     - OPENAI_API_KEY = (AI 機能利用時に必須)

   - 自動ロード: config モジュールはプロジェクトルートの .env/.env.local を自動で読み込みます。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. ディレクトリ作成（必要に応じて）
   - data/ （DB・flag・pid 用）
   - logs/ （ログファイル）

---

## 使い方（主要コマンド例）

- 実行エンジン（Execution）
  - 本番/開発/ペーパー共通:
    - python -m kabusys.run_execution
  - ペーパートレードモードで起動（MockBroker を使い DB を分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  動作:
    - Settings に基づき SQLite / DuckDB に接続
    - BrokerClientFactory によるブローカークライアント生成（paper_trading では Mock を使用）
    - ExecutionEngine を別スレッドで run_session 実行、stop_requested.flag を検知すると停止

  注意:
    - 実行中に停止させるには data/stop_requested.flag を作成することでスクリプト側が検知して停止します。
    - 実行時に pid が data/execution.pid に書き込まれます。

- 監視プロセス（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  （秒）

  動作:
    - プロセス優先度を high に設定
    - MonitoringDB を初期化（本番 sqlite_path を利用、環境に依存せず）
    - SystemMonitor.check_once を周期的に呼び出す（例では 60 秒デフォルト）
    - data/stop_requested.flag の存在でループを抜けて終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB パスは env PAPER_TRADING_SQLITE_PATH か data/paper_trading.db

- AI / リサーチ関数（ライブラリ呼び出し）
  - OpenAI を使う機能（news_nlp.score_news, regime_detector.score_regime）は OPENAI_API_KEY を設定すること
  - 例（Python API）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

---

## ファイル／フラグの意味（運用メモ）

- data/stop_requested.flag
  - run_execution / run_monitoring が存在を検知すると安全に終了します（停止要求フラグ）
- data/kill.flag
  - KillSwitch が条件を満たすと書き込むファイル。ExecutionEngine に対して「停止すべし」という信号
- data/execution.pid
  - ExecutionEngine の PID を記録（プロセス管理用）
- logs/<app_name>.log
  - ローテートされたログファイル（デフォルト: logs/ 、日次ローテーション、30 日保存）
- DB
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite（監視）: data/monitoring.db
  - SQLite（paper_trading）: data/paper_trading.db

---

## 環境変数まとめ（主要）

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用 / 動作切替
  - KABUSYS_ENV: development | paper_trading | live (default: development)
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PAPER_FILL_MODE: instant | partial | never | reject (paper_trading 振る舞い)
  - SQLITE_PATH: data/monitoring.db
  - DUCKDB_PATH: data/kabusys.duckdb
  - LOG_LEVEL: DEBUG|INFO|...
  - LOG_DIR: ログ保存先（デフォルト logs/）
  - OPENAI_API_KEY: OpenAI を用いるときに必要
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発用）

- 監視ループ制御
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## ディレクトリ構成（簡易）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・Settings 管理（自動 .env ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
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
    - risk_monitor.py
    - trade_monitor.py (参照実装あり)
    - kill_switch.py
    - alert_manager.py (参照)
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

---

## 運用上の注意 / ベストプラクティス

- 本番運用（KABUSYS_ENV=live）では .env の中身や LINE 等通知先の設定を必ず確認してください（validate_config の live ガードが警告を出します）。
- kill.flag / stop_requested.flag の扱いに注意：
  - kill.flag は意図的な停止要求や安全停止のトリガーです。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされるため、本番では 0 を推奨します。
- ログ出力先（LOG_DIR）や DB パスは適切な権限の場所を指定してください。ログディレクトリ作成に失敗するとファイルハンドラは無効化され stdout のみになります。
- AI（OpenAI）機能はネットワーク・API 制限・料金に注意して運用してください。API 呼び出しはリトライやフェイルセーフ（失敗時 0.0 にフォールバック）を組み込んでいますが、過剰なリクエストは避けてください。
- テスト環境（development / paper_trading）と本番（live）は DB を分離し、ペーパートレードは本番 DB を汚さないようになっています。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はソースコードの現状（主要ファイル）に基づいて作成しています。実際の運用や拡張時はそれぞれのモジュールの docstring / 関数定義を参照してください。質問や追加で載せてほしい使用例があれば教えてください。