# KabuSys

日本株向けの自動売買・研究用ライブラリ兼プロトタイプ。  
トレード実行（ExecutionEngine）・監視（MonitoringEngine）・ポートフォリオ構築・ファクター研究・AIニュース分析などの機能を備えています。

以下はコードベース（src/kabusys）に基づく README です。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群です。

- マーケットデータ（DuckDB）を用いたファクター計算・研究機能
- 注文管理・ブローカー抽象化を通した発注エンジン（ExecutionEngine, OrderManager, Reconciler 等）
- 実行系の安全性を保つ監視システム（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager）
- Paper Trading サポート（本番 DB と完全分離）
- ニュースの LLM（OpenAI）によるセンチメント解析 / レジーム判定
- Streamlit ダッシュボードや検証レポート生成ツール

設計方針として、ルックアヘッドバイアス回避、冪等性、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- 実行・復旧
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - 起動時のリコンシリエーション（Reconciler）
  - Order 管理（OrderManager / OrderRepository）

- 監視
  - SystemMonitor: CPU/メモリ/Disk、プロセス（PID）存在確認、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: リスクトリガーで停止フラグを書き込み ExecutionEngine を停止
  - AlertManager: LINE へのプッシュ通知（任意設定）
  - MonitoringEngine / run_monitoring.py：ポーリングループによる定期監視
  - Streamlit ダッシュボード（監視データ表示）

- 研究・ポートフォリオ
  - ファクター計算（momentum / value / volatility）
  - 将来リターン・IC計算・統計サマリ
  - 候補選定・重み算出・単元丸め・リスク調整（sector cap, regime multiplier）

- AI（OpenAI）
  - ニュース集合の銘柄別センチメントスコア化（src/kabusys/ai/news_nlp.py）
  - マクロニュース + ETF MA200 で日次レジーム判定（src/kabusys/ai/regime_detector.py）

- ツール
  - Paper Trading 検証レポート生成（src/kabusys/tools/paper_verification_report.py）

---

## セットアップ手順（開発環境向け）

前提
- Python 3.10+（typing の union 演算子 `|` を使用）
- Git によるプロジェクトルート検出（自動 .env ロードに利用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（requirements.txt がある場合はそちらを利用）
   主要依存例:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit
   - python-dateutil / その他標準ライブラリのみで実装している箇所も多いです

   例:
   ```
   pip install duckdb psutil openai requests streamlit
   ```

4. データディレクトリの作成
   ```
   mkdir -p data
   ```

