# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」の内部モジュール群を含みます。ここではプロジェクトの概要、主要機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめます。

注意: この README はソースコード（src/kabusys 以下）を参照して作成しています。実行前に必ず環境変数・依存ライブラリを確認してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な目的は以下です。

- 戦略に基づく銘柄選定・配分・株数計算（Portfolio construction）
- 発注管理・ブローカーとのインタフェース（ExecutionEngine、OrderManager 等）
- 監視（プロセス・データ鮮度・注文状況・リスク）とアラート送信（LINE）
- Paper Trading 用の分離された記録・検証ツール
- 研究用モジュール（ファクター計算、特徴量探索）
- ニュースに対する LLM ベースのセンチメント計算・市場レジーム判定（OpenAI 利用）
- DuckDB / SQLite を用いたデータ処理とログ永続化
- Streamlit ベースの監視ダッシュボード

設計上のポイント:
- 多くのコンポーネントは副作用を持たない「純粋関数」または明確な永続化層（MonitoringDB）になっています。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離される設計です。
- ルックアヘッドバイアスを避けるため、日付参照は関数引数で与えることを想定しています。

---

## 機能一覧

主要な機能／モジュール：
- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / Reconciler / RiskManager / OrderRepository など
  - Broker クライアントの抽象化（本番・モック対応）
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス・データ鮮度監視
  - TradeMonitor: 注文滞留・異常約定価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: フラグファイル (data/kill.flag) による Execution 停止シグナル
  - AlertManager: LINE による通知（クールダウン管理）
  - MonitoringEngine: 上記を束ねたポーリングループ
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
  - monitoring_db: SQLite スキーマ定義・永続化 API
- portfolio
  - 銘柄選定（select_candidates）、重み計算（等重・スコア重み）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、リスクベース/等分配等）
- research
  - factor_research: Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC、統計サマリ等
- ai
  - news_nlp: raw_news を LLM（OpenAI）でスコアリングして ai_scores に保存
  - regime_detector: ma200 乖離 + マクロニュースセンチメントで market_regime を判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（期間指定可）

---

## セットアップ手順

以下は一般的なローカル開発 / 試験環境向けの手順です。

1. Python 環境
   - Python 3.10+ を推奨（コードは型注釈に | を使用）
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（代表例）
   - pip install duckdb psutil requests openai streamlit
   - ※実プロジェクトでは requirements.txt を用意していることを想定してください。

3. ディレクトリと DB ファイル
   - data ディレクトリを作成:
     - mkdir -p data
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

4. 環境変数 (.env)
   - 本プロジェクトは .env/.env.local を自動で読み込みます（プロジェクトルートが .git または pyproject.toml により検出される場合）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 重要な環境変数（例）:
     - 必須（実運用で必要）:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - OpenAI:
       - OPENAI_API_KEY（ai/news_nlp と ai/regime_detector で使用）
     - 起動環境:
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DB / 動作設定:
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
       - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定挙動
       - PID_FILE_PATH, KILL_FLAG_PATH
       - LOG_LEVEL（DEBUG|INFO|...）
       - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知）
     - 監視ループ間隔:
       - MONITOR_POLL_INTERVAL（秒、デフォルト 60）

5. 注意事項
   - Process priority / CPU affinity の設定には psutil が必要で、権限により設定に失敗する場合があります（ログに警告が出ます）。
   - OpenAI API を利用する機能は API キーが必須です。API コールは課金対象となるため注意してください。
   - Paper Trading を使う場合は KABUSYS_ENV=paper_trading を設定してください（本番 DB とは分離されます）。

---

## 使い方

以下は主な起動方法・ツールの使い方サンプルです。

1. ExecutionEngine を起動（本番または paper_trading）
   - 環境例（Paper Trading）:
     - export KABUSYS_ENV=paper_trading
     - export OPENAI_API_KEY=sk-...
   - 起動:
     - python -m kabusys.run_execution
   - 動作:
     - 起動時に process priority を "high" に変更し、SQLite / DuckDB に接続します。
     - paper_trading のときは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。

