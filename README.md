# KabuSys

日本株自動売買システムのコードベース（簡易 README）。  
この README はリポジトリの主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成・運用上の注意点をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買（Execution）とシステム監視（Monitoring）、リサーチ/ファクター計算、AI を使ったニュースセンチメント評価などを含む汎用的な自動売買基盤です。  
主要な機能は以下のとおりです。

---

## 機能一覧

- Execution
  - 注文生成 / ブローカークライアント経由の発注（本番または Paper Trading の切替）
  - OrderManager を中心とした注文状態管理
  - 起動時のリコンシリエーション（Reconciler）
  - RiskManager によるリスク制御
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検知
  - RiskMonitor: ドローダウン、ポジション上限監視
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込みと LINE 通知
  - monitoring DB（SQLite）へのログ永続化と Streamlit ベースダッシュボード
- Portfolio construction
  - 候補選定・重み算出（等分配・スコア重み）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元丸め、aggregate cap）
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC、ファクターサマリ等のユーティリティ
- AI（OpenAI）連携
  - ニュースのセンチメント解析（gpt-4o-mini を想定）と ai_scores 書き込み
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- 各種ツール
  - Paper Trading 検証レポート生成スクリプト

---

## 必要条件（推奨）

- Python 3.10+
- pip
- SQLite（OS 標準）
- 外部ライブラリ（主要なもの）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード用）
- ネットワークアクセス（OpenAI / LINE を使う場合）

requirements.txt が無い場合は次のようにインストール例（プロジェクト適宜調整）:

pip install duckdb psutil requests openai streamlit

---

## 環境変数（主なもの）

このプロジェクトは .env / .env.local を自動読み込みします（プロジェクトルートが検出可能な場合）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数：

- KABUSYS_ENV: 稼働モード（development / paper_trading / live）  
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用トークン（AlertManager）
- LINE_USER_ID: LINE Push 送信先ユーザID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading 注文約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH 等（Settings 参照）

設定値は `kabusys.config.Settings` から取得されます。未設定の必須値は例外になります。

例（.env の抜粋）:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

---

## セットアップ手順

1. リポジトリをクローン
2. 仮想環境を作成・有効化（例: python -m venv .venv）
3. 必要パッケージをインストール
   - 例: pip install -r requirements.txt
   - requirements.txt がない場合:
     pip install duckdb psutil requests openai streamlit
4. .env をプロジェクトルートに作成（.env.example がある場合は参照）
5. data ディレクトリ作成（自動的に作られる箇所もありますが手動で準備しておくと良い）:
   mkdir -p data
6. DuckDB / SQLite の初期化は各スクリプト実行時に必要テーブルが作成されます（init_monitoring_db）。

---

## 実行方法

各コンポーネントはモジュールとして起動できます。プロジェクトルートから次を実行してください。

- 監視ループ（SystemMonitor を直接動かす単純起動）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使います。
  - python -m kabusys.run_execution

- Streamlit ダッシュボード（監視画面）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - あるいはダッシュボード内の DB 引数を指定

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（プログラムから呼び出し）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と target_date を受け取り、OpenAI API を使用します。API キーが引数になければ環境変数 OPENAI_API_KEY を参照します。

---

## 運用ノート / フラグファイル

- stop_requested.flag
  - run_monitoring.py / run_execution.py はプロジェクトルート配下 `data/stop_requested.flag`（実装内 path を参照）を監視し、存在を検知するとループを終了します。
  - 手動停止（安全シャットダウン）に利用できます。

- kill.flag
  - KillSwitch は内部条件（ドローダウン超過 など）で `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります（Execution 側は Settings.kill_flag_path を参照して動作）。
  - KillSwitch は既に存在する場合は再書き込みしません（冪等）。

- PID ファイル
  - ExecutionEngine は起動時に PID ファイルを書き込みます。SystemMonitor はこの PID を見てプロセスの存否をチェックし、stale PID を検知するとファイルを削除してアラートします。

- ポーリング間隔
  - MonitoringEngine のデフォルトは 60 秒。MONITOR_POLL_INTERVAL にて上書きできます（run_monitoring の起動スクリプトが使う）。

- ログ
  - 各スクリプトは logging.basicConfig(level=logging.INFO) を用いて起動します。LOG_LEVEL 環境変数で変更できます（Settings.log_level）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
- run_execution.py              — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポートツール
- monitoring/
  - __init__.py
  - monitoring_db.py             — monitoring SQLite レイヤ
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
  - ...（ブローカークライアント等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- data/                           — 実行時生成（DB・フラグ・pid 等）

（この README はコードベースから主要ファイルのみ抜粋した構成図です）

---

## 開発・テスト時の注意点

- Paper Trading
  - KABUSYS_ENV=paper_trading を指定すると、本番用 monitoring DB と分離して `PAPER_TRADING_SQLITE_PATH` に記録されます。
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant / partial / never / reject）。

- .env 読み込み
  - .env/.env.local を自動で読み込みます（OS 環境変数が優先）。テスト中に自動読み込みを防ぎたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- OpenAI / 外部 API
  - OpenAI を使用する機能は APIキーが必須です。テストでは該当モジュールの _call_openai_api をモックすることを想定しています。
  - API エラー時は多くの処理がフェイルセーフ（0.0 やスキップ）で継続する設計になっています。

- データベースマイグレーション
  - init_monitoring_db は存在しないテーブルやカラムの作成・追記を行います（簡易マイグレーション処理あり）。
  - 既存 DB へのカラム追加などは起動時に検出して ALTER を実行します（monitoring_db.py の実装参照）。

---

## よくある運用コマンド（まとめ）

- 監視開始:
  python -m kabusys.run_monitoring

- 実行エンジン開始:
  python -m kabusys.run_execution

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

不明点や追加で README に記載したい内容（詳細な環境変数説明、運用手順、CI 設定例など）があれば教えてください。README を拡張して提供します。