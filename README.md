# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視ツール群をまとめた軽量フレームワークです。  
このリポジトリは取引の実行エンジン、監視（モニタリング）、ポートフォリオ構築、ファクター研究、AI を使ったニュース評価などのコンポーネントを含みます。

この README はプロジェクトの概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

- Python ベースの日本株自動売買（KabuSys）向けライブラリ／アプリケーション群。
- コンポーネント群：
  - ExecutionEngine（発注・リスク管理・再同期）
  - Monitoring（システム・注文・リスク監視、LINE 通知、ストリームリットダッシュボード）
  - Portfolio（銘柄選定・配分・株数決定・セクター制限等）
  - Research（ファクター計算、将来リターン、IC 計算）
  - AI（ニュースの NLP によるセンチメント評価、レジーム判定）
  - Tools（Paper Trading 検証レポート等）
- 設定は環境変数（.env / .env.local）で管理。配布後にも動作するようにプロジェクトルート探索ロジックを備えています。

---

## 機能一覧

主な機能（抜粋）：

- Execution
  - ブローカークライアント抽象化（本番 / paper_trading 用 Mock 切替）
  - 発注、状態同期（Reconciler）、OrderManager、OrderRepository
  - RiskManager（各種リスク制約）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存 / データ鮮度チェック
  - TradeMonitor：滞留注文（stale order）・約定価格異常チェック
  - RiskMonitor：ドローダウン・保有銘柄上限チェック、ダッシュボード更新
  - KillSwitch：flag ファイルを書き込んで ExecutionEngine に停止シグナル送信
  - AlertManager：LINE Push による通知（クールダウン管理）
  - streamlit_dashboard：監視ダッシュボード表示（read-only）
  - Monitoring DB（SQLite）用の永続化・ユーティリティ
- Portfolio
  - 銘柄選定、重み計算（等額 / スコア加重）
  - セクターキャップ、レジーム乗数、ポジションサイズ算出（単元株丸め、aggregate cap）
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - news_nlp: OpenAI API を用いたニュースセンチメントの銘柄別スコア化（ai_scores テーブルへ保存）
  - regime_detector: ETF（1321）の MA 乖離とマクロニュース LLM 評価を合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB（data/paper_trading.db）から検証レポートを生成

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意し、仮想環境を作成・有効化します。

   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール（例）:

   pip install duckdb psutil requests streamlit openai

   ※ プロジェクトに requirements.txt があればそれを使ってください。上記はコード中で使われている主要ライブラリの一覧です。

3. データディレクトリを作成（任意）:

   mkdir -p data

4. 環境変数を設定 (.env/.env.local または OS 環境変数)

   主要な環境変数（例・説明）:

   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須: 一部モジュール）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須: 実取引時）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
   - KABUSYS_ENV: 環境。development / paper_trading / live（デフォルト: development）
     - paper_trading の場合、MockBrokerClient を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ分離記録されます。
   - PAPER_FILL_MODE: paper_trading のフィルモード（instant / partial / never / reject、デフォルト instant）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
   - KILL_FLAG_PATH: Kill Switch のフラグファイルパス（デフォルト data/kill.flag）
   - KILL_FLAG_CLEAR_ON_START: 実行開始時に kill.flag を自動削除する場合は "1"
   - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
   - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（空なら通知は送られずログのみ）

   .env の自動読み込みは、プロジェクトルート（.git または pyproject.toml がある場所）を探索して行われます。テストなどで自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（代表的な起動方法）

- ExecutionEngine の起動（本番は KABUSYS_ENV を live に設定）:

  python -m kabusys.run_execution

  動作のポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db にトレードログを残します（本番 DB とは完全分離）。
  - 実行開始時にプロセス優先度を high に設定します（psutil に依存。権限がない場合は警告ログ）。

- Monitoring（SystemMonitor のポーリングループ）:

  python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path（Settings.sqlite_path）を使用します（監視ログは常に単一 DB に集約する意図）。

- Streamlit ダッシュボード（監視画面）:

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  - ダッシュボードは監視 DB を read-only で開きます。MonitoringEngine を先に起動してデータを用意してください。

- Paper Trading 検証レポート:

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db で DB を指定可能（デフォルト data/paper_trading.db）

- AI 関連（ニューススコアリング / レジーム判定）:

  コードから下記関数を呼びます（DuckDB 接続 + target_date + API キーが必要）。

  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  実行時には OPENAI_API_KEY を環境変数にセットするか、関数引数で api_key を渡してください。API 呼び出しはリトライ・バックオフ・レスポンス検証を行います。

---

## 重要な挙動メモ

- .env パーサは export KEY=val 形式やクォート・エスケープ・インラインコメントに対応しています。
- Monitoring は process の生存チェックのため PID ファイル（PID_FILE_PATH）を参照します。PID が古く有効でない場合は stale PID として検出してファイルを削除します。
- KillSwitch は条件を満たすと kill.flag（KILL_FLAG_PATH）へ理由文を書き込み、ExecutionEngine はこのファイルを存在検査して停止処理を行う設計です。kill.flag は既に存在する場合に上書きしません（冪等）。
- Paper Trading は実データベースと分離されます（PAPER_TRADING_SQLITE_PATH を使用）。PAPER_FILL_MODE によって MockBroker の約定挙動が変わります。
- DuckDB を利用して大量時系列データ（prices_daily, raw_financials, raw_news など）を扱うように設計されています。

---

## ディレクトリ構成（主なファイルと簡単な説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定の読み込みと Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV に依存）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金制約処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite による監視データ層（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 滞留注文・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — flag による停止シグナル
    - alert_manager.py — LINE 通知（push）
    - monitoring_engine.py — 各モニタを束ねる実行ループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注ワークフロー / 状態遷移
    - reconciler.py — 再起動時リコンシリエーション（発注同期・ポジション差分検出）
    - 他（broker_factory 等はリポジトリ中に存在）
  - research/
    - factor_research.py — モメンタム/ボラ/バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース記事を LLM でセンチメント化して ai_scores に書き込む
    - regime_detector.py — レジーム判定と market_regime テーブルへの書込み
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

---

## よくあるタスク / 例

- 監視をデーモン的に動かす（UNIX 例）:
  - KABUSYS_ENV=production MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring &

- Paper Trading の検証レポートを作る:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit で監視 UI を表示:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 開発メモ / 拡張ポイント

- position_sizing, portfolio_builder 等は純粋関数で DB 非依存なのでユニットテストが書きやすいです。
- AI モジュールは API 呼び出しのラッパーを分離しており、テストでは _call_openai_api をモックしてテスト可能です。
- DuckDB のテーブル設計（prices_daily / raw_financials / raw_news 等）に合わせたデータ投入パイプラインが別モジュール（kabusys.data.pipeline等）として存在します（本 README では省略）。

---

## サポート / 問い合わせ

実運用・本番接続（kabuステーションや取引資産を動かす場合）は十分な検証とリスク管理を行ってください。設定ミスや権限不足、API の呼び出しエラーによる予期せぬ挙動に注意してください。

不明点や追加で README に載せてほしい項目があれば教えてください。README を実プロジェクトの README.md として整備するために、requirements.txt やサンプル .env.example を追加することも推奨します。