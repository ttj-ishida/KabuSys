# KabuSys

KabuSys は日本株の自動売買システム（プロトタイプ）です。マーケットデータ解析・ファクター計算・ポートフォリオ構築・発注エンジン・監視・AI を用いたニュース解析などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的:
- DuckDB / SQLite を利用したリサーチ・運用データ基盤
- ファクター計算・特徴量解析（research）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- 発注実行エンジン（ExecutionEngine）とリコンシリエーション
- 監視コンポーネント（System / Trade / Risk モニタ）、ストリームリットダッシュボード
- Paper Trading（本番 DB と分離）と検証レポート生成
- OpenAI を使ったニュースセンチメント（AI モジュール）

設計方針の要点:
- 多くのモジュールは「純粋関数」または DB 抽象層に分離されており単体テストしやすい
- ルックアヘッドバイアス防止（date.today() などを直接参照しない実装方針）
- フェイルセーフ（API 失敗時のフォールバックやログ記録）
- 環境変数 / .env による構成管理（自動ロード機能あり）

---

## 機能一覧

- research
  - calc_momentum, calc_volatility, calc_value（DuckDB を使ったファクター計算）
  - 特徴量探索・IC（Information Coefficient）計算
- portfolio
  - 候補選定（select_candidates）
  - 等金額・スコア加重配分
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイジング（lot 単位の丸め、aggregate cap）
- execution
  - OrderManager / Reconciler（再起動後の自動同期）
  - Broker クライアントファクトリ（paper_trading 時は Mock を使用）
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存チェック、データ鮮度
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン、ポジション数監視
  - KillSwitch: フラグファイルで ExecutionEngine を停止する仕組み
  - AlertManager: LINE へのプッシュ通知（cooldown 管理）
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ
  - Streamlit ベースの監視ダッシュボード
- ai
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント集約・書き込み
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成した日次レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（SQLite を読み取り）

---

## セットアップ手順

以下は一般的なセットアップ例です。プロジェクトに同梱の requirements.txt がある場合はそちらを優先してください。

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば: pip install -r requirements.txt）

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development  # development | paper_trading | live
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO
   - config.Settings は .env/.env.local を .git または pyproject.toml のあるプロジェクトルートから自動読み込みします。

5. データディレクトリの作成
   - mkdir -p data

6. 初期 DB の準備
   - monitoring モジュールは起動時に必要テーブルを作成します（init_monitoring_db）。特別な手順は不要です。

注意:
- Paper Trading は本番 DB と分離しており、KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
- OpenAI を利用する機能を使うには OPENAI_API_KEY が必要です。

---

## 使い方

主要なエントリポイント例。

1. Execution Engine を起動（本番または paper_trading）
   - 本番/開発/ペーパートレードは環境変数 KABUSYS_ENV で切替
   - Paper Trading の場合は MockBrokerClient が使われ、データは paper_sqlite_path（デフォルト data/paper_trading.db）へ書き込まれます

   例:
   - 本番/開発:
     - python -m kabusys.run_execution
   - Paper Trading:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

   実行時にプロセス優先度が "high" に設定され、DB 接続・各コンポーネントが組み立てられてセッションを実行します。

2. Monitoring（監視ループ）を起動
   - デフォルトは 60 秒間隔でポーリング。MONITOR_POLL_INTERVAL 環境変数で秒数を上書きできます（正の整数）。
   - python -m kabusys.run_monitoring
   - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   Monitoring は常に本番用 sqlite_path を使用します（KABUSYS_ENV に依らず）。

3. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - --db で読み取り用 DB パスを指定可能（デフォルト data/monitoring.db）。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を直接指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI 関連
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して、DuckDB 内の raw_news / prices_daily を参照してスコアを作成・書き込みできます。
   - 実行には OPENAI_API_KEY が必要です。API 呼び出しはリトライや失敗フォールバックの実装があります。

6. 環境変数・設定の注記（主なもの）
   - KABUSYS_ENV: development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN: J-Quants API のトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール用）
   - PAPER_FILL_MODE: paper_trading 時の挙動（instant | partial | never | reject）
   - PID_FILE_PATH / KILL_FLAG_PATH: pid ファイル / kill.flag のパス（デフォルト data/execution.pid, data/kill.flag）
   - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

その他の詳細は各モジュールの docstring を参照してください（例: monitoring/*.py, ai/*.py, research/*.py）。

---

## 主要コンポーネントと動作メモ

- process 優先度設定: run_monitoring/run_execution は起動最初に set_process_priority("high") を呼びます（utils/process_priority.py）。
- MonitoringDB（monitoring/monitoring_db.py）はテーブル作成と簡単なマイグレーションを行います（冪等）。
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止指示を与える仕組みです。Execution 側はこのフラグを検出して停止する必要があります（ExecutionEngine 実装に依存）。
- Reconciler は起動時にブローカーと OrderSent 状態の注文を突合して整合を取ります。
- AI モジュールは OpenAI の JSON レスポンスモードを利用し、レスポンスのバリデーション・スコアクリップ・分割バッチ処理・エクスポネンシャルバックオフ等を実装しています。

---

## ディレクトリ構成

（抜粋・主要ファイル）

- src/kabusys/
  - __init__.py                — パッケージ初期化（__version__）
  - config.py                  — 環境変数 / .env の読み込みと Settings
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - risk_adjustment.py       — セクター制限・レジーム乗数
    - position_sizing.py       — 株数計算・スケーリング・丸め
  - research/
    - factor_research.py       — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py   — 将来リターン/IC/summary
  - ai/
    - news_nlp.py              — ニュースセンチメント集約（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロLLM）
  - monitoring/
    - monitoring_db.py         — SQLite テーブル作成 & MonitoringDB クラス
    - system_monitor.py        — システム監視（CPU/メモリ/データ鮮度）
    - trade_monitor.py         — 注文滞留・約定異常チェック
    - risk_monitor.py          — ドローダウン・ポジション数監視
    - kill_switch.py           — kill.flag 管理
    - alert_manager.py         — LINE プッシュ通知
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py         — 発注の高レベル制御（state machine）
    - reconciler.py            — 再起動時のリコンシリエーション
    - (その他 Broker / Repository 等)
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - data/                      — デフォルトの DB 保存先（実行時に使用）
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

---

## 開発・運用時の注意点

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring は常に sqlite_path（デフォルト data/monitoring.db）を使います。Paper Trading は paper_sqlite_path へ分離されます。
- MONITOR_POLL_INTERVAL に不正な値が設定されるとデフォルト（60 秒）にフォールバックされます。
- OpenAI API を利用する機能は API レート制限やネットワーク障害を想定したリトライ処理を有しますが、API キーの管理は慎重に行ってください（漏洩防止）。
- streamlit の起動時に DB を読み込みに行きます。MonitoringEngine が起動しておらず DB ファイルが存在しなければエラー表示されます。

---

README の内容はコードベースの docstring と実装に基づく概要です。各モジュールの詳細な使用方法や内部仕様については該当ファイルの docstring（src/kabusys/*）を参照してください。必要であれば運用手順書や動作図、さらに踏み込んだ API ドキュメントも作成できます。