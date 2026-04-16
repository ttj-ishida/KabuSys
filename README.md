# KabuSys

日本株自動売買システムの一部コンポーネント群（監視・実行エンジン・ポートフォリオ構築・リサーチ・AIユーティリティ等）。  
このリポジトリはモジュール単位で実行できるスクリプト・ライブラリ群を含み、ローカル SQLite / DuckDB をデータ層に利用します。

主な設計方針
- 本番／ペーパー（検証）環境を分離（KABUSYS_ENV により挙動切替）
- DuckDB を使ったファクター計算・リサーチ処理
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定（オプション）
- フラグファイルで外部から安全に停止指示を送れる（stop_requested.flag / kill.flag）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（実行例）
- 環境変数 / .env の説明
- ディレクトリ構成

---

## プロジェクト概要

このコードベースは以下の主要機能を実装しています（一部概念実装を含む）:

- ExecutionEngine 起動スクリプト（run_execution.py）：ブローカー接続、注文管理、リスク管理、リコンシリエーション等を組み立てて発注セッションを実行します。KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、paper_trading 用の SQLite DB に記録します。
- Monitoring（監視）：SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視を行い、監視ログを SQLite に保存、必要に応じて LINE 通知や kill.flag を発行します。run_monitoring.py はこの監視ループを起動します。
- Portfolio（銘柄選定・配分・ポジション決定）：候補選定、等配分／スコア加重、単元株丸め、セクター制限、レジーム乗数等の純粋関数群。
- Research（ファクター・特徴量探索）：DuckDB 上の prices_daily / raw_financials を利用したモメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン、IC 計算、統計サマリー。
- AI（ニュース NLP / レジーム判定）：OpenAI を呼ぶことでニュースセンチメントやマクロセンチメントを計算し、ai_scores / market_regime テーブルに保存します（APIキー必須）。
- ユーティリティ：プロセス優先度設定、Streamlit ダッシュボード、検証レポート生成スクリプト など。

---

## 機能一覧

- run_execution.py
  - ExecutionEngine 起動／PID 管理、ペーパートレード専用 DB 分離
  - BrokerClientFactory を用いた実際のブローカー or MockBroker の選択
  - Reconciler による再起動時の自動修復

- run_monitoring.py
  - SystemMonitor をポーリングして system_status を記録
  - MONITOR_POLL_INTERVAL でポーリング間隔変更可
  - stop_requested.flag による優雅な停止

- monitoring モジュール
  - MonitoringDB: SQLite テーブル作成 / マイグレーション / CRUD
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - AlertManager: LINE push による通知（設定があれば送信）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み（Execution 停止指示）

- tools
  - paper_verification_report: Paper Trading の検証レポート（稼働率、約定率、レイテンシなど）を生成

- ai
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄ごとの ai_score を生成して保存
  - regime_detector.score_regime: ETF ma200 とマクロセンチメントを合成して market_regime を作成

- research / portfolio
  - ファクター計算、特徴量解析、ポートフォリオ構成ロジック（等重／スコア重み／リスクベース等）
  - position sizing の細かいルール（lot 単位丸め、aggregate cap）

---

## セットアップ手順

1. Python 環境（想定: 3.10+）
   - 仮想環境を作成・有効化してください。

2. 必要パッケージ（例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （必要に応じて他パッケージ）
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

3. プロジェクトルートに .env を配置（任意）
   - リポジトリは起動時にプロジェクトルート（.git / pyproject.toml を探索）から `.env` / `.env.local` を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限設定が必要な環境変数は Settings クラスの required 項目を参照してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD などは実運用で必須）。

4. データディレクトリの準備
   - デフォルトの DB パス:
     - monitoring SQLite: data/monitoring.db
     - DuckDB: data/kabusys.duckdb
     - paper trading SQLite: data/paper_trading.db（paper_trading モード）
   - 起動時に自動で作成されることが多いですが、権限など注意してください。

---

## 使い方（実行例）

基本的な CLI 実行はモジュール実行形式を推奨します。

- 監視ループを起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - run_monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使用します。
  - 停止はプロセスの Ctrl+C またはプロジェクトルート/data/stop_requested.flag を作成することで優雅に終了します。

- 実行エンジンを起動（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient が使われ、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 停止は data/stop_requested.flag（プロジェクト root/data）を作成することでエンジンを停止できます。
  - Execution は起動時に PID ファイルを書きます（デフォルト: data/execution.pid）。

- Streamlit 監視ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 読み取り専用で DB を開き、ポートフォリオ / ポジション / 注文 / システム状態を表示します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを指定する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI モジュール（OpenAI API キー必要）
  - news_nlp / regime_detector は OPENAI_API_KEY 環境変数または api_key 引数からキーを受け取ります。
  - 例（スクリプトまたは REPL から）:
    ```
    from kabusys.ai.news_nlp import score_news
    score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## 環境変数（主なもの）

- KABUSYS_ENV
  - 有効値: development | paper_trading | live
  - デフォルト: development

- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb

- SQLITE_PATH
  - Monitoring 用 SQLite（デフォルト: data/monitoring.db）

- PAPER_TRADING_SQLITE_PATH
  - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

- PAPER_FILL_MODE
  - paper_trading の模擬約定挙動。instant | partial | never | reject（デフォルト: instant）

- OPENAI_API_KEY
  - news_nlp / regime_detector などで使用

- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 実運用で必要（Settings にて必須チェック）

- LOG_LEVEL
  - DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - PID / kill flag のパスや起動時の挙動に関する設定

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。デフォルト 60。0 以下や不正な値は無視されデフォルトにフォールバック。

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env 自動読み込みを無効化します（テスト用途など）

---

## 停止・安全機構

- stop_requested.flag
  - run_monitoring.py / run_execution.py はプロジェクト root/data/stop_requested.flag の存在を監視し、見つかれば優雅に終了します。

- kill.flag
  - KillSwitch（監視ロジック）が致命的リスク（ドローダウン超過 等）を検知した場合、Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine はこの flag を検出して停止します。

---

## DB マイグレーション / 初期化

- monitoring.monitoring_db.init_monitoring_db(conn)
  - 起動時に必要な監視テーブル（system_status / trade_logs / positions / risk_logs / dashboard）とインデックスを冪等で作成します。既存テーブルに欠損カラムがある場合は簡易的な ALTER を行うマイグレーション処理があります（例: latency_ms, peak_value の追加）。

---

## ディレクトリ構成（主要部分）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込みと Settings
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py             — MonitoringDB（SQLite テーブル定義・操作）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ・・・（ブローカー / engine / repository 等の実装が含まれる想定）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - data/                          — 既定の DB / フラグファイルを置く想定ディレクトリ（ランタイム生成される）

---

## 開発メモ / 注意点

- OpenAI 周りはネットワーク／レート制限に対しエクスポネンシャルバックオフ・堅牢なバリデーションを行う設計ですが、API キーと料金に注意して利用してください。
- paper_trading モードは「本番 DB と完全分離」することを重視しています。常に PAPER_TRADING_SQLITE_PATH を確認してください。
- process priority / CPU affinity の設定はプラットフォーム依存（psutil を経由）です。権限不足時は警告を出してスキップします。
- DuckDB 問い合わせは SQL を多用しており、テーブル命名（prices_daily, raw_financials, raw_news など）に依存します。データスキーマに合わせてデータを投入してください。

---

必要であれば、.env.example のテンプレートやよくあるトラブルシュート項目（OpenAI エラー、DB ロック、権限問題など）を追加します。どの部分を詳しくドキュメント化したいか教えてください。