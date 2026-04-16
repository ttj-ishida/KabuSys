# KabuSys

日本株向け自動売買システムのコードベース。ポートフォリオ構築、発注エンジン、監視機能、研究／ファクター計算、AI（ニュース／レジーム判定）などを含むモジュール群で構成されています。

---

## 概要

KabuSys は日本株の自動売買を想定したモジュール化されたシステムです。主なコンポーネントは以下です。

- Execution Engine: ブローカーへの発注・注文状態管理・再同期（リコンシリエーション）
- Monitoring: システム稼働監視、注文監視、リスク監視、Kill Switch（停止フラグ）とアラート（LINE）
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- Research: DuckDB を用いたファクター計算、将来リターン、IC 計算等
- AI: OpenAI を使ったニュースセンチメントと市場レジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit ダッシュボードなど

設計上の注意点：
- 環境変数（.env / .env.local / OS環境変数）から設定を読み込みます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- `KABUSYS_ENV` により動作モードを切替（development / paper_trading / live）。
- Paper Trading モードでは本番 DB を分離し、MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用します。

---

## 機能一覧

- Execution
  - 注文作成 / 送信 / 状態同期（Reconciler） / 重複注文保護
  - RiskManager による注文制御（レート制限、ポジション上限など）
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文検知、約定異常価格検知
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード集計更新
  - KillSwitch: 必要に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: LINE によるアラート送信（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）
- Research / Portfolio
  - モメンタム、ボラティリティ、バリューなどのファクター計算（DuckDB）
  - 将来リターン、IC（Spearman）計算、ファクター統計
  - 候補選定、重み計算、ポジションサイズ計算（単元株丸め・制約考慮）
- AI
  - ニュースを LLM（gpt-4o-mini）でセンチメントスコア化し ai_scores テーブルへ保存
  - ETF とマクロニュースを組合せて市場レジーム（bull/neutral/bear）を判定し保存
- Tools
  - Paper Trading 検証レポート生成（期間フィルタ可能）
  - Streamlit ダッシュボード起動スクリプト

---

## セットアップ手順（開発環境向け）

前提：
- Python 3.10+ を推奨（ソースの型ヒントに | が使われています）
- システムにより追加の OS 権限（psutil のプロセス優先度設定等）が必要な場合があります

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を作成するか、OS 環境変数を設定します。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development  # or paper_trading / live
     - PAPER_FILL_MODE=instant  # paper_trading 用（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO
     - MONITOR_POLL_INTERVAL=60  # run_monitoring 用（秒）
   - 自動 .env 読み込みはデフォルトで有効。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 初期 DB（必要に応じて）
   - monitoring 用 SQLite（data/monitoring.db）は Monitoring モジュール起動時にテーブルが作成されます（init_monitoring_db）。
   - DuckDB（data/kabusys.duckdb）は研究用データをロードする必要がある場合があります。

---

## 使い方

主要な起動スクリプトとツールの使い方を示します。

1. 監視ループ開始（Monitoring）
   - python -m kabusys.run_monitoring
   - 概要:
     - プロセス優先度を high に設定（set_process_priority）
     - monitoring 用 SQLite (settings.sqlite_path) に接続してテーブルを初期化
     - SystemMonitor をポーリングして system_status 等を記録
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で上書き可能
     - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループ終了

2. 実行エンジン起動（Execution Engine）
   - python -m kabusys.run_execution
   - 概要:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading_db に記録（本番 DB と分離）
     - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動
     - 起動時に data/stop_requested.flag が存在する場合は起動を中止
     - 実行中に data/stop_requested.flag が作成されると安全に停止を試みる
     - 実行 PID は data/execution.pid に書き込まれる

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - PAPER_TRADING_SQLITE_PATH 環境変数で DB パスを指定可能。デフォルトは data/paper_trading.db。
   - レポートは稼働率、注文成功率、送信率、レイテンシ（P95）等を表示し PASS/FAIL を判定します。

4. Streamlit ダッシュボード（監視表示）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードでポートフォリオ値、オープンポジション、注文ログ、最新のシステムステータスやリスクログを確認できます。

