# KabuSys

KabuSys は日本株向けの自動売買／リサーチ／監視ツール群です。本リポジトリはアルゴリズムトレーディングのコアコンポーネント（Execution, Monitoring, Portfolio Construction, Research, AI を用いたニュース解析 等）を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

- 自動売買の実行エンジン（ExecutionEngine）と、その監視（MonitoringEngine）を提供します。
- Paper Trading（検証用）モードと Live（本番）モードを区別して運用可能。Paper Trading は本番 DB から分離して記録します。
- DuckDB を使ったリサーチ／ファクター計算（prices_daily, raw_financials 等）をサポート。
- OpenAI（gpt-4o-mini）を利用したニュースのセンチメント解析や市場レジーム判定機能を備えています（API キー必須）。
- 監視結果は SQLite に永続化され、Streamlit ベースのダッシュボードで可視化できます。

---

## 主な機能一覧

- Execution（発注）関連
  - 発注の作成 → ブローカー送信 → 同期・再突合（Reconciler）ロジック
  - OrderManager, OrderRepository を用いた状態管理
  - Broker クライアント切替（実口座／モック）

- Monitoring（監視）
  - システム状態監視（CPU/メモリ/ディスク、実行プロセス存在チェック、データ鮮度チェック）
  - 注文滞留 / 約定異常価格検知
  - ドローダウン・ポジション上限監視と KillSwitch（flag ファイルによる ExecutionEngine 停止トリガ）
  - LINE push によるアラート通知（AlertManager）
  - Streamlit ダッシュボード

- Portfolio（銘柄選定）
  - 候補選定、等金額・スコア加重の重み計算
  - セクター集中制限、レジームによる乗数調整
  - 発注株数算出（単元株丸め、リスクベース配分、利用可能資金のスケーリング）

- Research（ファクター計算）
  - Momentum / Volatility / Value ファクター計算（DuckDB + SQL）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等

- AI（ニュース NLP / レジーム判定）
  - raw_news から銘柄ごとにテキストを集約し OpenAI でスコアリング（ai_scores テーブルへ書込み）
  - マクロニュース + ma200 乖離を統合した市場レジーム判定

- ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ（psutil ベース）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）

---

## セットアップ手順（ローカル）

1. Python 環境を準備
   - 推奨: Python 3.9+（コードは typing 等の近年機能を利用しています）
   - 仮想環境の作成（例）
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がない場合は最低限以下をインストールしてください：
     - duckdb, psutil, requests, streamlit, openai
   - 例:
     - pip install duckdb psutil requests streamlit openai

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にしたい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主な環境変数（抜粋）:
     - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須機能で利用）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE通知用
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定動作）
     - PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL: "DEBUG","INFO",...（Settings で検証）

4. データディレクトリ
   - デフォルトで data/ 以下に DB 等を作る想定です。必要に応じて `mkdir -p data` を実行してください。

---

## 実行方法（簡易）

- 監視ループを起動（MonitoringEngine の簡易スクリプト）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - 監視は Settings に従い、monitoring 用の sqlite_path（SQLITE_PATH）を常に使用します（環境に依存せず本番 DB を使用します）

- Execution エンジンを起動（実行セッション）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し PAPER_TRADING_SQLITE_PATH（data/paper_trading.db など）に記録します（本番 DB と完全分離）。
    - 起動時にプロセス優先度を High に設定しようと試みます（権限等により失敗する場合は警告ログのみ）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db（無指定時は PAPER_TRADING_SQLITE_PATH 環境変数 → data/paper_trading.db）

---

## 使い方（ワークフロー例）

1. 環境変数を設定（.env）
   - KABUSYS_ENV=paper_trading
   - OPENAI_API_KEY=xxxx
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

2. 監視を開始
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

3. Execution を開始（別プロセス）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

4. 状態確認・可視化
   - Streamlit ダッシュボードを起動して監視データを確認

5. Paper Trading の検証
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

6. AI スコアリング（プログラム的に）
   - DuckDB 接続を構築し、kabusys.ai.score_news(conn, target_date, api_key=...)
   - 例（簡易）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, date(2026, 4, 10), api_key="...")

---

## 重要な設計上の注意点

- .env 自動読み込み
  - プロジェクトルートを .git / pyproject.toml から探索して `.env` / `.env.local` を自動的に読み込みします。
  - OS 環境変数が優先されます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB の分離
  - Monitoring（監視）用 DB（SQLITE_PATH）は常に本番用を想定しており、Monitoring は KABUSYS_ENV にかかわらず指定された sqlite_path を使用します。
  - Execution は KABUSYS_ENV が paper_trading の場合、paper_sqlite_path を使用して本番 DB と完全に分離します。

- OpenAI API
  - AI 機能（ニュース NLP、レジーム判定）は OPENAI_API_KEY を必要とします。API 呼び出しは冗長性（リトライ、フォールバック値）を取り入れていますが、キー未設定の場合は例外となる関数がありますので注意してください。

- プロセス優先度設定
  - 起動スクリプトは起動直後に set_process_priority("high") を呼びます（psutil による）。権限不足や未サポート OS の場合は警告を出して継続します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py (バージョン定義)
  - config.py (設定 / .env パーサ / Settings クラス)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - monitoring/
    - monitoring_db.py (SQLite 永続化 + MonitoringDB クラス)
    - system_monitor.py (システム状態・データ鮮度監視)
    - trade_monitor.py (滞留注文・約定異常監視)
    - risk_monitor.py (ドローダウン / ポジション上限監視)
    - kill_switch.py (flag ファイルによる停止トリガ)
    - alert_manager.py (LINE push)
    - monitoring_engine.py (各 Monitor を束ねる)
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（ブローカー周り・実装ファイル）
  - portfolio/
    - portfolio_builder.py (候補選定 / 重み付け)
    - position_sizing.py (株数決定 / スケーリング)
    - risk_adjustment.py (セクターキャップ / レジーム乗数)
  - research/
    - factor_research.py (momentum/volatility/value)
    - feature_exploration.py (forward returns / IC / summary)
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity)
  - data/ (既定の DB 配置先 / out-of-repo データ格納想定)

---

## 開発者向けメモ

- テスト可能な設計
  - OpenAI 呼び出し部分は _call_openai_api を分離しているため、テスト時にパッチ可能です（unittest.mock.patch）。
  - MonitoringDB の初期化スクリプトは冪等であり、既存 DB へのマイグレーションロジック（カラム追加）を含みます。

- ロギング
  - 起動スクリプトは basicConfig(level=logging.INFO) を使用しています。Settings.log_level による制御が他箇所に統合されていない点に注意（将来調整の余地あり）。

- ファイルロケーション
  - PID / kill.flag / DB のデフォルトパスは Settings で定義されています。運用環境に合わせて .env で上書きしてください。

---

## よく使うコマンドまとめ

- 監視開始:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行開始（paper_trading 例）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコアリング（プログラム的呼び出し）:
  - score_news(conn, target_date, api_key="...") / score_regime(conn, target_date, api_key="...")

---

README はプロジェクトの導入と基本的操作をまとめたものです。実際の運用では .env の管理、OpenAI キーやブローカークレデンシャルの安全な取り扱い、DB のバックアップ・権限設定等に十分ご注意ください。必要ならば各モジュールの詳細ドキュメント（関数仕様・例外挙動・DB スキーマ）も追加で作成します。