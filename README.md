# KabuSys

KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模なコードベースです。本リポジトリはポートフォリオ構築、ポジションサイズ計算、発注管理、監視、Paper Trading 検証、ニュースの AI スコアリング、レジーム判定などのコンポーネントを含みます。

この README はプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

重要: ここに記載するコマンドはプロジェクトルート（`pyproject.toml` / `.git` のあるディレクトリ）で実行してください。

---

## プロジェクト概要

- 目的: 日本株自動売買システム（発注エンジン + 監視 + 研究ツール群）
- 言語: Python
- 永続化:
  - 軽量な監視ログと発注履歴: SQLite（`data/monitoring.db`, `data/paper_trading.db`）
  - 分析用集計: DuckDB（`data/kabusys.duckdb`）
- 設計方針:
  - 可能な限り副作用を抑えた純粋関数群（ポートフォリオ/リスク計算）
  - 環境変数 / `.env` による設定管理（`kabusys.config.Settings`）
  - Paper Trading と Live を分離（DB / ブローカークライアント等）

---

## 機能一覧（抜粋）

- Execution（発注）:
  - 発注状態管理（OrderManager）
  - リコンシリエーション（再起動後の同期）
  - リスク管理（RiskManager, Reconciler）
  - Broker クライアントの抽象化（mock を含む）
- Monitoring（監視）:
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 滞留注文 / 約定価格の異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視 + ダッシュボード更新
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込みと LINE 通知
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio（銘柄選定・配分）:
  - 候補選定、等金額・スコア加重配分、リスク調整、ポジションサイズ計算
- Research（研究）:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（ニュース NLP / レジーム判定）:
  - OpenAI API を用いたニュースのセンチメントスコアリング（ai_scores への書き込み）
  - マクロニュース + ETF MA による市場レジーム（bull/neutral/bear）判定
- ツール:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. Python 環境準備（例: pyenv + venv）
   - 推奨: Python 3.10+
   - 仮想環境作成例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     ```
2. 依存パッケージをインストール
   - 必要なパッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - インストール例:
     ```bash
     pip install duckdb psutil openai requests streamlit
     ```
   - （実プロジェクトでは requirements.txt / pyproject.toml を参照してください）

3. データディレクトリ作成
   ```bash
   mkdir -p data
   ```
   - SQLite / DuckDB ファイルはデフォルトで `data/` に作成されます。

4. 環境変数の設定
   - 自動ロード: プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development | paper_trading | live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60

   - 例: `.env` の簡易例
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_kabu_pwd
     OPENAI_API_KEY=sk-...
     ```

---

## 使い方

以下は主要な実行方法の例です。パッケージを Python パスに含めている（プロジェクトルートで実行）ことを前提とします。

1. 監視（Monitoring）プロセス起動
   - ポーリングループで SystemMonitor を定期実行し、SQLite にログします。
   - 実行:
     ```bash
     python -m kabusys.run_monitoring
     ```
   - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
   - 停止: プロジェクトルート `data/stop_requested.flag` を作成するとループを終了します（または Ctrl+C）。

2. 実行エンジン（ExecutionEngine）起動
   - 本番 / Paper Trading の挙動を分離します。`KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、`data/paper_trading.db` に記録します。
   - 実行:
     ```bash
     python -m kabusys.run_execution
     ```
   - 実行中の PID はデフォルト `data/execution.pid` に書き込まれます。監視はこの PID を使ってプロセス生存を確認します。
   - 停止: `data/stop_requested.flag` を作成するか、監視側の `KillSwitch`（`data/kill.flag`）で停止をトリガできます。

3. Paper Trading 検証レポート
   - SQLite の Paper Trading DB を読み取り、各種指標（稼働率・注文成功率・レイテンシ等）を標準出力するスクリプト。
   - 実行例:
     ```bash
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     # または DB パス指定
     python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
     ```

4. Streamlit ダッシュボード（監視データ可視化）
   - 実行例:
     ```bash
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     ```
   - 監視 DB が読み取れない場合はエラーが表示されます（MonitoringEngine を先に起動してください）。

5. AI 関連（ニューススコアリング / レジーム判定）
   - OpenAI API キー（`OPENAI_API_KEY`）が必要です。
   - プログラムから呼び出す例（Python REPL / スクリプト内）:
     ```python
     from kabusys.ai.news_nlp import score_news
     import duckdb, datetime
     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, datetime.date(2026, 4, 1), api_key="sk-...")
     ```
   - レジーム判定:
     ```python
     from kabusys.ai.regime_detector import score_regime
     score_regime(conn, datetime.date(2026, 4, 1), api_key="sk-...")
     ```
   - 注意: ネットワークや API エラーはリトライやフォールバックロジックがありますが、API キー未設定時は例外になります。

6. 設定・環境の自動読み込み
   - `kabusys.config` モジュールはプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
   - テストなどで自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 運用上のファイル / フラグ

- data/execution.pid — ExecutionEngine が起動時に書き込む PID ファイル（監視が存在確認に使用）
- data/stop_requested.flag — 管理者が作成すると run_monitoring / run_execution のループが停止する
- data/kill.flag — KillSwitch がリスク条件で作成する停止フラグ（ExecutionEngine に停止を指示）
- data/monitoring.db — 監視ログ（デフォルト）
- data/paper_trading.db — Paper Trading 専用 DB（paper_trading 環境時に使用）
- data/kabusys.duckdb — DuckDB（分析用）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（Settings）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - execution/
    - order_manager.py — 発注ロジック（OrderManager）
    - reconciler.py — 再起動時の同期処理
    - order_repository.py, order_record.py, ... （注文 DB / レコード処理）
    - broker_factory.py, broker_api.py — ブローカー抽象化
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・CRUD ラッパー（MonitoringDB）
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグ発行ロジック
    - alert_manager.py — LINE Push 通知ユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねる実行器
    - streamlit_dashboard.py — streamlit による可視化
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数計算・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースを OpenAI でセンチメントスコアリングして ai_scores に書込
    - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 補足・運用注意点

- Paper Trading と Live は DB とブローカークライアントで明確に分離されています。テスト時に本番 DB を上書きしないよう環境変数を確認してください。
- `Settings` は必須の環境変数が未設定だと例外を投げます（J-Quants や Kabusys API 関連）。
- OpenAI を利用する機能（news_nlp / regime_detector）は API キーが必要です。API コストとレート制限に注意してください。
- 監視は監視 DB（SQLite）へログを書きます。長期間運用する場合は DB のバックアップ / ローテーションを検討してください。
- process priority / cpu affinity の設定は psutil に依存します。権限不足で設定が失敗することがあります（ログに警告が出ます）。

---

必要に応じて README に追記したい項目（例: CI / テスト方法、詳細な設定例、運用手順書など）があれば教えてください。