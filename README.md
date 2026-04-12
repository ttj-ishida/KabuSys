KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システムのコアライブラリ群を含みます。
実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ
（ファクター計算・特徴量解析）、および AI を使ったニュースセンチメント評価などの
主要コンポーネントで構成されています。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド / API 呼び出し例）
- 環境変数（主要なもの）
- ディレクトリ構成

プロジェクト概要
----------------
KabuSys は日本株の自動売買を目的としたモジュール群です。設計方針の概要は以下。

- モジュール化：execution / monitoring / portfolio / research / ai / tools に分割
- DB：
  - DuckDB を時系列データやリサーチ用に使用（デフォルト: data/kabusys.duckdb）
  - SQLite を監視・注文ログ等の永続化に使用（デフォルト: data/monitoring.db）
  - Paper Trading (KABUSYS_ENV=paper_trading) は本番 DB と分離（data/paper_trading.db）
- フェイルセーフ設計：監視やリコンシリエーションで部分障害を許容する実装
- LLM 統合：OpenAI を用いたニュースのセンチメント、レジーム判定機能（任意）

主な機能一覧
-------------
- execution
  - ExecutionEngine 起動処理（run_execution.py）
  - OrderManager / OrderRepository / Reconciler による発注管理と再同期（起動時リコンシリエーション）
  - RiskManager による発注制限
- monitoring
  - SystemMonitor：プロセス生存確認 / CPU・メモリ・ディスク監視 / データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常の監視
  - RiskMonitor：ドローダウン・ポジション上限監視（kill_switch と連携）
  - MonitoringEngine：各モニタを束ねてポーリング実行
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- portfolio
  - 候補選定、重み付け（等配分・スコア加重）、ポジションサイズ算出、セクター制限、レジーム乗数
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearmanランク相関）、統計サマリー
- ai
  - news_nlp.score_news: raw_news を LLM で評価して ai_scores に保存
  - regime_detector.score_regime: MA200 とマクロニュースで市場レジーム判定
- tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力

セットアップ手順
----------------
以下は一般的なローカルセットアップ手順です。

1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境を作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（requirements.txt がない場合は主要パッケージをインストール）
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて他パッケージを追加）

3. プロジェクトルートに .env を置く（自動読み込み）
   - config.Settings は .env と環境変数を参照します。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: 必須（Settings.jquants_refresh_token）
   - KABU_API_PASSWORD: 必須（kabuステーション用）
   - OPENAI_API_KEY: AI 機能を使う場合必須
   - 他はデフォルトがあるか任意。

使い方
------

1. 実行エンジン（ExecutionEngine）を起動
   - 本番／開発共通:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV 環境変数が paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録して本番 DB と完全に分離します。
     - 起動時にプロセス優先度を "high" に設定し、DB 接続・各種コンポーネントを初期化してセッションを実行します。

2. 監視ループを起動
   - python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト: 60）
     - 監視は環境にかかわらず本番 sqlite_path を使用して監視ログを保存します。

3. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で DB を開き、Overview / Positions / Orders / System タブを提供

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

5. AI 機能（プログラム内 API）
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key="...")

主要な環境変数
----------------
（Settings クラスで管理されるものの要約）

- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API（必須）
- OPENAI_API_KEY: OpenAI 利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の fill 挙動（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch フラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

重要な挙動メモ
---------------
- Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番）を使って監視ログを記録します。
- Execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使い本番 DB と切り離されます。
- init_monitoring_db() は冪等でテーブル作成と簡単なマイグレーションを行います（カラム追加確認など）。
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine の停止シグナルとして機能します（既に存在する場合は再書き込みしません）。
- set_process_priority() による優先度設定は OS に依存し、設定できない場合はログに警告を残してスキップします。

ディレクトリ構成（主なファイルと説明）
-------------------------------------
- src/kabusys/
  - __init__.py                  — パッケージ定義（バージョン等）
  - config.py                    — 環境変数 / Settings 管理（.env ロード機能含む）
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - execution/
    - order_manager.py           — 発注フロー / State Machine 外向き API
    - reconciler.py              — 起動時の自動復旧（Order / Position 突合）
    - (その他: broker_factory, order_repository, execution_engine 等)
  - monitoring/
    - monitoring_db.py           — SQLite 監視ログ保存層（テーブル作成・CRUD）
    - system_monitor.py          — システム状態 / データ鮮度監視
    - trade_monitor.py           — 注文滞留 / 約定異常監視
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - monitoring_engine.py       — 個別 Monitor を束ねるエンジン
    - alert_manager.py           — LINE Push 通知ユーティリティ
    - kill_switch.py             — kill.flag の書き込みロジック
    - streamlit_dashboard.py     — Streamlit ダッシュボード（監視用）
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算（等配分 / スコア配分）
    - position_sizing.py         — 発注株数計算（risk_based / equal / score）
    - risk_adjustment.py         — セクター制限・レジーム乗数
  - research/
    - factor_research.py         — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py     — 将来リターン計算・IC・統計サマリー
  - ai/
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI 統合）
    - regime_detector.py         — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - pipeline.py (参照あり)    — データパイプライン（get_last_price_date 等）
  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ

開発・運用上の注意
------------------
- DB ファイル（DuckDB / SQLite）は開発中にローカルに置く想定です。本番運用時は永続化・バックアップを検討してください。
- OpenAI や外部 API を使う機能は API キーが必要で、エラーやレート制限へはリトライやフォールバック（0 スコアなど）で耐性を持たせていますが、運用環境では監視とアラートの設定を推奨します。
- paper_trading モードは本番 DB を汚さないよう設計されています。検証時はこのモードを推奨します。
- streamlit ダッシュボードは監視 DB を読み取り専用で開くため、MonitoringEngine が先に起動している必要があります。

サンプル .env（最小例）
---------------------
以下は .env の例（実際の値は secrets を適切に設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=   # 任意
LINE_USER_ID=                 # 任意

お問い合わせ・拡張
-----------------
- 新しいブローカー実装や OrderRepository の拡張、lot_size の銘柄別対応などは既にコメントや TODO が残されています。モジュール単位で変更を組み込める設計になっています。
- テストで環境変数の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

以上が本リポジトリの README です。必要があれば、インストール用の requirements.txt、サンプル systemd ユニット、あるいはより詳しい運用手順（バックアップ・ログローテーション等）を追記できます。どの情報を優先して追加しますか？