# KabuSys — README (日本語)

このリポジトリは日本株向け自動売買システム「KabuSys」の一部コンポーネント群です。
本 README はコードベース（src/kabusys 以下）を対象に、概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

注意：これはプロジェクト全体の抜粋ドキュメントです。実運用前にテスト環境で十分な検証を行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支えるモジュール群で、主に以下の機能を含みます。

- 注文管理 / 発注（ExecutionEngine, OrderManager, BrokerClientFactory 等）
- リコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine）
- 監視データ保存（SQLite ベースの monitoring DB）
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
- リサーチ機能（ファクター計算・特徴量解析）
- ニュース NLP（OpenAI を用いたニュースのセンチメント解析）
- Market Regime 判定（AI と価格指標の合成）
- 運用補助ツール（Paper Trading レポート生成、Streamlit ダッシュボード）

設計上のポイント：
- DuckDB を用いた価格・ファイナンスデータ解析（リサーチ領域）
- SQLite を用いた監視ログ（monitoring.db）および、paper_trading 用の分離 DB（data/paper_trading.db）
- Paper Trading（KABUSYS_ENV=paper_trading）時はブローカー呼び出しをモックし、本番 DB と分離
- OpenAI 呼び出しは堅牢化（バッチ、リトライ、レスポンス検証）済み

---

## 主な機能一覧

- run_monitoring: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を記録
- run_execution: ExecutionEngine を起動して当日の売買セッションを実行（paper_trading は専用 DB に記録）
- monitoring: SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, AlertManager（LINE 通知）
- monitoring_db: 監視用 SQLite スキーマ初期化と操作ラッパー（MonitoringDB）
- portfolio: 候補選定、重み付け、セクター制限、ポジションサイズ計算の純粋関数群
- research: ファクター計算（momentum/value/volatility）・特徴量探索・IC 計算
- ai: news_nlp（ニュースセンチメントのスコア化）、regime_detector（市場レジーム判定）
- tools: paper_verification_report（Paper Trading の検証レポート生成）、Streamlit ダッシュボード
- utils: process_priority（プロセス優先度・CPU affinity 設定）などユーティリティ

---

## セットアップ手順（開発 / 簡易）

以下はローカルでの簡易セットアップ手順です。実運用環境に合わせて適宜調整してください。

1. Python（3.9+ 推奨）を用意
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（代表例）
   - pip install duckdb psutil requests openai streamlit

   ※実プロジェクトでは requirements.txt / pyproject.toml に依存関係をまとめて使用してください。

4. プロジェクトルートに .env を用意（自動ロード機能あり。詳細は下記）
   例 (.env.example 相当):
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - KABUSYS_ENV=development   # development | paper_trading | live
   - PAPER_FILL_MODE=instant  # instant | partial | never | reject
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...

   自動ロード:
   - デフォルトでプロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化可能。

5. データディレクトリを作成
   - mkdir -p data

6. DB スキーマ初期化は run スクリプト実行時に自動で行われます（monitoring_db.init_monitoring_db）。

注意: psutil の一部機能（プロセス優先度の設定や cpu_affinity）は権限が必要な場合があります。Windows / Linux の差分は utils/process_priority.py が吸収します。

---

## 使い方（主要スクリプト・コマンド）

※パッケージを直接使う想定（ソースツリー直下で Python モジュールとして実行可能）

1. 監視ループ起動（SystemMonitor をポーリング）
   - 環境変数: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
   - 実行:
     - python -m kabusys.run_monitoring
   - 補足:
     - 監視は常に設定の sqlite_path（本番 DB）を使用します（環境に依らず）。
     - プロセス優先度を "high" に設定しようとします（psutil 必須）。

2. 実行エンジン起動（ExecutionEngine）
   - Paper Trading 時は環境変数 KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と完全分離されます。
   - 実行:
     - python -m kabusys.run_execution

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - --db /path/to/paper_trading.db
   - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

4. Streamlit ダッシュボード（監視用）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視 DB を read-only モードで開き、ポートフォリオ / 注文履歴 / システム状況等を表示します。

5. AI 関連（プログラムから呼ぶ）
   - ニューススコア作成:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key="...")  # returns written count
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn=duckdb_conn, target_date=date(2026,4,1), api_key="...")

   OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY を使用します。API レスポンスのバリデーション・リトライが組み込まれています。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）。既定は development
- PAPER_FILL_MODE — paper_trading 時のモック約定振る舞い（instant|partial|never|reject）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH — kill.flag パス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動で削除するか（"1" で有効）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

設定は .env / .env.local / OS 環境変数からロードされます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 実運用上の注意点

- Paper Trading と live は DB が分離されます（paper_trading は PAPER_TRADING_SQLITE_PATH を使用）。
- Process priority / CPU affinity の設定は psutil を用いて行います。アクセス権限や OS により設定できない場合があります（警告ログのみ）。
- OpenAI 呼び出しはレート制限やネットワーク障害を想定したリトライロジックが入っていますが、API コストや応答の堅牢性を考慮し運用してください。
- KillSwitch（data/kill.flag）を使うことで外部から ExecutionEngine の停止指示を出せます。KillSwitch は RiskMonitor の判定（ドローダウンやポジション上限）で発動されることがあります。
- MonitoringDB のスキーマは init_monitoring_db() で自動的に作成・簡易マイグレーションされます。既存 DB に対する変更は注意して扱ってください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル / モジュールの概要ツリーです。

- src/
  - kabusys/
    - __init__.py
    - config.py                       # 環境変数 / 設定読み込み
    - run_monitoring.py               # SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py                # ExecutionEngine 起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py           # プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py              # SQLite スキーマ + MonitoringDB クラス
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py              # LINE 通知
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他: broker_factory, execution_engine, order_repository 等)
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
      - __init__.py
      - paper_verification_report.py

（注）上記はリポジトリ内の代表モジュールを抜粋しています。実行に必要な追加モジュールや依存ファイルが別途存在する可能性があります。

---

## 追加リソース / 参考

- .env の書式・パースにはコメントやクォートを考慮した独自パーサを使用します（config.py内）。
- Paper Trading の検証基準やポートフォリオ構築ロジックにはドメイン知識を含むコメントが豊富にあります（PortfolioConstruction.md 等に準拠）。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを溜めてください。

---

ご不明点や README に追記してほしい点（例：具体的な .env.example、リリース手順、CI 設定など）があれば教えてください。必要に応じてサンプル .env や運用チェックリストも作成します。