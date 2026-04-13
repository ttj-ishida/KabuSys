# KabuSys

日本株自動売買システムのライブラリ群（README 抜粋）。  
このリポジトリは戦略・発注・監視・リサーチ・AI 補助など、運用に必要な主要コンポーネントを含みます。

---

## プロジェクト概要
KabuSys は日本株アルゴリズムトレード向けの小規模フレームワークです。  
主要な責務は次の通りです。

- シグナル → 注文（ExecutionEngine、OrderManager、BrokerClient）
- 発注状態の永続化・復元（OrderRepository、Reconciler）
- 運用監視（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- リサーチ（ファクター計算、IC 計算、将来リターン等）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 運用補助ツール（paper trading の検証レポート、Streamlit ダッシュボード）

設計方針として、DuckDB / SQLite を用いたローカルデータ処理、外部 API 呼び出しは抽象化（OpenAI・証券 API 等）、およびルックアヘッドバイアス回避に配慮した実装がなされています。

---

## 機能一覧
- Execution
  - 注文作成・送信・状態同期・再起動時のリコンシリエーション
  - paper_trading 用にモックブローカーと専用 DB を分離
- Monitoring
  - システム資源（CPU/MEM/DISK）、プロセス存否、データ鮮度の監視
  - 注文滞留・約定価格の異常検出
  - ドローダウン・ポジション上限の監視
  - kill.flag による ExecutionEngine 停止シグナル
  - LINE による通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定（スコア順）、等重・スコア重み配分、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ算出（単元丸め・集約キャップ）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB SQL）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- AI
  - News NLP：OpenAI（gpt-4o-mini）でニュースを銘柄別にセンチメント化し ai_scores へ保存
  - Regime Detector：ETF（1321）MA乖離とマクロニュースを組み合わせて日次レジーム判定
  - API 呼び出しは安全なリトライやフェイルセーフを備える
- Tools
  - paper_trading 向け検証レポート生成スクリプト
  - Streamlit ダッシュボード起動スクリプト

---

## 必要条件（例）
- Python 3.10+
- ライブラリ（抜粋）
  - duckdb
  - psutil
  - openai
  - streamlit (ダッシュボード利用時)
  - requests
  - （必要に応じてブローカークライアント等）

requirements.txt がない場合は上記を pip でインストールしてください。例えば:
pip install duckdb psutil openai streamlit requests

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt  または上記必要パッケージを個別インストール

3. 設定（環境変数）
   - プロジェクトルートに `.env` / `.env.local` を置けます（自動読み込み）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須: 該当機能を使う場合）
     - KABU_API_PASSWORD — kabu API パスワード（必須: ブローカー利用）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時、必須）
     - KABUSYS_ENV — 起動環境（development | paper_trading | live）デフォルト: development
     - LOG_LEVEL — ログレベル（DEBUG|INFO|...）デフォルト: INFO
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH — Execution pid ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH — kill.flag（デフォルト: data/kill.flag）
     - PAPER_FILL_MODE — paper_trading の fill 動作（instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START — "1" にすると起動時に kill.flag をクリアするオプション（利用箇所に注意）

4. データベース初期化
   - 監視 DB（SQLite）は起動スクリプトが自動で init します（init_monitoring_db）。DuckDB のスキーマや prices_daily/raw_financials 等は運用に応じて用意してください。

---

## 使い方（主なコマンド）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作: Settings を読み取り、KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い MockBroker を用いる（本番 DB と分離）。
  - 起動時にプロセス優先度を High に設定します（set_process_priority）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は monitoring DB（sqlite_path）へログを永続化します。Monitoring は KABUSYS_ENV にかかわらず production sqlite_path を使用する仕様です。

- Streamlit ダッシュボード起動（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview/Positions/Orders/System を表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH より優先して DB を指定できます。
  - 本スクリプトは uptime / fill rate / send rate / P95 latency 等を集計し PASS/FAIL 判定を出力します。

- AI 機能（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news を集約して OpenAI で銘柄ごとにセンチメントを計算し ai_scores に書き込みます。
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します（必須）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF（1321）MA200 乖離 + マクロニュースセンチメントで日次レジームを算出し market_regime テーブルへ保存します。

注意: OpenAI 呼び出しはレート制限やネットワークエラーに対するリトライとフェイルセーフを備えていますが、API キーの設定が必須です。

---

## 設定ファイル（.env）読み込み仕様
- 自動読み込み順序:
  - OS 環境変数 > .env.local > .env
- プロジェクトルートの検出:
  - 現在のファイル位置から親ディレクトリを上がり、.git または pyproject.toml を基準にプロジェクトルートを探索します。見つからない場合は自動読み込みをスキップします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを抑制できます（テスト用途など）。

.env のパースはシンプルな独自実装です。シングル/ダブルクォート、export プレフィックス、インラインコメント等に対応します。

---

## 注意点 / 運用上のヒント
- run_monitoring は監視専用の SQLite（settings.sqlite_path）を開きます。Monitoring は常に「本番の sqlite_path」を参照するため、paper_trading 環境でも別 DB を使う実装とはなっていません（run_execution は paper_trading の場合別 DB を使用）。
- kill.flag による停止は冪等で、既存ファイルがあれば書き換えません。必要なら起動時にファイルを削除してください（KillSwitch.clear や KILL_FLAG_CLEAR_ON_START を利用）。
- process priority の設定は OS に依存します。権限不足等で設定できない場合はログに警告が出ますが処理自体は継続します。
- DuckDB と SQLite の両方を使います。DuckDB は時系列・ファクター計算など大規模読み取り向け、SQLite は監視・発注ログ等の永続化向けに使い分けています。
- AI 機能を使用する場合は OPENAI_API_KEY を必ず設定してください。API 呼び出しの料金に注意。

---

## ディレクトリ構成（主要ファイル抜粋）
（実際のリポジトリに合わせて調整してください）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — 優先度 / CPU affinity ユーティリティ
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py  (他ファイル)
    - broker_factory.py
    - broker_api.py
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite schema + 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/ (想定ローカル DB ファイル用ディレクトリ)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - monitoring.db    (デフォルト SQLITE_PATH)
    - paper_trading.db (paper_trading 用 SQLite)

- src/kabusys/tools/
  - __init__.py
  - paper_verification_report.py

---

## 追加情報 / 開発者向け
- ログレベルは環境変数 LOG_LEVEL で調整できます（Settings.log_level）。
- Settings クラスはプロパティベースで値を提供します。未設定の必須値は _require() により ValueError を発生させます。
- DuckDB 接続は duckdb.connect() を使用して受け渡す設計です。関数は接続オブジェクトを外部から渡すことを前提としています（テストの差し替えが容易）。
- 単体テストやモックの利用を想定した設計（API 呼び出し箇所は内部関数をパッチ可能）になっています。

---

この README はコードベースの主要点をまとめたものです。実運用・デプロイ時は各モジュールの詳細ドキュメント（docstrings）および環境ごとの設定を必ず確認してください。必要であれば、README にインストール用 requirements.txt や systemd サービス定義、Dockerfile のサンプルを追加することを推奨します。