# KabuSys — 日本株自動売買システム

このリポジトリは、日本株自動売買システム「KabuSys」のコアライブラリ群です。戦略・ポートフォリオ構築、発注/実行エンジン、監視、研究（ファクター計算）、AI（ニュースセンチメント／レジーム判定）、およびユーティリティを含みます。

---

## 概要

KabuSys は以下の主要機能を持つモジュール式の自動売買フレームワークです。

- 発注・実行エンジン（ExecutionEngine）
- 監視（System / Trade / Risk）と Kill Switch（安全停止）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定） — OpenAI API を利用
- Paper Trading 対応（本番 DB と分離された SQLite）
- ログ設定ユーティリティ（コンソール + 日次ローテーション）
- 設定ウィザード・検証ツール（.env 生成 / validate）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine 起動スクリプト。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に記録。
  - 停止フラグ（data/stop_requested.flag）を監視して安全に停止。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動。
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）。
  - 監視情報は監視用 SQLite（デフォルト: data/monitoring.db）へ保存。

- monitoring モジュール
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch: ドローダウンやポジション上限到達で停止フラグを書き込む
  - MonitoringDB: SQLite スキーマ作成・永続化 API

- portfolio モジュール
  - 候補選定、等重/スコア重み、リスク調整（セクター上限、レジーム乗数）
  - 株数算出（lot 単位・最大ポジション・投下合計のスケーリング）

- research モジュール
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- ai モジュール
  - news_nlp: OpenAI でニュースをセンチメント（-1.0〜1.0）化し ai_scores に保存
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して日次レジーム判定

- utils
  - logging_setup: stdout + 日次ローテートログハンドラ
  - process_priority: Windows / POSIX を吸収するプロセス優先度設定ユーティリティ

- tools
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを出力

---

## セットアップ手順

※ 仮定: Python 3.10+ を使用

1. リポジトリをクローン / ワークディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 依存ライブラリをインストール
   - 必須（主なもの）
     - duckdb
     - psutil
     - openai
     - sqlite3（標準ライブラリ）
     - （任意）PyYAML（config 検証で必要）
   - 例（pip）:
     pip install duckdb psutil openai pyyaml

   - 開発時はパッケージを編集可能インストール:
     pip install -e .

3. .env の作成（環境変数）
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成。
   - 主要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - OPENAI_API_KEY（AI 機能を使う場合に必須）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading の場合の DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（INFO 等）
     - MONITOR_POLL_INTERVAL（監視ループの秒数）
     - PAPER_FILL_MODE（paper_trading のマッチングモード: instant|partial|never|reject）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - data/ （ログ・DB・フラグファイル等）
   - logs/ （ログ出力先、デフォルト）

---

## 使い方（起動コマンド）

- Execution Engine 起動
  - python -m kabusys.run_execution
  - paper_trading モード（.env で KABUSYS_ENV=paper_trading）では paper_trading 専用 DB を使用し、本番 DB と分離

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告もエラー扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（例）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定してから、ai モジュールの関数を呼ぶ
  - 例（スクリプト/REPL 内）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=None)  # api_key None だと env を参照

---

## 重要なファイル／フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution がこのフラグを検知すると安全に停止します。
  - 手動で停止を要求する場合に使用。

- data/kill.flag
  - KillSwitch が条件に合致したときに書き込むフラグ。ExecutionEngine の停止トリガに使われる。

- data/execution.pid
  - ExecutionEngine の PID ファイル（Settings.pid_file_path で参照）

- ログ
  - デフォルトは logs/<app_name>.log 日次ローテーション（30日保持）
  - LOG_DIR 環境変数で変更可能

---

## 環境変数（主なもの / デフォルト）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development | paper_trading | live（default: development）
- OPENAI_API_KEY — AI 機能で必要
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
- LOG_LEVEL — INFO
- LOG_DIR — logs/
- MONITOR_POLL_INTERVAL — 60
- PID_FILE_PATH — data/execution.pid
- KILL_FLAG_PATH — data/kill.flag
- KILL_FLAG_CLEAR_ON_START — 0（1 にすると起動時に kill.flag を自動クリア）

---

## ディレクトリ構成

（主なパッケージと代表ファイル）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数の読み取りと Settings クラス（.env 自動ロード）
  - config_setup.py         — .env 作成ウィザード（対話式）
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト

  - execution/              — 発注・実行関連コンポーネント（Engine, Broker, OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

---

## 開発上の注意 / ベストプラクティス

- KABUSYS_ENV を正しく設定してください。特に production 相当の `live` を設定する際は validate_config を実行して設定を確認してください。
- 本番（live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch をクリアしないため）。
- Paper Trading モードでは paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB とは分離されます。
- AI 機能を利用する場合は OPENAI_API_KEY を設定してください。API 通信はリトライやフェイルセーフ処理がありますが、API 負荷に注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります。権限やパスに注意してください。

---

必要があれば README をプロジェクトの実際の CI / デプロイ手順、詳細な .env のサンプル、または各モジュール（ExecutionEngine、OrderManager、BrokerFactory など）の使い方を追加で作成します。どの部分を詳しく記述しましょうか？