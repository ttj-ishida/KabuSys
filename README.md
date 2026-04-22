KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースの小型フレームワークです。本リポジトリには以下の主要機能を含みます。

- 発注実行エンジン（ExecutionEngine）とブローカー抽象化（本番/ペーパー分離）
- 監視サブシステム（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・リスク調整・枚数決定）
- リサーチ用ファクター計算・特徴量解析（DuckDB を利用）
- ニュースに対する LLM ベースの NLP スコアリング（OpenAI）
- サポート CLI：.env ウィザード、設定検証、Paper Trading 検証レポート生成 等

特徴（抜粋）
--------------
- 実行環境（KABUSYS_ENV）により動作モードを切替（development / paper_trading / live）
- Paper Trading は本番 DB と完全分離（data/paper_trading.db を利用）
- モジュール設計によりリサーチ系は発注系と分離（DuckDB ベースの分析）
- LLM 利用部はフェイルセーフ（API失敗時のフォールバック）やリトライ実装あり
- ロギング設定ユーティリティでログの統一管理（コンソール + 日次ローテーション）

前提・依存
-----------
推奨 Python バージョン: 3.10+

必須パッケージ（例）
- duckdb
- psutil
- openai

推奨 / オプション
- PyYAML (config/*.yaml の検証を行う場合)

インストール例
- 仮想環境作成・有効化後:
  - pip install duckdb psutil openai pyyaml
（requirements.txt は同梱されていないため必要なパッケージを上記のようにインストールしてください）

環境変数（主要）
----------------
必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（任意／デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）
- OPENAI_API_KEY: LLM 系機能を使う場合必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動 ("instant"|"partial"|"never"|"reject")

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成（対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabuAPI / 各パス等を入力して .env を生成

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数や config/*.yaml の整合性を確認。--strict オプションで警告も FAIL 扱いにできます。

使い方（実行例）
----------------

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
    - 起動時に data/execution.pid を作成
    - 停止は data/stop_requested.flag を作成すると安全に停止します
    - Kill Switch（data/kill.flag）が設定されると ExecutionEngine を停止する設計があります

- Monitoring を起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視ループのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で指定可能（デフォルト 60 秒）
  - 監視用 SQLite は settings.sqlite_path（デフォルト data/monitoring.db）を使用します（monitoring は環境にかかわらず本番 sqlite_path を利用する実装です）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合: --db path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI（ニュース NLP / レジーム判定）をプログラムから呼ぶ例
  - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

  - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

注意: OpenAI API を使う機能は OPENAI_API_KEY（または引数での指定）が必要です。

主要コマンドまとめ
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン: python -m kabusys.run_execution
- 監視ループ: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み・Settings クラス
- config_setup.py
  - .env を対話式に生成するウィザード
- validate_config.py
  - 起動前検証 CLI

- run_execution.py
  - ExecutionEngine の起動スクリプト（PID管理・paper_trading 分離）
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL）

/ai
- news_nlp.py
  - raw_news を集約し OpenAI でセンチメントを算出、ai_scores に書き込む
- regime_detector.py
  - ETF の MA 乖離＋マクロニュースで市場レジームを判定し market_regime に書き込む

/monitoring
- monitoring_db.py
  - SQLite のスキーマ初期化・永続化用クラス MonitoringDB
- system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
  - システム/注文/リスクの監視ロジックと Kill Switch、アラート連携

/portfolio
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
  - 候補選定・重み付け・枚数決定・セクター制約・レジーム係数

/research
- factor_research.py
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
- feature_exploration.py
  - 将来リターン計算、IC、統計サマリ

/tools
- paper_verification_report.py
  - Paper Trading の検証レポートを生成する CLI

/utils
- logging_setup.py
  - ルートロギング設定（console + 日次ファイルローテーション）
- process_priority.py
  - プロセス優先度 / CPU affinity 設定ユーティリティ

データ・ログ
- デフォルトの DB / ログパス
  - data/monitoring.db（SQLite）
  - data/paper_trading.db（Paper Trading 用）
  - data/kabusys.duckdb（DuckDB）
  - data/kill.flag, data/stop_requested.flag, data/execution.pid
  - logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション）

運用上の注意
------------
- .env は機密情報を含むため絶対にバージョン管理にコミットしないでください。
- KABUSYS_ENV=live 設定時は特に注意（validate_config がいくつか注意喚起を行います）。
- process_priority/set_cpu_affinity は権限不足で警告が出ることがあります（スキップされる）。
- OpenAI 呼び出しはコストとレート制限に注意して運用してください。
- kill.flag / stop_requested.flag の取り扱いに注意（自動クリア設定は本番では推奨されません）。

トラブルシューティング（よくある問題）
-----------------------------------
- 必須環境変数未設定 → python -m kabusys.validate_config で検出
- DuckDB / SQLite ファイルが見つからない → デフォルト path（data/）を確認、必要なら事前にディレクトリ作成
- OpenAI API エラー → OPENAI_API_KEY を設定、ネットワーク/制限を確認
- PyYAML 未インストール → validate_config の YAML 検証はスキップされます（警告）

最後に
------
この README はコードベースの主要部分を概説したものです。各モジュール・関数には docstring が付いているため、実装の詳細な利用法やパラメータは該当ファイルを参照してください。必要であれば README にサンプル設定例やデプロイ手順（systemd / Docker / k8s）を追加できます。要望があれば追記します。