# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 実行スクリプト群）。

このリポジトリは、シグナル処理・ポートフォリオ構築・発注管理・監視・AI ベースのニュースセンチメント評価などを含む、トレーディングシステムのコンポーネント群を提供します。

---

## プロジェクト概要

- 「KabuSys」は日本株の自動売買を想定したモジュール群です。
- コア機能は以下のレイヤーに分かれます：
  - execution: 注文管理、ブローカーインタフェース、リコンシリエーション、リスク管理、ExecutionEngine。
  - portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限。
  - monitoring: システム稼働監視、注文監視、リスク監視、アラート（LINE）送信、監視DB、ダッシュボード。
  - research: ファクター算出、特徴量解析、IC 計算等（DuckDB を用いた時系列分析）。
  - ai: ニュースセンチメント評価（OpenAI API を利用）やレジーム判定。
  - tools: 検証レポート生成などの CLI ツール。
  - utils: OS 関連ユーティリティ（プロセス優先度・CPU affinity 等）。
- 設定は環境変数（.env / .env.local の自動読み込みあり）で行います。設定ロジックは `kabusys.config.Settings` が担当します。

---

## 主な機能一覧

- 実行（Execution）
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - BrokerClientFactory 経由で実際のブローカー or MockBroker（paper_trading）を切り替え
  - 起動時のリコンシリエーション（Reconciler）

- ポートフォリオ構築（Portfolio）
  - 候補選定（スコア降順）、等金額・スコア重み配分
  - セクター集中制限、レジーム乗数
  - ポジションサイズ計算（リスクベース / 等分配 / スコアベース）

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセスの監視、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じてフラグファイルを書き ExecutionEngine を停止
  - AlertManager：LINE Push によるアラート送信（クールダウン機能）
  - Streamlit ベースの監視ダッシュボード（read-only）

- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Spearman）や統計サマリ

- AI（OpenAI）
  - ニュースを集約して銘柄ごとにセンチメントを付与（ai_scores テーブルへ書き込み）
  - マクロ記事を用いた市場レジーム判定（market_regime テーブルへ書込）

- ツール
  - Paper Trading 検証レポート生成（paper_verification_report）

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を準備してください。

2. 必要なライブラリをインストールしてください（例）:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   - 実行環境によっては追加のパッケージが必要になる場合があります。

3. プロジェクトルートに `.env`（必要な環境変数を定義）を作成できます。
   - 自動ロードはデフォルトで有効です。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 自動ロードの順序: OS 環境 > .env.local（上書き） > .env（未設定キーのみ）

4. 重要な環境変数（一例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須のケースあり）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須のケースあり）
   - OPENAI_API_KEY: OpenAI を使う機能（ai.score_news / score_regime）に必須
   - KABUSYS_ENV: execution の動作モード（development | paper_trading | live）
     - paper_trading の場合、MockBroker を使用し DB は分離（PAPER_TRADING_SQLITE_PATH）
   - PAPER_FILL_MODE: paper_trading 時の約定動作（instant | partial | never | reject）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite DB パス（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は送信をスキップ）
   - PID_FILE_PATH / KILL_FLAG_PATH: pid / kill flag のパス（デフォルトは data/ 以下）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）

5. データベース
   - 監視関連テーブルは起動スクリプト内で自動で初期化されます（init_monitoring_db）。
   - DuckDB 側は prices_daily / raw_financials / raw_news / news_symbols などのテーブルが想定されます。これらは別途投入してください（調査 / 研究用途）。

---

## 使い方

基本的にパッケージモジュールとして提供されるスクリプトを Python で実行します。

- ExecutionEngine を起動（本番 / paper_trading 切替は KABUSYS_ENV）
  ```
  python -m kabusys.run_execution
  ```
  - paper_trading モード例:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 起動時にプロセス優先度を「high」に設定します（psutil の権限制限により失敗することがありますが無害）。

- Monitoring のポーリングループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path（Settings().sqlite_path）を使用します（環境にかかわらず）。

- Streamlit ダッシュボード（監視の可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - `--db` で SQLite のパスを指定（デフォルト: data/monitoring.db）。
  - read-only で DB を開きます（存在しない場合はエラー表示）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH で指定している場合は省略可）。
  - 出力は標準出力にレポートを印字します（稼働率、注文成功率、レイテンシ等）。

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY または関数引数）。
  - DuckDB に raw_news / news_symbols / ai_scores / market_regime / prices_daily 等のテーブルが必須です。
  - 例: Python コード内から呼び出す
    ```py
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")
    ```

---

## 重要な挙動・注意点

- paper_trading モードは本番 DB と分離され、デフォルトで data/paper_trading.db を使用します。安全にローカルで動作確認できます。
- Settings は起動時に .env / .env.local を自動読み込みしますが、OS 環境変数が優先され、.env.local は .env を上書きします。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- モジュールの多くは DuckDB 接続を受け取り SQL でデータを取得します。事前に DuckDB ファイルの準備（prices_daily 等のテーブル作成）が必要です。
- OpenAI 呼び出しは再試行やエラーハンドリングが組み込まれているものの、APIキー未設定やリクエスト上限等でスコア取得に失敗することがあります。失敗時はスキップ・フォールバックする実装です。
- プロセス優先度や CPU affinity の設定は OS に依存し、権限不足で失敗する場合があります（ログに警告が出ますが処理は継続されます）。
- KillSwitch は `KILL_FLAG_PATH` にファイルを書き、ExecutionEngine 側がそれを検出して安全停止する想定です。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリ内の主要なモジュールとファイル（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数読み込み / Settings
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity ヘルパ
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - ... (ブローカー & API 関連)
  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
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

（注）実際のリポジトリにはさらに細かい実装ファイルや依存ファイルが存在する場合があります（例: data パス、DuckDB テーブル作成スクリプトなど）。

---

## 開発時のヒント

- 設定の検証は `kabusys.config.Settings` を直接インポートして確認できます。
- 監視 DB の初期化は `init_monitoring_db(sqlite_conn)` を呼ぶことで冪等に実行されます。起動スクリプトでも行われます。
- テスト用にモジュール単体（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine.run_once）を使って動作確認が可能です。
- OpenAI 周りは外部 API 呼び出しを含むため、ユニットテスト時は `_call_openai_api` 等をモックしてください（コード内で想定されている箇所があります）。

---

必要であれば、環境変数例（.env.example 形式）や起動手順のハンズオン（サンプル .env、DB 初期化スクリプト、DuckDB のテーブル作成 SQL）を別途作成します。どの部分を優先して欲しいか教えてください。