2. Monitoring を起動
   - 環境変数でポーリング間隔を上書き可:
     - export MONITOR_POLL_INTERVAL=30
   - 起動:
     - python -m kabusys.run_monitoring
   - 動作:
     - SystemMonitor、TradeMonitor、RiskMonitor などの監視ロジックをポーリング実行して monitoring DB（data/monitoring.db）へ書き込みます。
     - MONITOR_POLL_INTERVAL が不正値（0 や負数）の場合はデフォルト 60 秒にフォールバックします。

3. Streamlit ダッシュボード（監視 UI）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

4. Paper Trading 検証レポート生成
   - Usage:
     - python -m kabusys.tools.paper_verification_report
     - オプション:
       - --from YYYY-MM-DD
       - --to YYYY-MM-DD
       - --db PATH  (PAPER_TRADING_SQLITE_PATH が指定されていれば省略可)
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

5. AI（ニューススコアリング / レジーム判定）
   - プログラムから呼び出す:
     - from kabusys.ai import score_news
     - score_news(duckdb_conn, target_date, api_key="sk-...")
   - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY でも可）。
   - LLM 呼び出しは retry/バックオフやレスポンス検証を実装していますが、API のエラーや制限に注意してください。

6. 設定の読み込み
   - Settings クラス: kabusys.config.Settings で環境変数をラップして提供します。
   - KABUSYS_ENV は {development, paper_trading, live} のいずれかであり、不正値は ValueError で弾かれます。

---

## 主要ファイル・ディレクトリ構成

src/kabusys の主要ファイルと簡単な説明:

- src/kabusys/
  - __init__.py — パッケージ情報
  - config.py — 環境変数 / .env 読み込みロジック、Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 単体起動スクリプト（監視用ポーリングループ）
- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...（発注・再同期・リスク管理ロジック）
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマと永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク・プロセス・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン/ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - position_sizing.py — 実際の株数計算（単元丸め・aggregate cap）
- src/kabusys/research/
  - factor_research.py — ファクター計算（DuckDB を使用）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- src/kabusys/ai/
  - news_nlp.py — ニュースの LLM センチメントスコア計算・ai_scores への保存
  - regime_detector.py — マクロセンチメント + ma200 乖離によるレジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 用レポート生成 CLI
- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は抜粋。詳細は各モジュールの docstring を参照してください。）

---

## 追加の実装上の注意 / 運用メモ

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等でテーブルを作成し、既存 DB に対する簡単なマイグレーション（カラム追加）も行います。
- 再起動時のリコンシリエーション:
  - Reconciler は起動時に OrderSent 状態の照合とポジション差分検出を行い、クラッシュ後の整合性を保ちます。
- KillSwitch:
  - RiskMonitor などが閾値を越えると data/kill.flag を書き込み、ExecutionEngine 側でこれを検知して安全停止する設計です。
- ロギング:
  - run_* スクリプトは logging.basicConfig(level=logging.INFO) を使用しています。LOG_LEVEL 環境変数で上書き可能です（Settings.log_level）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録されます。本番の orders DB と完全分離されます。
- OpenAI 使用:
  - news_nlp と regime_detector は OpenAI を呼び出します。API キーの管理・コスト・利用上の制約に注意してください。
  - レスポンスのバリデーション・クリップ等を実装して安全側にフォールバックする仕組みがありますが、API 失敗時は該当処理をスキップして継続する設計です。

---

## よく使うコマンド集

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール（例）
  - pip install duckdb psutil requests openai streamlit

- Execution 起動
  - python -m kabusys.run_execution

- Monitoring 起動
  - export MONITOR_POLL_INTERVAL=60
  - python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - もしくは
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

この README は開発者向けの概要をまとめたものです。各モジュールの詳細な設計やパラメータはソースコード内の docstring（注釈）を参照してください。必要であれば各モジュール別の詳細ドキュメント（API 仕様・設計ノート）も作成できます。