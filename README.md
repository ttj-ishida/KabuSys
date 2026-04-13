# KabuSys

日本株自動売買システムの軽量実装。戦略の研究・ファクター計算、ポートフォリオ構築、注文実行、監視・アラート、Paper Trading 検証用ツール群を含みます。

以下はこのリポジトリの README です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤（研究 → 発注 → 監視）を想定したモジュール群です。主な目的は次のとおりです。

- DuckDB / SQLite を用いた市場データ・ログの集計・永続化
- ファクター計算、特徴量探索（研究用ユーティリティ）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）
- ExecutionEngine / Broker 抽象化による発注・リコンシリエーション
- 監視（System / Trade / Risk）、LINE によるプッシュ通知、Streamlit ダッシュボード
- Paper Trading 用の検証レポート生成および AI（OpenAI）を使ったニュースセンチメント / レジーム判定

設計方針として、各機能は可能な限り副作用を抑えた純粋関数或いは小さな責務に分割されています。環境変数 / .env による設定を行います。

---

## 主な機能一覧

- research
  - ファクター計算: Momentum / Volatility / Value（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリ

- portfolio
  - 銘柄選定（スコア/等分）、スコア重み付け
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- execution
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - Reconciler による起動時の同期（ブローカーとの突合）
  - BrokerFactory を通じた実ブローカー / モックの切替（paper_trading サポート）

- monitoring
  - SystemMonitor, TradeMonitor, RiskMonitor
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - KillSwitch（フラグファイルによる ExecutionEngine 停止）
  - AlertManager（LINE プッシュ通知）
  - Streamlit ベースの監視ダッシュボード

- ai
  - news_nlp: OpenAI を用いたニュースセンチメント集約と ai_scores 書き込み
  - regime_detector: ETF MA200 とマクロニュースの LLM センチメント合成によるレジーム判定

- tools
  - paper_verification_report: Paper Trading の検証レポート出力（稼働率・注文成功率・レイテンシ等）

---

## セットアップ手順

前提: Python 3.9+（プロジェクトで明記はありませんが、型注釈により Python 3.9+ を想定）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 必要パッケージをインストール

   requirements.txt がない場合の例（本実装で参照している主なライブラリ）:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

   追加でテスト・開発用に必要なパッケージがあれば適宜インストールしてください。

4. 環境変数 / .env の用意

   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` や `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数例（.env）:
   ```
   KABUSYS_ENV=development          # development | paper_trading | live
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...               # AI 機能を使う場合必須
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PAPER_FILL_MODE=instant         # instant | partial | never | reject
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   LOG_LEVEL=INFO
   LINE_CHANNEL_ACCESS_TOKEN=...   # 監視アラートを LINE で送る場合
   LINE_USER_ID=...
   ```

   注意:
   - Paper Trading は `KABUSYS_ENV=paper_trading` に設定すると mock ブローカーが使われ、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に分離されます。
   - `MONITOR_POLL_INTERVAL` 環境変数で監視ポーリング間隔（秒）を上書きできます（デフォルト: 60）。

5. データベース初期化
   - 実行スクリプト（監視 / 実行）を起動すると `init_monitoring_db` が呼ばれて必要なテーブルが作成されます。別途手動でスクリプトを用意する必要はありません。

---

## 使い方（主なコマンド）

- Monitoring（監視ループ）の起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング秒数を変更可（例: `MONITOR_POLL_INTERVAL=30`）。
  - 監視は常に本番用 `sqlite_path` を使用します（KABUSYS_ENV に依らず本番 DB を参照）。監視 DB を分離したい場合は設定を調整してください。

- ExecutionEngine（注文実行）の起動
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使用され、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録されます。
  - 起動時に `kill.flag` のクリーンアップや PID ファイル更新等を行います（Settings を参照）。

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only URI で SQLite を開きます。MonitoringEngine が書き込んでいる DB を指定してください。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` を省略すると `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db` を参照します。
  - 出力は稼働率・注文成功率・レイテンシ等のサマリと PASS/FAIL 判定です。

- AI 機能（ニューススコア / レジーム判定）
  - 環境変数 `OPENAI_API_KEY` を設定してから、該当モジュールを呼び出してください（例: スケジュールされたジョブやスクリプトから）。
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 設定（主要な環境変数）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値（%）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE プッシュ）設定

設定は .env/.env.local に記述するか、OS 環境変数で指定してください。Settings モジュールが自動でプロジェクトルートの .env を読み込みます（自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## 動作上の注意点 / 実装上のポイント

- ProcessPriority: 起動スクリプトは最初にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限がないと警告が出てスキップされます。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブルと一部カラムの追加移行を行います。
- KillSwitch: kill.flag を作成すると ExecutionEngine 停止を促す仕組み。KillSwitch は冪等で既に存在する flag を再書き込みしません。
- Paper Trading: 本番 DB と確実に分離されるよう、`KABUSYS_ENV=paper_trading` 時は paper 用 SQLite を使用します。
- AI 呼び出し: OpenAI API を使用する箇所はエラーに対してフェイルセーフ（失敗時はスコア 0.0 などで継続）になっています。429 や一時エラーは指数バックオフでリトライします。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env ロードと Settings
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py          — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 永続化（テーブル定義 / CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ... (broker API 抽象・factory 等)
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
  - data/
    - pipeline.py (参照元あり)
    - stats.py (zscore_normalize 等、research で利用)
  - tools/
    - paper_verification_report.py
    - __init__.py

ドキュメントや設計ノート（PortfolioConstruction.md, StrategyModel.md 等）はコード内コメントや別ドキュメントとして参照する想定です。

---

## 例: 開発時の簡単な流れ（Paper Trading）

1. .env をセットアップ（あるいは環境変数を設定）
   - KABUSYS_ENV=paper_trading
   - OPENAI_API_KEY=...
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

2. 実行エンジンを起動（Mock broker により DB に発注ログが残る）
   ```
   python -m kabusys.run_execution
   ```

3. 監視を起動（別プロセス）
   ```
   python -m kabusys.run_monitoring
   ```

4. 発注・約定ログを確認 / 検証レポート出力
   ```
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
   ```

5. Streamlit でダッシュボードを開く
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

---

## 貢献・拡張案

- Broker 実装の追加（実ブローカー API 実装）
- 単元株数や手数料モデルを銘柄別に扱うための拡張（stocks マスタ）
- テストカバレッジ拡充（ユニット / 統合テスト）
- スケジューラ（cron / Airflow）連携で AI スコアリングやレジーム判定を定期実行
- DuckDB を利用した研究パイプラインの最適化（インデックス・CTE 改善）

---

もし README に追加したい具体的な使用例（環境ファイルの雛形、requirements.txt の正確な内容、CI 設定、Dockerfile など）があればお知らせください。必要に応じて追記・整形します。