5. 環境変数の設定
   プロジェクトルートに `.env` / `.env.local` を作成すると自動で読み込まれます（OS環境変数が優先）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合必須)
   - KABUSYS_ENV (default: development) — 有効値: development, paper_trading, live
   - PAPER_FILL_MODE (paper_trading 時のモックの約定挙動: instant|partial|never|reject)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
   - SQLITE_PATH (監視 DB, default: data/monitoring.db)
   - DUCKDB_PATH (DuckDB path, default: data/kabusys.duckdb)
   - PID_FILE_PATH (default: data/execution.pid)
   - KILL_FLAG_PATH (default: data/kill.flag)
   - MONITOR_POLL_INTERVAL (監視ポーリング秒, default: 60)
   - LOG_LEVEL (default: INFO)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）

   例 .env（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=your_token
   KABU_API_PASSWORD=your_password
   OPENAI_API_KEY=sk-xxxx
   KABUSYS_ENV=development
   ```

6. DB 初期化
   - 監視用 SQLite（monitoring.db）は run_monitoring または run_execution 実行時に自動でテーブル作成（init_monitoring_db）が行われます。
   - DuckDB（prices_daily や raw_financials 等のテーブル）は外部データ取り込み手順に従って準備してください（本 README ではデータ取り込み手順は省略）。

---

## 使い方（起動例）

基本的にパッケージとして実行できます。プロジェクトルートで以下のコマンドを実行してください。

1. 監視ループを起動（Monitoring）
   - 監視ループは常時ポーリングして monitoring.db にログを書きます。
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）。
   ```
   python -m kabusys.run_monitoring
   ```
   ポーリングはデフォルト 60 秒。停止は Ctrl+C、またはプロジェクトルートの data/stop_requested.flag を作成するとループ内で検知して終了します。

2. 実行エンジンを起動（Execution）
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と分離されます。
   ```
   python -m kabusys.run_execution
   ```
   - 実行プロセスは data/execution.pid を作成します。停止は data/stop_requested.flag を作成するか、kill.flag による停止（KillSwitch）で制御します。

3. Streamlit ダッシュボード（監視可視化）
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

4. Paper Trading 検証レポート生成
   - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   あるいは DB を指定:
   ```
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```

5. AI 機能（ニューススコア算出 / レジーム判定）
   - OpenAI API キーが必要です（OPENAI_API_KEY）。DuckDB コネクションをアプリ側で用意して `score_news` / `score_regime` を呼び出します。
   - 関数:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止・強制停止（フラグファイル）

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py のループ内で定期的に存在をチェックし、存在すれば安全に終了します（外部から停止指示を出す場合に利用）。
- data/kill.flag
  - KillSwitch が write すると作成され、ExecutionEngine 側で検知して安全に停止するトリガーとなります。
- PID ファイル
  - Execution は `data/execution.pid`（デフォルト）を作成。SystemMonitor は PID を確認し、存在してもプロセスが生きていない (stale) 場合に削除してアラートを出します。

---

## 設定 / 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（default: development）
  - paper_trading のときは paper DB を使用（Settings.is_paper で判定）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 認証（必須）
- OPENAI_API_KEY: LLM を使用する機能に必要
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH, SQLITE_PATH, DUCKDB_PATH: データベースファイルパス
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 監視関連
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）

（詳細は src/kabusys/config.py を参照）

---

## 開発・デバッグのヒント

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml のある場所）を基準に `.env` / `.env.local` を読み込みます。
  - テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
  - .env のパースはシェル形式の一部をサポート（export 句、クォート、インラインコメント等）。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等で起動時に呼ばれます。既存 DB にスキーマ変更が必要な場合は自動で簡易マイグレーション（列追加）を試みます。

- Unit テスト
  - 外部 API 呼び出し（OpenAI など）は _call_openai_api 関数を patch して差し替え可能に設計されています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py — 環境変数 / 設定管理
- run_monitoring.py — 監視ポーリングループ起動
- run_execution.py — ExecutionEngine 起動

- monitoring/
  - __init__.py
  - monitoring_db.py — SQLite 永続層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py

- execution/
  - order_manager.py
  - order_repository.py (存在するがここでは一部のみ抜粋)
  - reconciler.py
  - broker_factory.py (ブローカークライアント生成)
  - execution_engine.py (エンジン本体 — 起動/停止/セッション管理)

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
  - paper_verification_report.py
  - __init__.py

- utils/
  - process_priority.py
  - __init__.py

- data/ （ランタイムで使用）
  - monitoring.db（default SQLITE_PATH）
  - paper_trading.db（paper trading 用）
  - kabusys.duckdb（default DUCKDB_PATH）
  - execution.pid, stop_requested.flag, kill.flag など

---

## 参考・補足

- Paper Trading 環境は本番データと完全に分離されるよう設計されています（別 SQLite ファイル、MockBroker）。
- モジュールは「DB 参照なし」の純粋関数（portfolio, position sizing 等）と、DB を必要とするコンポーネント（monitoring_db, monitors, execution）に分かれています。ユニットテストはこの分離を活かして行いやすくなっています。
- LLM 呼び出し（OpenAI）はリトライ・バックオフ・レスポンスバリデーションを実装しており、失敗時はフェイルセーフ挙動（スコア 0.0 など）にフォールバックします。

---

必要に応じて README に追記します。具体的に載せたい「起動スクリプトの引数詳細」「ブローカー接続設定」「DB 初期データの入れ方」などがあれば教えてください。