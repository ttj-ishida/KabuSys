# KabuSys

KabuSys は日本株向けの自動売買／研究／監視を行う小規模なシステムです。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視コンポーネント、ポートフォリオ構築ロジック、リサーチユーティリティ、AI を使ったニューススコアリングなどが含まれます。

主な特徴、セットアップ手順、使い方、ディレクトリ構成を以下にまとめます。

---

## プロジェクト概要

- 日本株自動売買のためのコンポーネント群を提供します。
  - 注文作成・管理（ExecutionEngine / OrderManager / OrderRepository）
  - 起動時リコンシリエーション（Reconciler）
  - 監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
  - ポートフォリオ構築（候補選定・重み・ポジションサイズ計算・セクター制限）
  - リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー 等）
  - AI を用いたニュースのセンチメント評価（OpenAI を利用）
  - Streamlit による監視ダッシュボード
  - Paper Trading 用の分離された DB と検証用レポート生成

- 設定は環境変数／.env ファイルで管理。Settings クラスが各種値を提供します。

---

## 機能一覧（抜粋）

- Execution
  - Broker クライアントの抽象化（本番 / モックの切替をサポート）
  - OrderManager による注文ライフサイクル管理
  - Reconciler による再起動時の自動復旧とポジション照合
  - RiskManager（レート制限・ポジション上限・ドローダウン等の制限）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態、データ鮮度を監視
  - TradeMonitor：滞留注文・約定異常価格を検出
  - RiskMonitor：ドローダウン・ポジション上限を監視、ダッシュボード更新
  - KillSwitch：重大なリスク発生時にフラグファイルを書き込み ExecutionEngine を停止
  - AlertManager：LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）

- Portfolio / Research
  - 候補選定、等重/スコア重み、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数の適用
  - DuckDB を用いたファクター計算（mom, volatility, value）
  - 将来リターン・IC・統計サマリなどのリサーチ用ユーティリティ

- AI
  - OpenAI を用いたニュースセンチメント（銘柄別）スコアリング
  - 市場レジーム判定（ETF MA200 とマクロニュースの LLM スコアを合成）

- ツール
  - Paper Trading の検証レポート生成（paper_verification_report）
  - Streamlit による監視ダッシュボード起動スクリプト

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動

   git clone <repo-url>
   cd <repo-root>

2. Python 環境を用意（推奨: venv）

   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows

3. 必要なパッケージをインストール

   pip install pip-tools
   # requirements.txt がない場合は主要依存をインストール
   pip install duckdb psutil requests openai streamlit

   （実際のプロジェクトでは requirements.txt / lock を用意してください。）

4. data ディレクトリを作成

   mkdir -p data

   デフォルトの DB パス:
   - 監視データ（SQLite）: data/monitoring.db
   - DuckDB: data/kabusys.duckdb
   - Paper Trading SQLite: data/paper_trading.db

5. 環境変数を設定（.env をプロジェクトルートに置くことを想定）
   自動で .env / .env.local を読み込みます（OS に定義された環境変数は保護される）。
   自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例、必須項目に注意）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知を使う場合)
   - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
   - PAPER_FILL_MODE: instant | partial | never | reject (paper_trading 時の挙動)
   - SQLITE_PATH（監視 DB のパス）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
   - DUCKDB_PATH（DuckDB のパス）
   - LOG_LEVEL（INFO 等）
   - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔 秒、デフォルト 60）

   例 (.env):
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-xxxx
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 使い方（代表的なコマンド）

- 監視ループを起動（production 想定の sqlite パスを使います）

  python -m kabusys.run_monitoring

  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で変更できます（デフォルト 60）。  
    例: export MONITOR_POLL_INTERVAL=30

  - 停止方法: プロジェクトルートの data/stop_requested.flag を作成すると監視ループは次回ポーリング時に終了します。

- ExecutionEngine（実行エンジン）を起動

  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（モック）を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込みます（本番 DB と分離）。
  - 起動時に data/execution.pid が使われ、プロセス優先度を "high" に設定しようとします。
  - 停止方法:
    - data/stop_requested.flag を作成するとエンジンは安全に停止します。
    - KillSwitch（リスク条件を満たした場合）で data/kill.flag が書き込まれ、外部運用側で検知して停止させることができます。

- Streamlit ダッシュボード

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  - 読み取り専用で SQLite を開きます（監視データが存在する必要あり）。

- Paper Trading 検証レポート生成

  python -m kabusys.tools.paper_verification_report
  # 期間指定例
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（ニューススコアリング / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

  これらは Python API として呼び出す設計です（DuckDB 接続を渡します）。OpenAI API キーが必要です。

---

## 停止・シグナル制御

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py はこのファイルの存在を監視し、検出すると安全にシャットダウンします（外部から停止要求を出す用途）。

- KillSwitch / data/kill.flag
  - 監視コンポーネント（RiskMonitor 等）によって重大な条件が検出されたとき、KillSwitch が kill.flag（設定に従う）を書き込みます。ExecutionEngine はこれを検知して停止できます。
  - kill.flag は Settings.kill_flag_path (デフォルト data/kill.flag) で指定できます。
  - Settings.kill_flag_clear_on_start が有効であれば起動時に kill.flag を自動クリアする運用も可能（コードの呼び出し側で利用）。

---

## 設定の読み込みルール（.env）

- 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）で .env を読み込み（既存 OS 環境変数は上書きしない）。
  - .env.local が存在する場合は .env の後に上書き（ただし OS 環境変数は保護）。
  - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- .env のパースはシェル風の export KEY=val やクォートされた値、インラインコメントなどに対応しています。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込み（Settings）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト

  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 execution 関連モジュール: order_repository, engine, broker_factory 等)

  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 / DB 書き込みラッパー
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

  - research/
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py             — OpenAI を使ったニューススコアリング
    - regime_detector.py      — マーケットレジーム判定

  - tools/
    - paper_verification_report.py

  - utils/
    - process_priority.py     — クロスプラットフォームのプロセス優先度 / CPU affinity 設定

- data/
  - monitoring.db (SQLite)   — 監視ログ（デフォルト）
  - paper_trading.db         — Paper Trading 用 DB（分離）
  - kabusys.duckdb           — DuckDB（時系列価格等）
  - stop_requested.flag      — 外部停止要求フラグ
  - kill.flag                — KillSwitch が書き込むフラグ
  - execution.pid            — 実行エンジンの PID ファイル

---

## 運用上の注意・補足

- Paper Trading は本番 DB と完全に分離されます（run_execution は KABUSYS_ENV によって paper DB を選択）。
- OpenAI / LINE 通知を使う場合はそれぞれの API キー・トークンを適切に設定してください。失敗時はロギングでフォールバックし、システムは継続する設計になっています（重大な失敗で例外を投げる箇所も一部あります）。
- Process priority / CPU affinity の設定はプラットフォームに依存します。権限不足や未サポート環境では警告ログが出ますが処理は続行します。
- DB スキーマのマイグレーションはいくつか自動で行います（monitoring_db.init_monitoring_db がカラム追加を行う例あり）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境変数の自動ロードを無効化すると安定します。

---

README の内容はコードベース（src/kabusys 以下）の実装に基づいています。  
運用上の詳細なパラメータや実際の broker 実装（kabuAPI 連携など）は各環境に応じて追加・調整してください。必要であればこの README をベースに .env.example や requirements.txt、起動用 systemd ユニット例なども作成します。必要なものがあれば教えてください。