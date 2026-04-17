# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」のコードベースです。  
本 README はプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買および関連ユーティリティ群を提供する Python パッケージです。  
主な要素は以下の通りです。

- Execution Engine: ブローカーとの発注・注文状態管理・リスク管理・自動復旧（Reconciler）
- Monitoring: システム・注文・リスク監視、アラート（LINE）送信、監視データの永続化
- Portfolio construction: 銘柄選定、重み計算、ポジションサイジング、セクター制限
- Research: ファクター計算（Momentum/Volatility/Value）や特徴量解析
- AI モジュール: ニュースの NLP による銘柄センチメント評価、レジーム判定（OpenAI を利用）
- ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボードなど

設定は環境変数（または .env / .env.local）で管理され、Settings クラス（kabusys.config）でラップされています。

---

## 機能一覧（抜粋）

- Execution
  - Broker クライアント作成（実口座 / ペーパートレーディング切替）
  - OrderManager による注文作成／同期
  - Reconciler による再起動時の自動リコンシリエーション
  - RiskManager によるリスク制御（上限・ドローダウン等）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの監視
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン、ポジション上限の監視（ダッシュボード更新、risk_logs 書込み）
  - KillSwitch: 条件に応じて flag ファイルを書き、ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Messaging API を用いた通知（クールダウン管理あり）
  - Streamlit による監視ダッシュボード
- Portfolio
  - 候補選定、等重・スコア重み、リスクベースの株数算出、セクター上限適用、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（mom/vol/value）、将来リターン、IC 計算、統計要約
- AI
  - news_nlp: raw_news -> OpenAI でセンチメントスコアを生成し ai_scores に保存
  - regime_detector: マクロ記事 + ETF MA200 乖離を組合せて日次レジーム判定
- ツール
  - paper_verification_report: Paper Trading の検証・集計レポート出力
  - streamlit_dashboard: 監視データの可視化

---

## セットアップ手順

以下は開発環境のセットアップ手順（一例）です。

1. Python バージョン
   - 推奨: Python 3.10+（コード上の型注釈や挙動を考慮）

