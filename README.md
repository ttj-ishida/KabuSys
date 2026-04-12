# KabuSys

日本株自動売買システムの一部を抜粋したコードベースの README。監視（Monitoring）、実行（Execution）、ポートフォリオ構築、リサーチ、AI ニューススコアリングなどのモジュールを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は次の通りです。

- Execution：ブローカーとの発注・注文状態管理・再同期（Reconciler）
- Monitoring：プロセス／システム状態、注文異常、リスク閾値の監視とログ永続化（SQLite）
- Research：DuckDB を使ったファクター計算・特徴量探索
- Portfolio：候補選定・重み計算・ポジションサイズ算出・リスク調整
- AI：OpenAI を利用したニュースのセンチメント評価と市場レジーム判定
- Tools：Paper Trading の検証レポート生成などユーティリティスクリプト

設計上の特徴：
- DuckDB（時系列市場データ）と SQLite（監視・発注ログ）を併用
- 環境（development / paper_trading / live）に応じた動作分離（paper_trading は発注をモックし別DBへ記録）
- OpenAI API を用いた NLP スコアリング（失敗時はフェイルセーフで継続）
- .env ファイルの自動読み込み（プロジェクトルートを探索）

---

## 機能一覧（抜粋）

- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカーファクトリ、OrderManager、RiskManager、Reconciler による起動時・稼働時処理
  - paper_trading 環境では MockBroker を使用し data/paper_trading.db に記録

- 監視系
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID / データ鮮度を監視・ログ化
  - TradeMonitor: 滞留注文（stale）や約定価格異常を検知
  - RiskMonitor: ドローダウンやポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件を満たしたら kill.flag を書き Execution を停止させる（ファイルフラグ）
  - AlertManager: LINE Push による通知（チャンネル設定がある場合）
  - MonitoringEngine: 上記監視群を束ねてポーリング

- リサーチ / ファクター
  - momentum / volatility / value 等のファクター算出（DuckDB 経由）
  - forward return / IC / 統計サマリ等の分析ユーティリティ

- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等配分・スコア重み配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- AI（OpenAI）
  - ニュースを銘柄単位に集約して OpenAI（gpt-4o-mini）でセンチメント評価、ai_scores テーブルへ保存
  - マクロニュース + ETF MA200 乖離を用いた market regime 判定（bull/neutral/bear）

- ツール
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL を判定するレポート生成

---

## セットアップ手順

※ リポジトリに requirements.txt がない場合は下記パッケージをインストールしてください。

1. Python 環境（推奨: Python 3.10+）を用意し、仮想環境を作成・有効化します。

   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 必要パッケージのインストール（例）

   pip install duckdb psutil openai requests streamlit

   （プロジェクトで他の依存がある場合は適宜追加してください）

3. 環境変数 / .env の準備

   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（CWD ではなくソースファイルの親ディレクトリから .git または pyproject.toml を探索してプロジェクトルートを決定します）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（必要に応じて設定）:

   - KABUSYS_ENV = development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN = ...
   - KABU_API_PASSWORD = ...
   - OPENAI_API_KEY = ... (AI 機能を使う場合必須)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知を行う場合)
   - PAPER_FILL_MODE = instant | partial | never | reject
   - PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
   - SQLITE_PATH = data/monitoring.db
   - DUCKDB_PATH = data/kabusys.duckdb
   - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, CPU_THRESHOLD_PCT, など

4. データディレクトリ作成（必要に応じて）

   mkdir -p data

---

## 使い方（主なコマンド）

- Monitoring（ポーリング監視ループ）の起動

  環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。起動時にプロセス優先度を "high" に設定します。

  python -m kabusys.run_monitoring

  例（ポーリングを30秒に設定）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution（発注エンジン）の起動

  KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、Paper 用 SQLite（デフォルト: data/paper_trading.db）に記録します。起動時にプロセス優先度を "high" に設定します。

  python -m kabusys.run_execution

- Paper Trading 検証レポート生成

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB を指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- 監視ダッシュボード（Streamlit）

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI スコアリング / レジーム判定（プログラム的に利用）

  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - target_date: date オブジェクト
    - api_key: None の場合は環境変数 OPENAI_API_KEY を参照

  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらは DuckDB のテーブル（raw_news, news_symbols, ai_scores, prices_daily, market_regime 等）に依存します。

---

## 重要な振る舞い・注意点

- .env の自動読み込み
  - 優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードはデフォルトで有効。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパーサはシェル風構文（export 付き、クォート、インラインコメント等）に対応。

- データストア
  - Monitoring（system_status / trade_logs / positions / risk_logs / dashboard）は SQLite（Settings.sqlite_path）に永続化。
  - DuckDB は prices_daily / raw_financials 等の大規模分析用に使う想定（Settings.duckdb_path）。
  - paper_trading 環境では `paper_sqlite_path` を使用して本番 DB と分離。

- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼び、psutil を使って OS に応じた優先度を設定します。権限不足や未対応 OS の場合は警告を出してスキップします。

- Kill Switch
  - KillSwitch はリスク閾値を満たすと `KILL_FLAG_PATH`（デフォルト data/kill.flag）にテキストを書き込みます。ExecutionEngine はこのフラグファイルを読み停止する設計になっています（ファイル存在で停止）。

- OpenAI 呼び出し
  - API 呼び出しはリトライ（指数バックオフ）を行いますが、API キー未設定の場合はエラー（ValueError）を投げます。失敗時は安全側の既定値にフォールバックする箇所があります（macro sentiment=0 等）。

- DB スキーマ
  - monitoring_db.init_monitoring_db(conn) で必要なテーブル・インデックスを冪等に作成します。既存 DB に対する簡単なマイグレーション（カラム追加）処理も含みます。

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py                      — 環境変数/設定読み取り
    run_monitoring.py              — Monitoring の起動スクリプト
    run_execution.py               — Execution の起動スクリプト

    ai/
      __init__.py
      news_nlp.py                  — ニュース NLP スコアリング
      regime_detector.py          — 市場レジーム判定

    monitoring/
      __init__.py
      monitoring_db.py            — SQLite 永続化層（monitoring DB）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py

    execution/
      order_manager.py
      reconciler.py
      (その他 broker / order_repo 等の実装ファイルが存在する想定)

    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      __init__.py
      factor_research.py
      feature_exploration.py

    tools/
      __init__.py
      paper_verification_report.py

    utils/
      __init__.py
      process_priority.py

ドキュメントや仕様はソース内の docstring に詳細が記載されています。各モジュールは可能な限り純粋関数設計（副作用最小）やフェイルセーフ方針で書かれています。

---

## 開発メモ / 推奨事項

- 本番で実行する場合は KABUSYS_ENV=live を使い、適切な DB パスと API シークレットを設定してください。
- Paper Trading の検証は必ず paper_trading 環境で分離して行ってください（DB・ブローカーが分離されます）。
- OpenAI を使う機能は API 利用制限・コストが発生するため運用前に制御（バッチサイズ、頻度、バックオフ設定）を確認してください。
- streamlit ダッシュボードは監視 DB を読み取り専用で開くため、MonitoringEngine を先に起動してデータを蓄積してください。

---

必要であれば README に追記（例: サンプル .env、詳細な起動例、各モジュールの API ドキュメント自動生成方法）を作成します。どの情報を優先して追加しますか？