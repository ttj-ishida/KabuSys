# KabuSys

日本株向けの自動売買システム（ライブラリ／運用ツール群）のミニマル実装。  
このリポジトリは、売買実行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築ロジック、リサーチ/ファクター計算、AI を使ったニュース評価などを含みます。

以下はこのコードベースの概要・セットアップ・使い方・ディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的: 日本株の自動売買を行うための実行エンジン（ExecutionEngine）と運用監視（Monitoring）ツール群、研究用モジュールを提供する。
- 主な機能: 注文管理・リコンシリエーション、リスク管理、監視ログ永続化（SQLite）、データ分析（DuckDB）、ニュースのLLMによるセンチメント評価、監視ダッシュボード（Streamlit）など。
- 設計方針:
  - DB（SQLite / DuckDB）を用いた永続化と分析
  - Paper Trading（検証）と Live（本番）を環境で切替
  - LLM 呼び出しはフェイルセーフ（失敗時にスキップやフォールバック）
  - 自動的に .env / .env.local を読み込み（無効化可能）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカー抽象化（実ブローカー／MockBroker の切替）
  - OrderManager：注文作成・状態管理
  - Reconciler：再起動時の注文／ポジション突合
  - RiskManager：発注前のリスク制御設定（パラメータ化）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス稼働検証
  - TradeMonitor：滞留注文／約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：リスク閾値超過時に停止フラグを書き込み（Execution を安全停止）
  - AlertManager：LINE プッシュ通知の簡易実装
  - MonitoringEngine：各モニターの統合ポーリング
  - Monitoring DB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard の管理

- Research / Data
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索・IC 計算（rank / factor_summary）
  - DuckDB を用いた高速集計

- AI
  - news_nlp: raw_news を LLM（OpenAI）でセンチメント評価し ai_scores に書込
  - regime_detector: ETF の MA200 とマクロニュースを LLM で評価して市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
  - Streamlit ダッシュボード（監視情報可視化）

---

## セットアップ手順

前提:
- Python 3.9+（実際の互換性はコードに合わせてください）
- OS: Linux / macOS / Windows（プロセス優先度関連はプラットフォーム依存）

推奨手順（例）:

1. リポジトリをクローンし、仮想環境を作る
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数 / .env
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます（既定で OS 環境変数を上書きしない挙動）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（主要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用
- OPENAI_API_KEY — OpenAI API を利用する機能（news_nlp / regime_detector）を有効にする場合
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）

重要な環境変数（デフォルト値）:
- SQLITE_PATH: data/monitoring.db
- DUCKDB_PATH: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring から参照。デフォルト 60）

---

## 使い方（主要コマンド）

1. ExecutionEngine を起動する（本番 / Paper 切替）
   - 本番想定:
     - export KABUSYS_ENV=live
   - Paper Trading:
     - export KABUSYS_ENV=paper_trading
     - Paper 環境時は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます（本番 DB と分離）。
   - 起動:
     - python -m kabusys.run_execution
   - 停止:
     - 実行中に data/stop_requested.flag を作成すると安全に停止します（CLI からファイルを作成してプロセスに停止指示）。

2. Monitoring を起動する
   - 監視ループを開始:
     - python -m kabusys.run_monitoring
   - オプション:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（例: export MONITOR_POLL_INTERVAL=30）
   - 注意:
     - run_monitoring は KABUSYS_ENV に関係なく「本番の sqlite_path」を使って監視テーブルを操作します（監視ログは本番 DB に記録されます）。

3. Streamlit ダッシュボード（監視画面）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ブラウザで可視化（ポートは Streamlit の既定に従う）

4. Paper Trading 検証レポート生成
   - 使い方:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB パスを明示する場合:
       - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI 関連（ニューススコア / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY または関数引数で渡す）。
   - news_nlp.score_news / regime_detector.score_regime を呼び出して DuckDB 上のテーブルを元にスコアリング・書き込みを行います。
   - 失敗時はフェイルセーフでフォールバックする設計です（例: API 失敗 → スコア 0.0 or スキップ）。

6. 停止・Kill フラグ
   - ExecutionEngine を外部から止めるには:
     - data/kill.flag を作成（KillSwitch により評価される）または data/stop_requested.flag を作る（run_execution/run_monitoring が監視）
   - 起動時に KILL_FLAG_CLEAR_ON_START 環境変数が "1" に設定されていれば起動時に kill.flag を自動でクリアします。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys を基点とした主要モジュール）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、Settings クラス（.env 自動ロード機能含む）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading と本番を切替）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・読み書きラッパー（MonitoringDB）
    - system_monitor.py — システム状態 / データ鮮度チェック
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — LINE プッシュ通知ラッパー
    - monitoring_engine.py — 各モニターを束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 注文の作成・キャンセル等の外向き API
    - reconciler.py — 再起動時の注文・ポジション突合処理
    - （その他ブローカー関連, order_repository などが含まれる）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・単元丸め・投下資金制御
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value などのファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC / 統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM で評価し ai_scores に書込
    - regime_detector.py — 市場レジーム判定（MA200 + LLM マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力

- data/
  - デフォルトの SQLite / DuckDB ファイルやフラグファイルを置くディレクトリ（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）

---

## 注意点 / 運用メモ

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml が存在する階層）にある .env / .env.local を自動で読み込みます。ただし OS 環境変数は保護され、.env は既に設定済みの変数を上書きしません。.env.local は override=True でロードします。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 監視 DB の初期化
  - init_monitoring_db() は冪等にテーブルを作成します。run_monitoring / run_execution 起動時に自動で呼ばれます。

- Paper Trading
  - KABUSYS_ENV=paper_trading のとき、Execution は MockBrokerClient を使用し、paper_sqlite_path に書き込みます。本番 DB と分離されています。

- OpenAI / LLM
  - news_nlp と regime_detector は OpenAI を利用します（OPENAI_API_KEY が必要）。
  - API エラー時はリトライ・バックオフやフォールバック値が組み込まれていますが、キーがない場合は呼び出し側で例外になるので注意してください。

- プロセス優先度 / CPU affinity
  - utils.process_priority.set_process_priority, set_cpu_affinity を用いてプロセス優先度やアフィニティを設定します。権限不足で失敗した場合はログ警告のみで継続します。

---

この README はコードの主要用途と運用のポイントをまとめたものです。さらに詳しい内部動作（関数 API や構成パラメータ）は各モジュールの docstring / ソースコメントを参照してください。必要であればインストール手順や運用手順（systemd / supervisor 用 unit ファイルや Docker 化手順）も追記できます。どの情報を優先して追加しますか？