README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームの骨組みを提供する Python パッケージです。
主な機能は次のとおりです：

- データ収集／DuckDB ベースの時系列解析（research）
- ポートフォリオ構築・リスク制御（portfolio）
- 発注実行エンジン（ExecutionEngine）と注文管理（execution）
- 監視（system / trade / risk）とアラート送信（LINE）
- Paper Trading 用のモック環境と検証レポート生成ツール
- ニュース NLP（OpenAI）を利用した銘柄センチメントと市場レジーム判定

注: このリポジトリはフル実装を想定したモジュール群を含みます。外部サービス（kabuステーション、J-Quants、OpenAI 等）との連携には各種環境変数や API キーが必要です。

機能一覧
--------
主要機能の要約：

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行系
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV=paper_trading では MockBroker を使用）
  - run_monitoring: SystemMonitor をポーリング

- 監視
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視
  - TradeMonitor: 滞留注文・約定価格異常を検出
  - RiskMonitor: ドローダウン／ポジション上限監視、dashboard 更新、risk_logs 出力
  - KillSwitch: 一定条件で data/kill.flag を書き込み ExecutionEngine に停止シグナル

- 通知
  - AlertManager: LINE Messaging API へプッシュ（クールダウン管理）

- 研究・分析
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - research.feature_exploration: 将来リターン・IC・統計サマリー

- AI（OpenAI）
  - ai.news_nlp: ニュース記事を集約して LLM に投げ、銘柄別スコアを ai_scores に書き込み
  - ai.regime_detector: ETF（1321）MA とマクロニュースで日次レジーム判定

- Portfolio（純粋関数群）
  - 候補選定、重み計算、ポジションサイズ算出、セクター上限適用、レジーム乗数

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成

セットアップ手順
----------------

1. リポジトリをクローン / 展開
   - この説明はパッケージルート（pyproject.toml または .git がある場所）で行います。

2. 仮想環境を作成して依存をインストール
   - 例（venv + pip）:
     - python -m venv .venv
     - source .venv/bin/activate  # Windows は .venv\Scripts\activate
     - pip install -r requirements.txt
   - 必要な主な依存:
     - duckdb
     - psutil
     - requests
     - openai（AI 機能を使う場合）
     - PyYAML（設定検証で YAML 内容をチェックしたい場合。無くても動作します）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に直接作成する。
   - 自動ロード:
     - デフォルトでプロジェクトルートの .env（および .env.local）を自動読み込みします。
     - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）
   - その他は config_setup のウィザードで説明があります。

5. DB 初期化
   - monitoring 用 SQLite は自動でテーブル作成・マイグレーションされます（init_monitoring_db）。

使い方（起動方法・CLI）
--------------------

- 設定検証
  - python -m kabusys.validate_config
  - 警告を厳格に扱いたい場合: python -m kabusys.validate_config --strict

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 監視ループを起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 停止方法:
    - data/stop_requested.flag を作成すると監視ループは次のポーリングで終了します。
    - Ctrl+C（KeyboardInterrupt）でも停止します。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 実行中は data/execution.pid に PID を書き込みます。
  - 停止方法:
    - data/stop_requested.flag を作成すると実行エンジンを安全停止します。
    - KillSwitch が条件を満たすと data/kill.flag が書かれ ExecutionEngine に停止シグナルが送られます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニューススコア／レジーム判定）
  - ai.news_nlp.score_news / ai.regime_detector.score_regime を呼び出し可能（プログラムから）。
  - 実行には OPENAI_API_KEY が必要です。API 呼び出しはリトライやフォールバックを備えていますが、キー未設定だと例外になります。

運用上の注意
-------------
- process priority:
  - run_monitoring / run_execution は起動時に set_process_priority("high") を呼び出してプロセス優先度を上げます（psutil 利用、権限不足なら警告）。
- Kill Switch / Stop フラグ:
  - data/kill.flag : KillSwitch により書かれる停止フラグ（実行エンジンに停止指示を出す）
  - data/stop_requested.flag : run_*.py の外部停止用フラグ（直接作成するとスクリプトが終了）
- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると本番 DB と発注が分離され、data/paper_trading.db に記録されます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() はテーブルの作成と簡易マイグレーション（カラム追加）を行います。既存 DB を上書きしないため基本的に安全です。
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込みます。OS 環境変数は保護されます。

ディレクトリ構成
----------------
主要なファイル・パッケージ（src/kabusys 以下）:

- __init__.py
- config.py
  - Settings クラス：環境変数管理、自動 .env ロード
- config_setup.py
  - .env 対話ウィザード
- validate_config.py
  - 設定検証 CLI

- run_monitoring.py
  - SystemMonitor のポーリングスクリプト（MONITOR_POLL_INTERVAL）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker）

- monitoring/
  - monitoring_db.py : SQLite の永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py : CPU・プロセス・データ鮮度監視
  - trade_monitor.py : 注文滞留・約定異常監視
  - risk_monitor.py : ドローダウン・ポジション数監視
  - kill_switch.py : kill.flag 書き込みロジック
  - monitoring_engine.py : 各 Monitor を束ねるエンジン
  - alert_manager.py : LINE 通知

- execution/ (発注関連: Engine, OrderManager, BrokerFactory 等) — 本リストでは実装ファイルは省略（リポジトリ内にある前提）

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

- tools/
  - paper_verification_report.py

- utils/
  - process_priority.py

- data/ （デフォルトの DB / フラグ / PID 保存先）
  - data/kabusys.duckdb (default)
  - data/monitoring.db (default)
  - data/paper_trading.db (paper trading 用 default)
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

よくある Q&A / トラブルシューティング
------------------------------------
Q: .env の値が読み込まれない
A: プロジェクトルートが検出できない場合は自動ロードをスキップします。KABUSYS_DISABLE_AUTO_ENV_LOAD を未設定にしているか確認、または明示的に環境変数を設定してください。

Q: OpenAI を使うときの注意
A: OPENAI_API_KEY が必要です。API 呼び出しはリトライしますが、料金やレート制限に注意してください。

Q: Paper Trading と本番 DB の混同を避けたい
A: KABUSYS_ENV=paper_trading に設定すると paper_sqlite_path を使用します。デフォルトでは data/paper_trading.db に分離されます。

付録：主要な環境変数（抜粋）
----------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper trading 用 DB)
- OPENAI_API_KEY (AI 機能)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag をクリアするか: 0/1)

最後に
-----
この README はリポジトリ内のコード（主要モジュール）を基に作成しています。実際の導入・運用時は config/*.yaml（存在する場合）や config_setup で生成された .env を必ず確認し、validate_config でチェックしたうえで起動してください。不明点や追加説明が必要であれば教えてください。