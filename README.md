README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤コードです。本リポジトリは以下の主要機能を提供します。

- 発注実行エンジン（ExecutionEngine） — 実際の発注またはペーパートレードを実行
- 監視（Monitoring） — システム稼働状況・データ鮮度・リスク監視、アラート発行、Kill Switch
- ポートフォリオ構築ユーティリティ（選定・重み付け・ロット丸め）
- リサーチ / ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ニュース NLP（OpenAI を使ったニュースセンチメント評価）
- 開発・運用支援ツール（.env ウィザード、設定検証、Paper Trading の検証レポート）
- ロギング・プロセス優先度ユーティリティ等の共通ユーティリティ群

特徴
----
- 環境別設定: KABUSYS_ENV により development / paper_trading / live を切替可能
- Paper Trading は本番 DB と分離（デフォルト data/paper_trading.db）
- DuckDB を分析用に利用、SQLite を監視 / 発注履歴に利用
- OpenAI（gpt-4o-mini 等）を用いたニューススコアリングとレジーム判定の仕組み
- ファイルフラグ（data/stop_requested.flag, data/kill.flag）によるシンプルなプロセス制御
- 日次ローテーションでログを保存（logs/<app_name>.log）

セットアップ手順
----------------

前提
- Python 3.9+（コードの typing や構文に依存）
- システムに sqlite3 が利用可能（標準ライブラリ）
- pip が利用可能

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   依存ライブラリ（少なくとも次をインストールしてください）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定ファイル検証を行う場合のみ）
   例:
     pip install duckdb psutil openai PyYAML

   注意: requirements.txt が存在する場合はそれを使ってください。

4. 環境変数 (.env) の作成
   - 対話式ウィザードを使う（推奨）:
       python -m kabusys.config_setup
     これによりプロジェクトルートに .env を生成 / 更新できます。
   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD    (必須)
     そのほか:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
     - LOG_LEVEL
     - OPENAI_API_KEY (AI 機能を使う場合)

5. 設定検証
   - python -m kabusys.validate_config
     --strict を付けると警告も FAIL 扱いになります。

6. データ・ログディレクトリの準備
   - data/ と logs/ は自動作成されますが、権限が必要な場合は事前作成してください。

使い方
------

主要なエントリポイント（CLI 実行可能モジュール）

- 実行エンジン（Execution）
  - 開始:
      python -m kabusys.run_execution
    動作:
      - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用します。
      - PID ファイル: data/execution.pid（設定により変更可能）
      - プロセス優先度を high に設定し起動します（権限により設定できない場合は警告ログ）。
    停止:
      - data/stop_requested.flag を作成すると実行ループが検知して終了します。
      - KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込み、実行エンジンを停止させます。

- 監視プロセス（Monitoring）
  - 開始:
      python -m kabusys.run_monitoring
    動作:
      - Settings に従った SQLite（監視 DB）と DuckDB に接続します。
      - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、KillSwitch / AlertManager を通じて通知・制御します。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
      - 監視は常に本番 sqlite_path を使用（環境にかかわらず）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 事前に .env と config/*.yaml を確認できます。PyYAML があれば YAML の構文検証も行います。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH / data/paper_trading.db
    - 稼働率・注文成功率・レイテンシ等のサマリを出力します。

- AI / リサーチ関数（プログラム呼び出し）
  - ニューススコアリング:
      from kabusys.ai.news_nlp import score_news
      # duckdb へ接続して呼び出す例
      import duckdb, datetime
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, datetime.date(2026, 4, 1), api_key="sk-...")
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date, api_key=...)
  - これらはライブラリ関数として呼び出す想定です（CLI ラッパーは現状なし）。

停止・強制停止
- 優雅な停止: data/stop_requested.flag を配置すると run_execution/run_monitoring のループが検知して終了します。
- Kill Switch: 監視が条件を満たすと data/kill.flag を生成し ExecutionEngine を停止させます。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動でクリアします（本番では推奨されません）。

ログ
- デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- 日次ローテーション（30日分保持）
- ログレベルは LOG_LEVEL 環境変数で制御

設定項目の主な説明 (Settings)
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution の挙動を決める（development | paper_trading | live）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI 利用時に必要
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

ディレクトリ構成
----------------

リポジトリ内の主要ファイル/ディレクトリ（src/kabusys を起点）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話型ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト（CLI）
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト（CLI）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成スクリプト
  - utils/
    - logging_setup.py       — ロギング初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注・ブローカー・ルール系（Engine, OrderManager など）
  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視 DB 層
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
  - ai/
    - news_nlp.py            — ニュースセンチメント集計・OpenAI 連携
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロセンチメント）
  - data/                   — 実行時に利用するファイル群（デフォルトパス: data/）
    - stop_requested.flag   — 手動で作ればプロセス終了を要求できるフラグ
    - kill.flag             — Kill Switch による停止フラグ
    - execution.pid         — PID ファイル（ExecutionEngine）
  - logs/                   — ログファイルの保存先（logs/<app_name>.log）

注意事項・運用メモ
-----------------
- 本番運用（KABUSYS_ENV=live）では LINE 通知や kill flag の設定を十分に確認してください。validate_config は live 時に追加警告を出します。
- process_priority や cpu_affinity の設定は権限に依存します。権限がないと警告でスキップされます。
- OpenAI API 呼び出しはトークン・レート制限・課金に注意して実行してください。API 呼び出しはリトライロジックを備えていますが、失敗時はフォールバック処理が行われます。
- .env ファイルは機密情報を含むため、絶対にバージョン管理にコミットしないでください。
- DuckDB / SQLite のパスは Settings で変更可能です。Paper Trading は本番 DB と物理的に分離することを推奨します。

サポート / 開発
----------------
- 設計意図やアルゴリズムの詳細はソース内の docstring / コメントを参照してください（PortfolioConstruction.md 等のドキュメントが別途ある想定）。
- ユニットテストや CI の導入を推奨します。AI 呼び出し部分はモックがしやすいように設計されています。

以上で README のサマリです。必要であれば、セットアップ用の requirements.txt、systemd / supervisor 用のユニット例、またはデプロイ手順（コンテナ化やサービス定義）を追加で作成します。どれが必要か教えてください。