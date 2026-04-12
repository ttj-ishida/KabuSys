# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ兼実行スクリプト群）です。本リポジトリには以下の主要機能が含まれます: 注文実行エンジン、監視（モニタリング）サブシステム、ポートフォリオ構築ユーティリティ、研究用ファクター計算、ニュースの NLP スコアリング（OpenAI）など。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントを分離して実装したモジュール群です。主な設計方針は以下の通りです。

- モジュール化：Execution / Monitoring / Portfolio / Research / AI 等を分離。
- DB レイヤ：SQLite（監視・paper_trading 用）と DuckDB（時系列・分析用）を併用。
- フェイルセーフ設計：監視→Kill Switch、柔軟な DB パス、リトライ・バックオフ等。
- テストしやすさ：多くの関数は純粋関数または DB 接続を注入する設計。

バージョン: 0.1.0

---

## 機能一覧

- Execution
  - ExecutionEngine（起動スクリプト: kabusys.run_execution）
  - ブローカー抽象化（BrokerClientFactory）により本番/ペーパー両対応
  - OrderManager / OrderRepository / Reconciler による自動リコンシリエーション
  - RiskManager（発注前チェック、サーキットブレーカー等）

- Monitoring
  - SystemMonitor：プロセス生存・CPU/メモリ/ディスク監視、データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：フラグファイルで ExecutionEngine 停止指示
  - AlertManager：LINE Push による通知（クールダウン管理）
  - MonitoringEngine / run_monitoring 起動スクリプト
  - streamlit による監視ダッシュボード（streamlit_dashboard.py）

- Portfolio
  - 候補選定、等金額/スコア重み、リスク調整（セクター上限・レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap、cost buffer）

- Research
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC / ランク変換、統計サマリー

- AI
  - news_nlp: OpenAI を使ったニュースセンチメント集計 → ai_scores に書込み
  - regime_detector: ma200 とマクロセンチメントを合成して market_regime を判定

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 前提・依存

開発時点での想定（実行環境に合わせて調整してください）:

- Python 3.10+
- 必要な外部パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準ライブラリで利用）

requirements.txt は本リポジトリに含まれていないため、上記パッケージを適宜インストールしてください。

例:
pip install duckdb psutil openai requests streamlit

---

## 環境変数（主なもの）

設定は OS 環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

重要な環境変数（一部）:

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ書き込みます。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE通知用（AlertManager）
- SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject）

Settings クラスで値検証を行います。不正な値は起動時に例外になります。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   git clone <repo_url>
   cd <repo_dir>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows の場合 .venv\Scripts\activate

3. 依存パッケージをインストール
   pip install duckdb psutil openai requests streamlit

   （必要に応じて他のパッケージも追加してください）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、シェル環境でエクスポートしてください。
   - 例（簡易）:
     KABUSYS_ENV=paper_trading
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

   自動ロードはプロジェクトルートの検出（.git または pyproject.toml）を元に行われます。

5. データフォルダ準備
   デフォルトでは data/ 配下に DB・PID・フラグ等が作成されます。必要に応じて作成してください。
   mkdir -p data

6. DuckDB / SQLite ファイルは初回起動時に自動で必要なテーブルが作成されます（init_monitoring_db が実行されます）。

---

## 使い方（主なコマンド）

- ExecutionEngine を起動（本番または paper_trading に応じて挙動が変わります）
  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され data/paper_trading.db に記録します（本番 DB と分離）。

- Monitoring を起動（ポーリングループ）
  python -m kabusys.run_monitoring

  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず monitoring DB は production path を使う設計）。

- Paper Trading 検証レポートを生成
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- 監視ダッシュボード（Streamlit）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 関連（プログラムから関数を呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

  これらは DuckDB 接続や OpenAI API キーを引数で渡して利用できます。

- その他ユーティリティ
  - プロセス優先度の設定: kabusys.utils.process_priority.set_process_priority("high")
  - 設定読み取り: from kabusys.config import Settings; settings = Settings()

---

## 実運用時の注意点

- データ鮮度チェックや PID ファイルの存在チェックなど、監視・実行系で安全処理が組み込まれていますが、実運用ではさらに監視・バックアップ・アラート設定を行ってください。
- OpenAI を利用する機能は API コストが発生します。API キーの権限と利用量に注意してください。
- paper_trading モードは本番口座と完全分離する設計ですが、設定ミスに備えて環境変数と DB パスを必ず確認してください。
- .env の自動読み込みはプロジェクトルートの検出に依存します。意図せず別ディレクトリで実行すると環境変数が読み込まれない場合があります。

---

## ディレクトリ構成（主要ファイルと説明）

（root の src/kabusys 下構成）

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス：環境変数の検証・デフォルト値管理。自動で .env / .env.local を読み込む。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。KABUSYS_ENV によりペーパー/本番切替。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔変更可。
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
    - ブローカー抽象化、発注ロジック、リコンシリエーション等を含む。
  - monitoring/
    - monitoring_db.py — SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルを使った停止指示
    - alert_manager.py — LINE push 通知（クールダウン有り）
    - monitoring_engine.py — 各監視を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの簡易ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 発注株数決定、スケールダウンロジック等
  - research/
    - factor_research.py — ファクター計算（Momentum/Volatility/Value）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - ai/
    - news_nlp.py — raw_news を OpenAI で解析し ai_scores へ書き込む処理
    - regime_detector.py — ma200 とマクロセンチメントから市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## よくある問い（FAQ）

- Q: .env のロード順は？
  - A: OS 環境変数 > .env.local > .env の順で読み込みます（.env.local は .env を上書き）。既に存在する OS 環境変数は保護されます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Q: Monitoring DB のテーブルは自動作成されますか？
  - A: はい。run_monitoring や run_execution 内で init_monitoring_db が呼ばれ、必要なテーブル・インデックス・マイグレーションを実行します。

- Q: paper_trading と本番の DB は分離されていますか？
  - A: はい。KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を優先して接続します（デフォルト: data/paper_trading.db）。

---

README は以上です。必要であれば下記の追加ドキュメントを作成できます。

- 詳細なデプロイ手順（systemd / supervisor / Docker / Kubernetes 用構成例）
- API リファレンス（各モジュールの公開関数一覧）
- 開発ガイド（ユニットテストの実行方法、モック方法）