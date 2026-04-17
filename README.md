# KabuSys

日本株向けの自動売買システム（ライブラリ／実行コンポーネント群）。  
ポートフォリオ構築、ポジションサイズ計算、発注／オーダー管理、監視（モニタリング）、および研究用のファクター計算やAIベースのニュースセンチメント機能を含みます。

---

## 概要

KabuSys は以下の目的で設計されたモジュール群です。

- 戦略に基づく銘柄選定と配分（等配分・スコア加重・リスクベース等）
- 発注フロー（OrderManager / ExecutionEngine）とブローカー抽象化（本番／Paper Trading の分離）
- 起動時の自動リコンシリエーション（Reconciler）による復旧
- 監視（System / Trade / Risk）とアラート（LINE への Push）
- Paper Trading 用の検証レポート生成ツール
- DuckDB を用いた研究向けファクター計算（momentum, volatility, value）
- OpenAI を用いたニュースセンチメント・レジーム判定

設計方針として、ルックアヘッドバイアス防止、フェイルセーフ（API失敗時のフォールバック）、および実運用を意識した冪等性を重視しています。

---

## 主な機能一覧

- portfolio:
  - 銘柄選定（select_candidates）
  - 重み計算（等配分 / スコア加重）
  - ポジションサイズ計算（単元丸め、リスク制約、aggregate cap）
  - セクター集中制限、レジーム乗数適用

- execution:
  - OrderManager（注文作成、重複防止、同期）
  - ExecutionEngine、OrderRepository、Reconciler（起動時の同期・差分検出）
  - Paper Trading モード（本番 DB と完全分離）

- monitoring:
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、プロセス監視）
  - TradeMonitor（滞留注文、約定異常）
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch（条件達成時に data/kill.flag を書き込み ExecutionEngine 停止）
  - AlertManager（LINE Push API による通知）
  - Streamlit ダッシュボード（監視ダッシュボード）

- ai:
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出・ai_scores に書き込み
  - regime_detector: ETF (1321) の MA とマクロニュースの LLM センチメントを合成して市場レジームを判定

- research:
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索：将来リターン計算、IC 計算、統計サマリー

- tools:
  - paper_verification_report: Paper Trading データから稼働率／注文成功率／レイテンシ等の検証レポートを生成

---

## 前提 / 必要環境

- Python 3.10+
- SQLite（Python 標準モジュール sqlite3 を使用）
- 推奨 Python パッケージ（少なくともプロダクションで使う場合）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- OS: Linux / macOS / Windows（ただしプロセス優先度周りはプラットフォーム差分あり）

例（pip）:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. Python 環境の準備（仮想環境推奨）
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   pip install -r requirements.txt
   （requirements.txt が無い場合は上の必要パッケージを個別にインストール）

4. データディレクトリの作成
   mkdir -p data

   デフォルト DB パス:
   - monitoring (SQLite): data/monitoring.db
   - paper trading (SQLite): data/paper_trading.db
   - DuckDB: data/kabusys.duckdb

   起動時に SQLite テーブルは init_monitoring_db() により自動作成されます。

5. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能使用時に必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に書き込む
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB パス上書き）
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（監視用 DB デフォルト data/monitoring.db）
   - MONITOR_POLL_INTERVAL（監視ループの秒数、デフォルト 60）
   - LOG_LEVEL（INFO 等）

   .env のパースは shell 形式に準拠（export キーワード対応、クォート・コメント処理あり）。

---

## 使い方（実行例）

- ExecutionEngine を起動（デフォルト: KABUSYS_ENV 環境に従う）
  python -m kabusys.run_execution

  Paper Trading モードで起動したい場合:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  （Paper Trading は本番 DB と分離して data/paper_trading.db を使用）

- Monitoring を起動（プロセス優先度設定 → ポーリングループ開始）
  python -m kabusys.run_monitoring

  ポーリング間隔を変更する（秒）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  停止は data/stop_requested.flag を作成すると監視ループが終了します（stop フラグファイルの場所は実装上プロジェクト data 以下にあります）。

- Streamlit ダッシュボード（監視 UI）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラムから呼び出す）
  - ニューススコア算出:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  いずれも OPENAI_API_KEY が必要（api_key を引数で与えることも可能）。

---

## 重要な運用注意

- Process priority: 実行スクリプトは起動時に set_process_priority("high") を試みます。権限不足などで失敗しても例外は捕捉され、ログに警告が出ます。
- PID / Stop / Kill フラグ:
  - 実行コンポーネントは data/execution.pid 等の PID ファイルを利用します。
  - 停止フラグ: data/stop_requested.flag（存在検知でループ終了）
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine 停止をトリガーします（RiskMonitor 等が条件）。
- 監視 DB （monitoring.db）は起動時に required テーブルを自動作成・マイグレーションを行います。
- Paper Trading は本番 DB と完全に分離する設計です。必ず KABUSYS_ENV=paper_trading を指定して起動してください。
- OpenAI 呼び出しはリトライ・バックオフ機構を備えていますが、API キーの漏洩・コストには注意してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）処理
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite への永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor のまとめ（テスト用 run_once / 実運用 run）
    - alert_manager.py — LINE Push API で通知
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 発注フロー・Order State Machine 外部 API
    - reconciler.py — 起動時の自動復旧 / ポジション照合
    - （その他：broker_factory, execution_engine, order_repository 等が存在）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定・単元丸め・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 計算（DuckDB 参照）
    - feature_exploration.py — forward returns / IC / summary 統計
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

（実際のファイル群はソースを参照してください。上は主要機能のマッピングです）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / その他しきい値系（CPU_THRESHOLD_PCT 等）

config.py に各プロパティの詳細とデフォルトが記載されています。例外や不正値は Settings にて検出されます。

---

## 開発 / テストに関するメモ

- Settings はプロジェクトルート（.git または pyproject.toml を基準）から .env を自動ロードします。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続を渡してファクター計算等を呼び出す設計です。研究 / バッチ処理は DuckDB 上で再現可能になるよう配慮されています。
- OpenAI API 呼び出しは専用の呼出ラッパー関数（_call_openai_api）を用いており、ユニットテストではパッチして挙動を制御できます。
- 監視・実行コンポーネントはファイルベースのフラグ（stop / kill / pid）を用いるので、CI 等からの終了制御はこれらのファイルを操作して行えます。

---

## 最後に

この README はソースコード（src/kabusys）に実装された主な機能と運用方法の概要です。実際に運用する場合は .env.example を参考に環境変数を設定し、まずは開発環境（paper_trading）で十分に検証した上で live モードに移行してください。

追加で README に含めたい項目（導入例、環境変数の完全な一覧、デプロイ手順、運用手順書など）があれば教えてください。必要に応じて追記・整備します。