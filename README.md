# KabuSys — README

本リポジトリは日本株向け自動売買システム「KabuSys」の一部モジュール群を含みます。  
この README はコードベースから抽出した使い方・セットアップ手順・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた日本株自動売買基盤のモジュール群です（コードは一部抜粋）:

- 注文作成・送信・状態管理（Execution）
- 注文のリコンシリエーション（起動時の自動復旧）
- リスク管理（ドローダウン監視・ポジション上限等）
- 監視（システム稼働／データ鮮度／注文滞留／約定異常の検出）
- 監視データの永続化（SQLite）
- ポートフォリオ構築（候補選定・重み算出・株数算出）
- リサーチ用ファクター計算（DuckDB を使った価格・財務データ処理）
- AI モジュール（OpenAI を使ったニュースのセンチメント、レジーム検出）
- 監視ダッシュボード（Streamlit）
- 紙上（Paper Trading）向け検証レポート生成ツール

設計上のポイント:
- DuckDB と SQLite を使い、履歴分析と監視ログを分離
- 環境変数 / .env による設定管理（自動読み込みあり）
- 本番/ペーパー環境の分離（paper_trading の DB は別ファイル）
- LLM 呼び出しは失敗耐性（リトライ、フォールバック）を持つ

---

## 機能一覧

- Execution
  - Broker クライアントの抽象化（実環境 / Mock）
  - OrderManager（状態遷移、重複検知）
  - Reconciler（再起動後の注文・ポジション同期）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定価格の異常検出
  - RiskMonitor: ドローダウンやポジション上限の監視、ダッシュボード更新
  - KillSwitch: 条件達成時にフラグファイルを書き ExecutionEngine を停止させる
  - AlertManager: LINE Push による通知（クールダウン機能あり）
  - Streamlit ダッシュボード（読み取り専用で監視情報を可視化）
- Portfolio
  - 候補選定、等金額・スコア重み、セクター制限、レジーム乗数、株数計算（単元丸め、資金キャップ）
- Research
  - Momentum / Volatility / Value のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースの銘柄別センチメントスコア生成（OpenAI）
  - 市場レジーム判定（MA200 とマクロニュースの合成、OpenAI）
- ツール
  - Paper Trading の検証レポート生成スクリプト

---

## 動作環境・依存関係（概略）

- Python 3.9+（型注釈に Path | None などを使用）
- 主要ライブラリ（抜粋）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- 標準ライブラリ: sqlite3, logging, datetime, os, time など

実際の requirements.txt は本リポジトリに含まれていない可能性があるため、上記パッケージを適宜インストールしてください。

---

## セットアップ手順

1. Python 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージのインストール（例）
   ```
   pip install duckdb psutil requests openai streamlit
   ```

3. データディレクトリ作成
   ```
   mkdir -p data
   ```
   デフォルトの DB は `data/kabusys.duckdb`（DuckDB）と `data/monitoring.db`（SQLite）です。

4. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須環境変数（一部）
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須で参照箇所あり）
   - KABU_API_PASSWORD — kabuステーション API パスワード（Execution）
   - OPENAI_API_KEY — OpenAI API を使う機能（ai.score_news / score_regime）
   - KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト: development）
   - その他任意設定（下記「環境変数一覧」参照）

6. 初回起動時
   - 監視 DB スキーマは起動スクリプト内で自動作成されます（init_monitoring_db は冪等）。

---

## 環境変数（主なもの）

- 一般
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動読み込みを無効化

- API / 認証
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- DB パス / モード
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring は常にこの本番パスを使用
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading 時に Execution が使用
  - PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動）

- 監視 / 実行
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (1/0)
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- 閾値
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

（必要に応じて .env.example を作成して下さい）

---

## 実行方法（主要スクリプト）

- 監視ループ（SystemMonitor を起動）
  - 環境変数: MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 注意: Monitoring は KABUSYS_ENV に関係なく `sqlite_path`（本番パス）を使用します。

- Execution エンジン（注文処理）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。

- Streamlit ダッシュボード（読み取り専用）
  - 実行例:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - read-only URI を使って SQLite をオープンします。MonitoringEngine を起動していない場合は DB が存在しない旨を表示します。

- Paper Trading 検証レポート（ツール）
  - 実行:
    ```
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

---

## ライブラリAPI（主な公開関数の利用例）

- AI モジュール（ニューススコア、レジーム判定）
  - score_news:
    ```
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=datetime.date(2026,4,11), api_key="sk-...")
    ```
    - 戻り値: 書き込みた銘柄数（int）
    - OpenAI API キーは引数か環境変数 OPENAI_API_KEY を使用

  - score_regime:
    ```
    from kabusys.ai.regime_detector import score_regime
    count = score_regime(conn, target_date=datetime.date(2026,4,11), api_key="sk-...")
    ```

- Research モジュール（DuckDB 接続必須）
  - calc_momentum, calc_volatility, calc_value:
    ```
    from kabusys.research import calc_momentum
    rows = calc_momentum(conn, target_date)
    ```

---

## 重要な挙動メモ

- .env の自動読み込み
  - プロジェクトルートに `.env` と `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先され、.env.local は上書き）。
  - テストなどで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- DB 初期化 / マイグレーション
  - monitoring_db.init_monitoring_db(conn) は冪等でテーブルを作成し、既存 DB に対し必要なカラム追加（簡易マイグレーション）を行います。

- Monitoring と Execution の DB 分離
  - 監視（Monitoring）は常に `SQLITE_PATH`（data/monitoring.db）を使用。
  - Execution は `KABUSYS_ENV=paper_trading` のとき `PAPER_TRADING_SQLITE_PATH` を使用して本番 DB と完全に分離。

- Kill Switch
  - 条件達成時に `KILL_FLAG_PATH` に文字列を書き込み、ExecutionEngine 側が検出して停止する想定です。
  - 既にフラグがある場合は上書きしません（冪等）。

---

## ディレクトリ構成（抜粋）

（プロジェクトの src/kabusys 以下の主要ファイル・モジュールの一覧）

- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 broker, engine, order_repository 等のモジュール想定)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py
  - data/ (想定: DuckDB/SQLite ファイルを置くディレクトリ)

この README はコードベースから抽出した情報に基づいています。実際に運用する際は各モジュールの詳細実装（broker 実装、ExecutionEngine 実装、データ取得パイプライン等）およびセキュリティ（APIキーの保護）を確認・補完してください。

必要であれば、README に含めるサンプル .env.example、requirements.txt、起動スクリプトの systemd / supervisor 用ユニット例なども作成できます。どの情報を追加しますか？