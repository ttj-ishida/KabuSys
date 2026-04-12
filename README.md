# KabuSys

日本株自動売買システムのライブラリ / ツール群（部分実装）。  
この README はリポジトリ内の主要スクリプト・モジュールを参照して作成しています。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコンポーネント群です。  
主な役割：

- 注文発行・状態管理（ExecutionEngine / OrderManager / Reconciler）
- 監視（MonitoringEngine／System/Trade/Risk モニタ）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- 研究用ファクター計算（momentum / volatility / value 等）
- AI を使ったニュース NLP（OpenAI 経由のセンチメント）と市場レジーム判定
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）

設計方針の例：
- DuckDB / SQLite をデータストアに使用（DuckDB は時系列計算用）
- 環境変数 / .env で設定を管理（自動読み込み機能あり）
- Paper Trading 環境は本番 DB と完全分離
- LLM 呼び出しはリトライやバリデーションを含めてフェイルセーフ化

---

## 主な機能一覧

- Execution
  - 注文生成 / 送信 / 同期（OrderManager, ExecutionEngine, Reconciler）
  - Paper Trading モード（MockBrokerClient を使い別 DB に記録）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/実プロセス生存確認
  - TradeMonitor：滞留注文検出、約定価格異常検出
  - RiskMonitor：ドローダウン、ポジション上限監視
  - KillSwitch：一定条件で ExecutionEngine 停止フラグを生成
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定、等金額／スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（lot 単位丸め、資金配分のスケールダウン）
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算、統計サマリー
- AI
  - news_nlp: raw_news → OpenAI（gpt-4o-mini）でセンチメントを算出、ai_scores に保存
  - regime_detector: ETF MA200 とマクロニュースを合成して市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）

---

## セットアップ手順

前提
- Python 3.9+（型ヒントからの想定）
- OS により psutil の一部機能に権限が必要な場合あり

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt がある場合はそれを使ってください（本リポジトリに含まれている想定の主要依存は上記）。

3. 環境変数 / .env を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須例：
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
   - OpenAI を使う機能を使う場合：
     - OPENAI_API_KEY=...
   - 例（.env）:
     ```
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PAPER_FILL_MODE=instant
     OPENAI_API_KEY=sk-...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     ```
   - 自動ロードの挙動：
     - OS 環境変数 > .env.local > .env の優先順位で読み込まれます。
     - OS 環境変数の既存キーは .env で上書きされません（.env.local は override）。

4. データディレクトリの作成
   - data/ 以下（SQLite・DuckDB 等のデフォルトパス）を作成して権限を与えてください。

---

## 使い方

ここでは主要なエントリポイントと使い方を示します。パッケージをインストールしていない場合はソースツリー直下から python -m で起動できます。

1. 監視ループ（Monitoring）
   - スクリプト: src/kabusys/run_monitoring.py
   - 実行方法:
     - python -m kabusys.run_monitoring
     - または python src/kabusys/run_monitoring.py
   - 説明:
     - 起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。
     - 監視データは Settings.sqlite_path （デフォルト: data/monitoring.db）へ保存されます（監視は本番 sqlite_path を環境にかかわらず使用します）。
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
       - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

2. 実行エンジン（Execution）
   - スクリプト: src/kabusys/run_execution.py
   - 実行方法:
     - python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
     - 起動時にプロセス優先度 "high" を試みます。
     - duckdb は Settings.duckdb_path（デフォルト data/kabusys.duckdb）を使用します。

3. Paper Trading 検証レポート
   - スクリプト: kabusys.tools.paper_verification_report
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプションで --db PATH に DB ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

4. Streamlit ダッシュボード（監視）
   - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
   - 実行例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - read-only モードで SQLite DB を開きます。MonitoringEngine が稼働していないと DB が存在しないため起動エラーになります。

5. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）を設定しておく必要があります。
   - プログラム API:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意:
     - OpenAI 呼び出しはコストが発生します。API 呼び出しに失敗してもフェイルセーフ（スコア0や部分スキップ）で継続する設計です。

6. 設定（Settings クラス）
   - 環境変数は kabusys.config.Settings でラップされています。
   - 主要な環境変数（デフォルトがあるものと必須のもの）:
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 任意・デフォルトあり:
       - KABUSYS_ENV (development | paper_trading | live) — default: development
       - LOG_LEVEL (INFO)
       - SQLITE_PATH (data/monitoring.db)
       - DUCKDB_PATH (data/kabusys.duckdb)
       - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
       - PAPER_FILL_MODE (instant | partial | never | reject)
       - PID_FILE_PATH (data/execution.pid)
       - KILL_FLAG_PATH (data/kill.flag)
       - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

---

## 実運用上の注意事項

- Process priority / CPU affinity は psutil を介して設定します。権限不足や未サポート OS の場合は警告が出てスキップされます。
- Monitoring は常に（環境にかかわらず）Settings.sqlite_path を使用して監視ログを書きます。Paper Trading の注文ログは paper_sqlite_path に分離されます。
- OpenAI を使う機能は API レスポンスのバリデーションやリトライを行いますが、API キーの管理や費用には注意してください。
- init_monitoring_db() は DB スキーマを冪等に作成・マイグレーションするので、初回起動時に監視 DB が自動でセットアップされます。
- .env の自動ロードはプロジェクトルート (.git または pyproject.toml を起点) を検出して実行されます。テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールのツリー（src/kabusys 以下）。実際のリポジトリにはさらにファイルが存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py (参照されているがここに含まれる想定)
    - reconciler.py
    - execution_engine.py (参照されている想定)
    - broker_factory.py (参照されている想定)
    - broker_api.py (参照されている想定)
    - order_record.py (参照されている想定)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - utils/
    - __init__.py
    - process_priority.py
  - data/ (想定：DuckDB / CSV / データパイプライン関連モジュールがここに関連)

---

## よく使うコマンド一覧

- 監視ループ開始（デフォルト 60s ポーリング）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Execution 起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 付記・開発者向けメモ

- Settings モジュールは .env のパースを独自実装しており、export プレフィックスやクォート・コメント処理をサポートしています。
- 多くのモジュールは DB 接続（sqlite3 / duckdb）を引数で受け取る設計のため、ユニットテストでモック接続を差し替えやすくなっています。
- AI 関連関数はテスト用に API 呼び出し箇所（_call_openai_api 等）を patch できるように設計されています。
- 監視用 DB スキーマ変更（カラム追加等）は init_monitoring_db() 内で簡易マイグレーションを行っています。

---

問題点の報告やドキュメント改善の要望があれば教えてください。README の追記やコマンド例の追加など対応します。