5. AI モジュール（ニューススコアリング / レジーム判定）
   - kabusys.ai.score_news（プログラムから呼び出し）:
     - 引数に DuckDB 接続と target_date、OPENAI_API_KEY を渡し、ai_scores テーブルを更新
   - kabusys.ai.regime_detector.score_regime（同様に呼び出し）
   - 注意: OpenAI API 呼び出しを行うため OPENAI_API_KEY が必要。API 呼び出しはリトライ・フォールバックロジックを備えています。

6. 設定と環境の読み込み
   - 設定管理は kabusys.config.Settings によって行われます。
   - 自動でプロジェクトルートを検出して .env / .env.local を読み込みます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 主要な設定例は上記「セットアップ手順」を参照してください。

---

## 主要ファイル・スクリプト一覧

- 実行/運用
  - src/kabusys/run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - src/kabusys/run_execution.py — ExecutionEngine 起動スクリプト

- 設定
  - src/kabusys/config.py — 環境変数・設定管理

- 監視
  - src/kabusys/monitoring/monitoring_db.py — monitoring SQLite 層
  - src/kabusys/monitoring/system_monitor.py
  - src/kabusys/monitoring/trade_monitor.py
  - src/kabusys/monitoring/risk_monitor.py
  - src/kabusys/monitoring/kill_switch.py
  - src/kabusys/monitoring/alert_manager.py
  - src/kabusys/monitoring/monitoring_engine.py
  - src/kabusys/monitoring/streamlit_dashboard.py

- 実行ロジック（execution）
  - src/kabusys/execution/*.py （OrderManager, Reconciler, ExecutionEngine 等 ※一部省略）

- ポートフォリオ構築
  - src/kabusys/portfolio/portfolio_builder.py
  - src/kabusys/portfolio/position_sizing.py
  - src/kabusys/portfolio/risk_adjustment.py

- 研究 / ファクター
  - src/kabusys/research/factor_research.py
  - src/kabusys/research/feature_exploration.py

- AI
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/ai/regime_detector.py

- ユーティリティ
  - src/kabusys/utils/process_priority.py

- ツール
  - src/kabusys/tools/paper_verification_report.py

---

## ディレクトリ構成（抜粋）

src/
- kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py
  - utils/
    - __init__.py
    - process_priority.py
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
    - (order_manager.py, reconciler.py, execution_engine.py, broker_factory.py, ...)
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

プロジェクトルート:
- data/                  # 実行時に生成する DB やフラグファイル（monitoring.db, kabusys.duckdb, execution.pid, kill.flag 等）
- pyproject.toml / .git  # プロジェクトルート特定に使用

---

## 運用上の注意（重要）

- Paper Trading と本番（live）は DB を明確に分離してください（Settings は paper_trading モードで paper_sqlite_path を使用します）。
- OpenAI やブローカー API のキーは安全に管理し、公開リポジトリに含めないでください。
- psutil を用いたプロセス優先度設定は一部 OS / 権限で失敗する可能性があり、その場合はログに警告が出ます（処理は継続します）。
- 停止フラグ（data/stop_requested.flag）や kill.flag の扱いに注意してください。これらは手動で作成・削除することでプロセス制御ができます。
- Monitoring / Execution の長時間運用時はログローテーション、監視、バックアップを検討してください。

---

## 開発・テストヒント

- 設定の自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからテスト用の環境変数をプログラム側で注入できます。
- AI API 呼び出し部分は内部で抽象化されているため、ユニットテスト時は該当関数（例: _call_openai_api, score_news 内の呼び出し）をモックすることでネットワーク依存を切り離せます。
- MonitoringDB の init_monitoring_db() は冪等でありマイグレーション処理（カラム追加）も行います。既存 DB のスキーマ差分を吸収する作りになっています。

---

必要であれば、README に追記する以下の情報も作成できます：
- 推奨の requirements.txt / pip install 一括コマンド
- サンプル .env.example（最小限の必須変数）
- systemd / supervisor 用のサービスユニット例（実運用向け）
- ログ出力・ローテーション方針のサンプル

ご希望があれば追加で作成します。