2. 仮想環境作成（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate      # macOS/Linux
   .venv\Scripts\activate         # Windows
   ```

3. 必要パッケージのインストール（代表例）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   ※requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

注意:
- Settings は .env/.env.local をプロジェクトルートから自動ロードします。プロジェクトルートは .git または pyproject.toml を探索して決定されます。
- 自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要スクリプト）

以下は主要な起動・利用方法の例です。

1. Monitoring の起動
   - 監視ポーリングループを開始します（デフォルト 60 秒間隔）。
   - 環境変数で間隔を上書き可能: MONITOR_POLL_INTERVAL（秒）
   ```
   python -m kabusys.run_monitoring
   ```
   備考:
   - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
   - 停止にはプロジェクトルートの data/stop_requested.flag を作成するか Ctrl+C。

2. Execution Engine の起動
   - 実際の発注／エンジン実行を行います。paper_trading 環境時は MockBroker を使い、Paper 用 DB に記録します。
   ```
   python -m kabusys.run_execution
   ```
   備考:
   - KABUSYS_ENV=paper_trading の場合、`paper_sqlite_path` を使用して本番 DB と分離します。
   - 起動時に data/stop_requested.flag が存在すると起動を中止します。
   - PID ファイルは data/execution.pid（デフォルト）に書き込まれます。

3. Paper Trading 検証レポート生成
   - データベースから検証指標を集計して標準出力に出力します。
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - DB パスを指定する場合:
   ```
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```

4. Streamlit 監視ダッシュボード
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを入れておく必要があります。

5. AI / レジーム関連（プログラム内呼び出し）
   - ニューススコアリング:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB 接続を受け取り、OpenAI API キー（引数または環境変数 OPENAI_API_KEY）を参照します。

停止・強制終了フロー:
- ExecutionEngine を停止させたいときは data/kill.flag（Settings.kill_flag_path で変更可）を作成することで、Engine 側が検知して停止します（KillSwitch による自動発動もあり）。

ログレベル:
- 環境変数 LOG_LEVEL で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。Settings.log_level を通じてチェックされます。

---

## 主要設定（環境変数）まとめ

- KABUSYS_ENV: development | paper_trading | live（既定: development）
- SQLITE_PATH: 監視 DB（monitoring）パス（既定: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（既定: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（既定: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、既定 60）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 認証情報
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env の自動読み込みを無効化

Settings クラスは環境変数の検証や既定値を提供します。未設定の必須値は Settings が例外を投げます。

---

## ディレクトリ構成（抜粋・主要ファイル説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env の読み込みと Settings クラス
  - run_monitoring.py
    - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で調整）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 切替あり）
  - data/（実行時に使用する想定のデータディレクトリ。pid/flag/db を配置）
- src/kabusys/monitoring/
  - monitoring_db.py
    - SQLite のテーブル初期化 / MonitoringDB クラス（ログ永続化）
  - system_monitor.py
    - システム状態 / データ鮮度チェック
  - trade_monitor.py
    - 注文滞留 / 約定異常チェック
  - risk_monitor.py
    - ドローダウン / ポジション上限チェック
  - kill_switch.py
    - kill.flag の管理（Execution 停止シグナル）
  - alert_manager.py
    - LINE への通知（クールダウン管理）
  - monitoring_engine.py
    - 各 Monitor を束ねる実行ループ（テスト用 run_once と本番用 run）
  - streamlit_dashboard.py
    - Streamlit ベースの監視ダッシュボード
- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, ...
  - ブローカー API 抽象と注文管理、復旧ロジック
- src/kabusys/portfolio/
  - portfolio_builder.py
    - 候補選定、等重・スコア重み
  - position_sizing.py
    - 株数算出、単元丸め、aggregate cap 調整
  - risk_adjustment.py
    - セクターキャップ、レジーム乗数
- src/kabusys/research/
  - factor_research.py
    - momentum / volatility / value ファクター計算（DuckDB 経由）
  - feature_exploration.py
    - 将来リターン、IC、統計サマリー等
- src/kabusys/ai/
  - news_nlp.py
    - raw_news を集約して OpenAI へ送信、ai_scores に保存する処理
  - regime_detector.py
    - ETF MA200 とマクロ記事の LLM センチメントを合成して market_regime を書き込む
- src/kabusys/tools/
  - paper_verification_report.py
    - ペーパートレーディングの統計・判定レポート生成スクリプト
- src/kabusys/utils/
  - process_priority.py
    - プロセス優先度／CPU affinity 設定ユーティリティ（psutil 使用）

（上記は主要ファイルの抜粋です。詳細はソースコードを参照してください。）

---

## 運用上の注意

- Monitoring は Settings.sqlite_path（本番用の monitoring DB）を利用するため、開発環境で実行する場合は sqlite_path を明示的に切り替えてください。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用。ペーパートレードは本番 DB と物理的に分離して運用してください。
- process priority / cpu affinity の設定はプラットフォーム依存で失敗することがあり、その場合はログに警告が出ます（psutil の権限要件等）。
- OpenAI API を使用する機能は API キーの管理とコストに注意してください。API 呼び出しはリトライやフォールバック（失敗時はスコア 0 等）を備えていますが、十分なレート制限・エラー処理を検討してください。
- データの永続化（DB スキーマ）は init_monitoring_db() によるマイグレーション対応が一部実装されていますが、本番運用時はバックアップを推奨します。

---

## 貢献 / 開発のヒント

- .env.example を用意しておくと初期構築が容易になります（本リポジトリにはサンプルが無い場合があるため自分で作成してください）。
- DuckDB に投入する価格・財務データのスキーマは research モジュールに依存します。prices_daily / raw_financials / raw_news 等のテーブル形状に注意してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、明示的に環境を制御すると再現性が高まります。
- AI モジュールの外部呼び出し部分は関数単位で置換可能（テスト用に _call_openai_api を patch する等）。

---

この README はコードの主要な利用方法と構成をまとめたものです。詳細な API 仕様や各モジュールの設計文書（PortfolioConstruction.md / StrategyModel.md 等）がある場合は併せて参照してください。質問や補足があればお知らせください。