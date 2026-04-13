# KabuSys

日本株自動売買システムのモジュール群 (軽量なプロトタイプ)。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント・レジーム判定）などの主要コンポーネントを含みます。

以下はコードベースから自動生成した README です。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコアライブラリ群です。主な責務は以下の通りです。

- Execution: 注文作成・送信・状態管理、リコンシリエーション（再起動後の同期）
- Monitoring: システム状態・注文滞留・リスク（ドローダウン・ポジション上限）監視、アラート送信（LINE）
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- Research: DuckDB を用いたファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- AI: ニュース記事のセンチメントを LLM (OpenAI) で判定しスコア化、マクロニュースを用いた市場レジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit ダッシュボードなどのユーティリティ

注: DuckDB / SQLite をデータレイヤとして利用。監視ログは SQLite に永続化されます。

---

## 機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV によって paper_trading（モックブローカー）モードを切替。
  - DB 接続（本番または paper_trading 用 SQLite）と DuckDB を使用。
  - プロセス優先度を設定（High）。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動。ポーリング間隔は環境変数で上書き可能（MONITOR_POLL_INTERVAL）。
  - 監視データは production sqlite_path（環境にかかわらず）へ保存。

- Monitoring サブシステム
  - SystemMonitor: CPU/Mem/Disk、Execution プロセス存在、データ鮮度を監視。
  - TradeMonitor: 注文滞留（stale orders）・約定価格異常を検出。
  - RiskMonitor: ドローダウン、ポジション上限チェック。ダッシュボード集計更新。
  - KillSwitch: 条件を満たすと flag ファイルを書き ExecutionEngine 停止指示。
  - AlertManager: LINE プッシュ通知（クールダウン機構あり）。
  - Streamlit ダッシュボードで監視情報の可視化。

- Portfolio モジュール
  - 候補選定（score順）、等配分・スコア加重配分、ポジション数計算（単元丸め・リスクベース）、セクターキャップ、レジーム乗数。

- Research モジュール
  - DuckDB の prices_daily / raw_financials テーブルを用いたファクター計算（momentum, volatility, value）。
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ等。

- AI モジュール
  - news_nlp.score_news: raw_news を集約して OpenAI (gpt-4o-mini) へ送信、銘柄ごとに -1.0..1.0 のスコアを ai_scores テーブルへ書き込む。
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュースセンチメントを合成し market_regime を更新。

- Tools
  - paper_verification_report: Paper Trading DB を解析し、稼働率・注文成功率・レイテンシ等の検証レポートを出力。
  - Streamlit ダッシュボード: data/monitoring.db を読み取り監視情報を可視化。

---

## セットアップ手順

1. Python 環境準備
   - 推奨: Python 3.9+（ソースに明示はありませんが、型アノテーション等を利用）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - インストール例:
     - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt があればそれを使ってください）

3. パッケージの配置
   - 開発時は src ディレクトリを PYTHONPATH に含めるか編集可能インストール:
     - pip install -e .

4. 環境変数設定
   - .env または .env.local をプロジェクトルートに置くと自動で読み込まれます（デフォルトで自動ロード有効）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数とデフォルト:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合必須)
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN (任意、アラート送信に必要)
   - LINE_USER_ID (任意)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db) — Monitoring DB
   - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
   - PAPER_FILL_MODE (default: instant) — instant|partial|never|reject
   - KABUSYS_ENV (default: development) — development | paper_trading | live
   - MONITOR_POLL_INTERVAL (run_monitoring 用、default: 60 秒)
   - PID_FILE_PATH (default: data/execution.pid)
   - KILL_FLAG_PATH (default: data/kill.flag)
   - KILL_FLAG_CLEAR_ON_START (0 or 1)
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - LOG_LEVEL (default: INFO)

5. データ準備
   - DuckDB に prices_daily / raw_financials / raw_news 等のテーブルを用意する必要があります（リサーチ・AI 系機能を使う場合）。
   - 監視・実行系は内部で init_monitoring_db() を呼び、必要な SQLite テーブルを生成します。

---

## 使い方

基本的な起動手順例を示します。実行はパッケージモードで行うのが簡便です（src を PYTHONPATH に含めるかローカルにインストールしてください）。

- ExecutionEngine を起動（通常モード）:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading モード（モックブローカー、データ分離）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Paper Trading は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。

- Monitoring を起動（ポーリングループ）:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=120  # 120 秒

- Streamlit ダッシュボードを起動（監視データの可視化）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコア・レジーム判定について
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取る関数です。API キーは引数または環境変数 OPENAI_API_KEY を使用します。

注意点:
- run_monitoring はコメントどおり Monitoring 用 DB として settings.sqlite_path（production path）を常に使用します（KABUSYS_ENV に依存しない）。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して本番 DB と分離します。
- 実行時にプロセス優先度を "high" に設定しようとします（権限不足の場合は警告でスキップ）。

---

## 主要ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュールです（コードベースに基づく一覧）。

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py
  - run_monitoring.py

  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py

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
    - reconciler.py
    - (その他 broker / order_repository 等のモジュールが存在する想定)

  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

  - tools/
    - __init__.py
    - paper_verification_report.py

  - utils/
    - __init__.py
    - process_priority.py

- data/ (想定されるデータディレクトリ)
  - kabusys.duckdb (DuckDB ファイル)
  - monitoring.db or paper_trading.db (SQLite ファイル)
  - execution.pid, kill.flag などのフラグ/メタファイル

---

## 運用上の注意 / 補足

- 自動環境変数読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動ロードします。OS の環境変数が優先されます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

- フェイルセーフ設計
  - AI 呼び出し（OpenAI）や外部 API の失敗に対してはリトライやフォールバック（スコア0.0など）を行う実装になっています。DB 書き込みは可能な限り冪等に実装されています。

- セキュリティ
  - API キーやパスワードは環境変数で管理してください（リポジトリに直接保存しない）。

---

この README はコード中の docstring／コメントからまとめたものです。運用時には DuckDB のデータ構築手順（市場データの投入）、ブローカー接続情報の設定、LINE API 設定等が別途必要になります。必要であれば、各モジュール（Execution / Monitoring / AI / Research）の詳細な運用手順・設定例やサンプル .env を作成しますのでお知らせください。