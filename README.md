KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアモジュール群です。
戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
リサーチ用のファクター計算や AI ベースのニュースセンチメント評価などを含みます。

ここではリポジトリの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

ポイント（実装上の注意）
- 設定は .env ファイル（または環境変数）で管理します。自動読み込み機能あり（プロジェクトルート検出に依存）。
- ログは標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）へ出力します。
- run_execution / run_monitoring はフラグファイル（data/stop_requested.flag や data/kill.flag）で停止やキルを制御します。
- Paper Trading（KABUSYS_ENV=paper_trading）では実際のブローカを呼ばず MockBrokerClient を使い、DBは data/paper_trading.db に分離されます。

機能一覧
-------
- 設定管理
  - .env の自動読み込みとパース（kabusys.config）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行エンジン（Execution）
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - ブローカー抽象化（BrokerClientFactory）で paper_trading と live を切替可能
  - RiskManager / OrderManager / Reconciler などの発注周りコンポーネント

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db.py）
  - KillSwitch（drawdown 等で実行エンジンを停止させるフラグファイル生成）
  - run_monitoring スクリプト（kabusys.run_monitoring）

- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算（等分配／スコア加重）
  - 単元・リスクに基づく株数決定、セクター上限適用、レジーム乗数

- リサーチ / ファクター計算
  - Momentum / Value / Volatility のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）連携
  - ニュースを LLM（gpt-4o-mini）でセンチメント化し ai_scores へ格納（kabusys.ai.news_nlp）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（kabusys.ai.regime_detector）
  - API 呼び出しはリトライ・バックオフ・バリデーションあり

- ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

必須／推奨依存パッケージ
---------------------
（実行環境に合わせて pip 等でインストールしてください）
- Python >= 3.10（typing の | 記法を使用しているため）
- duckdb
- psutil
- openai
- PyYAML（config 検証時に任意で使用）
- その他標準ライブラリ（sqlite3, logging, threading, datetime 等）

セットアップ手順
----------------

1. リポジトリを取得（例）
   - git clone <repo_url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt があれば pip install -r requirements.txt を推奨）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルート）。最低で下記の必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（デフォルト値含む）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（例）
     - OPENAI_API_KEY: OpenAI を使用する場合に必要
     - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading 用）

5. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に FAIL と扱う場合:
     - python -m kabusys.validate_config --strict

基本的な使い方
-------------

1. 監視ループを起動（system/process/trade/risk をポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
   - run_monitoring は data/stop_requested.flag が存在するとループを終了します。

2. ExecutionEngine を起動（発注セッション）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し DB は data/paper_trading.db に記録します。
   - 実行中の PID は data/execution.pid に書かれます。停止は data/stop_requested.flag を作成することで行います。
   - 起動時に data/stop_requested.flag が存在する場合は起動をスキップして終了します。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD（開始日）
     - --to YYYY-MM-DD（終了日）
     - --db PATH（DB ファイルを明示する場合）
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

4. AI スコアリング / レジーム判定（ライブラリ関数として呼び出す）
   - ニュースセンチメント: from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=None)
   - レジーム判定: from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=None)
   - これらは DuckDB 接続を受け取り、テーブル（prices_daily, raw_news, news_symbols 等）を参照します。

重要なファイル／フラグ
--------------------
- デフォルト DB / ファイルパス
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - PID ファイル: data/execution.pid（ExecutionEngine）
  - Kill flag: data/kill.flag（KillSwitch が生成）
  - Stop flag: data/stop_requested.flag（run_monitoring/run_execution が監視）

- MONITOR_POLL_INTERVAL 環境変数による監視間隔の上書き（秒）
- KILL_FLAG_CLEAR_ON_START（env）: ExecutionEngine 起動時に kill.flag を自動クリアするか（開発用）
  - 本番では 0 を推奨

ディレクトリ構成（主要ファイル）
----------------------------
以下は src/kabusys の主なモジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - execution/                — 発注エンジン関連（BrokerFactory, Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 構造と読み書き
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                     — データ関連（DuckDB/SQL テーブル操作モジュール等）
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py

（上記は主なモジュールの一覧で、実際のリポジトリにはさらに細かなサブモジュールや補助モジュールが含まれます）

運用上の注意事項 / ベストプラクティス
-----------------------------------
- 本番運用時は KABUSYS_ENV を "live" に設定してください。validate_config は live 向けの追加チェックを行います。
- .env は機密情報を含むため、絶対に Git 等にコミットしないでください。
- OpenAI API キーを使用する機能はネットワーク接続と API 利用料が必要です。ローカル検証ではキー不要のパスを設けています（機能による）。
- run_execution/run_monitoring は logs/ にログを出力します。ログディレクトリは LOG_DIR 環境変数で変更できます。
- データベースファイル（DuckDB/SQLite）は適切にバックアップしてください。Paper Trading は本番 DB と明確に分離されます（PAPER_TRADING_SQLITE_PATH）。

トラブルシューティング
----------------------
- モジュール起動時に環境変数不足エラーが出る:
  - python -m kabusys.validate_config を実行して不足項目を確認してください。
- ログファイル作成に失敗してファイル出力が無効化される:
  - 権限やディスク容量を確認してください。コンソール出力は引き続き行われます。
- OpenAI 呼び出しが失敗する:
  - OPENAI_API_KEY が正しく設定されているか、およびネットワーク接続／API 利用制限を確認してください。ライブラリ側の RateLimit 等は内部でリトライ機構がありますが上限あり。

ライセンス / 貢献
-----------------
（この README には含まれていません。リポジトリに LICENSE ファイルがあればそちらを参照してください）

最後に
------
この README はソース内の実装（config, run_*, monitoring, ai, portfolio, research, tools 等）を基に作成しています。実際の運用にあたっては validate_config と小規模なローカル実行で挙動確認を行ってください。必要があれば README を拡張してインストール手順（requirements.txt）やデプロイ手順を追記してください。