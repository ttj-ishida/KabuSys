# KabuSys

日本株自動売買システムのコアライブラリ群と運用ユーティリティ群です。  
このリポジトリは戦略・ポートフォリオ構築、注文実行、監視、研究、AI（ニュースセンチメント・レジーム判定）などの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール化された自動売買フレームワークです。

- 戦略／ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- 注文実行（ブローカー抽象化、注文状態管理、リコンシリエーション）
- 監視（システム状態・データ鮮度・注文異常・リスク監視、LINE通知、kill flag）
- 研究（ファクター計算、特徴量探索、IC計算）
- AI 支援（ニュースのLLMセンチメント評価、マクロセンチメントによるレジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ベースの監視ダッシュボード）

設計方針の特徴：
- DuckDB を用いた時系列・財務データ処理（prices_daily / raw_financials 等）
- SQLite を監視ログ／注文ログに使用
- LLM 呼び出しは OpenAI API を利用（環境変数で API キー指定）
- 本番 / paper_trading / development を切り替え可能（Settings.env）

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数/.env の自動ロード、および Settings クラス
- kabusys.portfolio
  - portfolio_builder: 候補選定・等重/スコア重み付け
  - position_sizing: 発注株数・投下資金スケーリング・単元丸め
  - risk_adjustment: セクター上限・レジーム乗数
- kabusys.execution
  - OrderManager / Reconciler / ExecutionEngine（起動スクリプトと連携）
  - BrokerFactory（paper_trading 時は MockBroker を使用）
- kabusys.monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス・データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数上限監視
  - KillSwitch: flag ファイルで ExecutionEngine に停止信号を送る
  - AlertManager: LINE によるプッシュ通知（クールダウン管理）
  - MonitoringDB: SQLite テーブル定義と永続化 API
  - MonitoringEngine / streamlit ダッシュボード
- kabusys.research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリー
- kabusys.ai
  - news_nlp: raw_news をまとめて OpenAI で銘柄別センチメント評価 → ai_scores
  - regime_detector: ETF MA200 とマクロセンチメントを合成して market_regime を記録
- tools
  - paper_verification_report: Paper Trading DB から検証レポート生成

---

## セットアップ手順

前提
- Python 3.10 以降（コードは型注釈に `X | None` を使用）
- SQLite は組み込み、下記パッケージをインストールしてください

推奨インストール（venv 使用例）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクト配布に pyproject.toml / requirements.txt がある場合はそちらを使用してください）

3. 環境変数 / .env の用意
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

推奨の最低必須環境変数（運用により異なります）:
- JQUANTS_REFRESH_TOKEN (必要な場合)
- KABU_API_PASSWORD — kabuステーション接続用
- OPENAI_API_KEY — AI 機能を使う場合必須
- KABUSYS_ENV — development | paper_trading | live （デフォルト: development）

主要な環境変数とデフォルト:
- KABUSYS_ENV (development | paper_trading | live) — 環境切替
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager にて通知する場合

サンプル .env（参考）
    # KabuSys 環境
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

    # DB
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

    # Broker / API
    KABU_API_PASSWORD=your_kabu_password
    KABU_API_BASE_URL=http://localhost:18080/kabusapi

    # OpenAI
    OPENAI_API_KEY=sk-...

    # LINE 通知（任意）
    LINE_CHANNEL_ACCESS_TOKEN=
    LINE_USER_ID=

---

## 使い方（主要スクリプト / コマンド）

パッケージがプロジェクト直下にある想定での実行例です。パッケージインストール済みの場合は -m で実行できます。

1) 監視ループを起動（SystemMonitor 単体実行）
- python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（monitoring DB は共通運用想定）。

2) ExecutionEngine（注文実行）を起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。

3) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- オプション:
  - --from YYYY-MM-DD
  - --to YYYY-MM-DD
  - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

4) Streamlit ダッシュボード（監視）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 SQLite を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

5) AI 機能（ライブラリ呼び出し）
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）

補足:
- 起動時に Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動削除する想定（設定で制御）。
- PID ファイル（Settings.pid_file_path）を使って ExecutionEngine の生存検査を行います。stale PID は検知されると削除され、リスクログが残ります。

---

## ディレクトリ構成（概要）

以下は主要なパッケージ・モジュールと役割の概観です（src/kabusys 以下）。

- __init__.py
  - パッケージメタ（__version__ 等）

- config.py
  - Settings：環境変数/.env の取り扱い、各パス・閾値の取得

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker）

- tools/
  - paper_verification_report.py : Paper Trading 検証レポート生成
  - __init__.py

- portfolio/
  - portfolio_builder.py : 候補選定・重み付け
  - position_sizing.py : 株数決定・aggregate cap
  - risk_adjustment.py : セクター上限・レジーム乗数
  - __init__.py

- monitoring/
  - monitoring_db.py : SQLite テーブル定義 + MonitoringDB クラス
  - system_monitor.py : システム・データ鮮度監視
  - trade_monitor.py : 注文滞留・価格異常監視
  - risk_monitor.py : ドローダウン・ポジション上限監視
  - kill_switch.py : kill.flag 管理
  - alert_manager.py : LINE 通知
  - monitoring_engine.py : まとめてポーリングする Engine
  - streamlit_dashboard.py : Streamlit ダッシュボード
  - __init__.py

- research/
  - factor_research.py : Momentum / Volatility / Value 等の計算
  - feature_exploration.py : 将来リターン・IC・統計
  - __init__.py

- ai/
  - news_nlp.py : raw_news → OpenAI → ai_scores
  - regime_detector.py : ETF MA200 + マクロセンチメント → market_regime
  - __init__.py

- execution/
  - order_manager.py, reconciler.py, ...（注文状態管理・復旧ロジック）
  - broker_factory / broker_api / order_repository など（ブローカー抽象化）

- utils/
  - process_priority.py : cross-platform のプロセス優先度 / CPU affinity 設定
  - __init__.py

- data/
  - （デフォルト DB・ファイル配置想定）data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など

---

## 運用上の注意点

- DB のマイグレーションは MonitoringDB.init_monitoring_db が冪等に行います（起動時に必要テーブルを作成）。
- Paper Trading と本番は SQLite ファイルを分離する設計です（PAPER_TRADING_SQLITE_PATH）。
- OpenAI 呼び出しはリトライと安全側フォールバック（失敗時はスコア 0 やスキップ）を実装していますが、API コスト／レート制限に注意してください。
- PID ファイルや kill.flag を用いたプロセス監視・停止機構があるため、それらのファイル操作権限・配置場所に注意してください。
- set_process_priority() は OS によって効果が異なり、権限不足などで設定に失敗する場合があります（ログに警告）。

---

## トラブルシュート（簡易）

- DB が見つからない / 開けない
  - paths（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を確認してください。streamlit は読み取り専用 URI を使用しています。
- OpenAI 未設定エラー
  - OPENAI_API_KEY を環境変数または関数引数で指定してください（news_nlp / regime_detector）。
- MONITOR_POLL_INTERVAL が無効
  - 正の整数を設定してください。無効な値はデフォルト 60 秒にフォールバックします。

---

この README はコードベースの主要点と運用方法にフォーカスしています。より詳しい設計（PortfolioConstruction.md / StrategyModel.md 等）やブローカー実装、細かい API 仕様は別ドキュメントを参照してください。追加で自動化・CI、デプロイ手順、テスト手順のテンプレート等が必要であれば教えてください。