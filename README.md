# KabuSys

日本株自動売買システムのコードベース（抜粋）。この README はリポジトリ内の主要コンポーネントと実行手順をまとめたものです。

注意: 実行には外部 API キー（J-Quants / Kabuステーション / OpenAI 等）や native ライブラリ（psutil など）が必要になる場合があります。以下はソースコードから読み取れる仕様の要約です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムの基盤実装群です。主要責務は以下:

- 注文作成・送信・状態同期（Execution）
- リスク管理（ドローダウン・ポジション上限等）
- 監視（システム状態、注文滞留、約定異常の検出）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 研究用ファクター計算（Momentum / Value / Volatility 等）
- ニュースの NLP によるセンチメント評価（OpenAI）
- Paper Trading 用の隔離DBサポートと検証レポート生成
- 監視ダッシュボード（Streamlit）

コードは純粋関数群（ポートフォリオ・リサーチ類）と、永続化・監視・Execution 周りの実装で構成されています。

---

## 主な機能一覧

- Execution
  - OrderManager / OrderRepository / Reconciler による注文ライフサイクル管理と起動時リコンシリエーション
  - Broker クライアントを設定に応じて切替（実運用 / paper_trading 用 Mock）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション数の監視、kill.flag の生成（Execution 停止シグナル）
  - AlertManager: LINE Push による通知（クールダウン管理あり）
  - Streamlit による監視ダッシュボード
- Portfolio
  - 候補選定（スコア順）、等重／スコア加重配分、リスク制約（セクターキャップ、レジーム乗数）、株数決定（単元丸め、aggregate cap）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索：将来リターン計算、IC（Spearman）計算、統計サマリ
- AI
  - news_nlp: raw_news -> OpenAI（gpt-4o-mini）で銘柄別センチメント算出、ai_scores へ書き込み
  - regime_detector: ETF (1321) の MA とマクロニュースで市場レジーム（bull/neutral/bear）を判定
- Tools
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL 判定するレポートを出力

---

## セットアップ手順（開発環境向け）

以下はソースから推測される一般的なセットアップ手順です。実環境に合わせて適宜調整してください。

1. Python 環境
   - Python 3.9+ を推奨（型注釈や新しい構文を使用）
   - 仮想環境を作成する例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 代表的な依存: duckdb, psutil, openai, requests, streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （実プロジェクトでは requirements.txt や poetry/poetry.lock 等があるはずです）

3. 環境変数 / .env
   - プロジェクトは起動時にプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索して `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。
   - 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主要な環境変数（コード中で参照されるもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API refresh token（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API key（AI 機能を使う場合）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
     - paper_trading の場合、paper 用 DB に分離して動作します
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の MockBroker の約定モード (instant|partial|never|reject)（デフォルト: instant）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH: Execution PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
   - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

4. データディレクトリの作成
   - デフォルトでは data/ 下に DB や PID/flag を配置します:
     - mkdir -p data

---

## 使い方（起動例）

1. ExecutionEngine（発注エンジン）を起動
   - 通常実行（本番 or development）:
     - KABUSYS_ENV=development python -m kabusys.run_execution
   - Paper Trading:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - Paper 環境では MockBrokerClient を使い data/paper_trading.db に記録します。

2. Monitoring（監視ループ）を起動
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます。
     - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視データは本番 DB として扱う想定）。

3. Streamlit 監視ダッシュボード
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視 DB を read-only モードで開きます。MonitoringEngine を先に起動してデータを書き込んでおく必要があります。

4. Paper Trading 検証レポート
   - 単発レポートを生成:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB を指定する場合:
       - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI モジュール（スクリプト化の例）
   - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を受け取る関数です。簡単な呼び出し例（Python スクリプト内）:
     - from kabusys.ai.news_nlp import score_news
     - import duckdb, datetime
     - conn = duckdb.connect("data/kabusys.duckdb")
     - score_news(conn, datetime.date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")

   - API キーが未設定の場合は ValueError を送出します。

---

## 重要な実行・動作上の仕様メモ

- Settings モジュールは .env / .env.local を自動読み込みします（OS 環境変数が保護されます）。無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- run_monitoring と run_execution 起動時にプロセス優先度を "high" にセットしようとします（psutil を使用）。権限がない場合は警告が出ますが継続します。
- Paper Trading モードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- MonitoringDB (SQLite) は init_monitoring_db() により冪等にテーブルを生成・マイグレーションします。
- KillSwitch は data/kill.flag を作成して ExecutionEngine 停止を促す仕組みです（RiskMonitor などから評価・生成）。
- OpenAI 呼び出しはリトライや JSON パースの頑健化が組み込まれていますが、API のコストやレート制限には注意してください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・モジュールのツリー（ソースから抜粋したもの）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                          — 環境変数 / Settings 管理
    - run_execution.py                   — ExecutionEngine 起動スクリプト
    - run_monitoring.py                  — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py     — Paper Trading 検証レポート
    - ai/
      - __init__.py
      - news_nlp.py                      — ニュース NLP（OpenAI）による銘柄スコアリング
      - regime_detector.py               — 市場レジーム判定（MA + マクロ NLP）
    - monitoring/
      - __init__.py
      - monitoring_db.py                 — SQLite 永続層（監視ログ）
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
      - (その他 Broker / Engine / OrderRepository 等のファイル)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py

この README はコードから読み取れる挙動を基に作成しています。実運用やローカル開発では、プロジェクト固有の README / docs / デプロイ手順に従ってください。

---

もし README に追記してほしい点（例: 想定される requirements.txt の内容、CI / デプロイ手順、開発用の docker-compose 例など）があれば教えてください。