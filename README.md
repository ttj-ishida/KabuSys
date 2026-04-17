# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。銘柄選定、ポジションサイジング、発注管理、監視、AI を用いたニュースセンチメントや市場レジーム判定、Paper Trading 検証ツール等を含みます。本リポジトリ内のスクリプトを組み合わせて運用・検証ができます。

以下はこのコードベースの概要、機能、セットアップ、使い方、ディレクトリ構成のドキュメントです。

注意: ここでのパス例はパッケージがソースツリー（例: src/）のまま実行されることを想定しています。パッケージインストール後は python -m kabusys.<module> でも実行できます。

---

## プロジェクト概要

- 自動売買システムのコアロジック（発注管理・再同期間合・リスク管理等）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ）機能
- 監視（システム稼働、注文滞留、ドローダウンなど）とアラート送信（LINE）
- DuckDB / SQLite を使ったデータ処理・集計機能（ファクター計算、リサーチ）
- OpenAI を用いたニュースセンチメント（news_nlp）／市場レジーム判定（regime_detector）
- Paper Trading 用 DB と検証レポート出力ツール

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し本番 DB と分離
- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL により間隔指定可）
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ねて定期実行、KillSwitch 評価、AlertManager 通知
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス PID、データ鮮度を監視
  - TradeMonitor: 注文滞留、約定価格異常を検出
  - RiskMonitor: ドローダウン・ポジション上限の監視（ダッシュボード更新・リスクログ）
  - AlertManager: LINE push 通知（クールダウン管理）
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
- データベース永続性（SQLite）
  - monitoring_db.py: 監視用テーブル群の初期化・読み書き（system_status, trade_logs, positions, risk_logs, dashboard）
- 発注関連
  - order_manager.py: Order の作成・状態遷移管理（Duplicate 判定等）
  - reconciler.py: 起動時のブローカー照合とポジション差分検出（自動復旧）
  - BrokerFactory / ExecutionEngine 等（実装は別ファイル）
- ポートフォリオ構成
  - portfolio_builder.py: 候補選定、等配分・スコア加重
  - position_sizing.py: 株数算出（lot 単位丸め、risk_based 等）
  - risk_adjustment.py: セクター上限・レジーム乗数
- リサーチ（DuckDB を用いたファクター計算）
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算
  - research.feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI 関連
  - ai.news_nlp: raw_news から OpenAI API で銘柄別センチメントを算出し ai_scores に保存
  - ai.regime_detector: ETF(1321) の MA200 とマクロニュースの LLM センチメントを合成して日次レジーム判定
- ツール
  - tools.paper_verification_report.py: Paper Trading DB（data/paper_trading.db）から検証レポートを作成
- ユーティリティ
  - utils.process_priority: プロセス優先度 / CPU affinity の設定ユーティリティ
- 設定管理
  - config.py: 環境変数 / .env 自動読み込み、Settings クラス（各種パスや閾値・フラグなど）

---

## 前提・必須パッケージ

- Python 3.9+（typing/構文の使用を想定）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- インストール例（仮想環境内で）:
  - pip install duckdb psutil requests openai streamlit

（実プロジェクトでは requirements.txt を用意することを推奨します）

---

## 環境変数（主要）

- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant / partial / never / reject） デフォルト: instant
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用 flag パス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

config.py はプロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順（ローカルで簡単に動かす場合）

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. .env をプロジェクトルートに作成（例は下記参照）
5. データディレクトリを作成
   - mkdir -p data
6. （任意）DuckDB / SQLite DB の初期化は run_monitoring/run_execution が自動で行います（init_monitoring_db を呼ぶ）

例 .env（最小）
- JQUANTS_REFRESH_TOKEN=your_token
- KABU_API_PASSWORD=your_kabu_password
- OPENAI_API_KEY=sk-...
- KABUSYS_ENV=development
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
（実際には .env.example を参照してください）

---

## 実行方法（代表例）

- 監視ループ起動（SystemMonitor を定期実行）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 実行（ソースツリー直下から）
    - python -m kabusys.run_monitoring
    - または python src/kabusys/run_monitoring.py
  - 特記事項:
    - run_monitoring はプロセス優先度を high に設定し、Settings.sqlite_path を使って monitoring DB を初期化します
    - 停止は data/stop_requested.flag ファイルを作成するとポーリングループが検知して終了します

- ExecutionEngine 起動（注文発行エンジン）
  - 実行:
    - python -m kabusys.run_execution
    - または python src/kabusys/run_execution.py
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag があると起動せずに終了します
    - 実行中に KillSwitch（data/kill.flag）を検出するとエンジンを停止するフローが組み込まれています

- Streamlit ダッシュボード（監視 UI）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で監視 DB を開き、概要・ポジション・注文・システム状態を表示します

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 関連（スクリプト化されている関数群）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して、対象日のニュースウィンドウをスコア化し ai_scores テーブルへ書き込み
    - OPENAI_API_KEY が必要
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 MA200 とマクロニュースを LLM で評価して market_regime に書き込む

---

## 停止 / フラグ制御

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py がポーリング中にこのファイルの存在を検知すると安全に終了します
- data/kill.flag
  - KillSwitch により作成されると ExecutionEngine に停止シグナルを送る用途（Execution 側で path を監視）
  - KillSwitch.clear() で削除可能（Execution 起動時にオプションでクリアする設定もあります）

---

## ディレクトリ構成（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env の読み込みと Settings 定義
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py              — SQLite テーブル定義・監視ログ操作
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
    - system_monitor.py             — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py              — 注文滞留・約定異常検出
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - kill_switch.py                — kill.flag 管理
    - alert_manager.py              — LINE Push 通知（クールダウン管理）
    - streamlit_dashboard.py        — Streamlit ダッシュボード
  - execution/
    - order_manager.py              — 発注 API と DB の間の外向き API
    - reconciler.py                 — 再起動時のブローカー照合・ポジション差分検出
    - (その他: broker_factory, execution_engine, order_repository など)
  - portfolio/
    - portfolio_builder.py          — 候補選定と重み計算
    - position_sizing.py            — 株数算出・制約処理
    - risk_adjustment.py            — セクター制限・レジーム乗数
  - research/
    - factor_research.py            — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py        — 将来リターン / IC / 統計
  - data/ (実行時に生成される想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - execution.pid, kill.flag, stop_requested.flag, etc.
  - utils/
    - process_priority.py           — プロセス優先度・CPU affinity ユーティリティ

---

## 実装上のポイント / 注意事項

- Settings（config.py）はプロジェクトルートの .env / .env.local を自動読込します。OS 環境変数を上書きしたくない場合は .env.local を用いるか KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を指定できます（デフォルト 60 秒）。0 以下の値は無効扱いでデフォルトにフォールバックします。
- 監視用 DB 初期化は init_monitoring_db により冪等に実行されます（既存スキーマへのマイグレーションも若干対応）。
- Paper Trading は本番 DB と完全分離する設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使う機能は外部 API 呼び出しが発生するため API キーの管理・料金に注意してください。API 呼び出し失敗時はフォールバックやリトライの実装があり、致命的に停止しない設計です。
- process_priority.set_process_priority() によりスクリプト起動時にプロセス優先度を「high」に設定しようとします。権限不足で失敗する場合はログに警告を出して続行します。

---

## よく使うコマンドまとめ

- 監視ループ開始:
  - python -m kabusys.run_monitoring
- 実行エンジン開始:
  - python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 停止（安全停止フラグ作成）:
  - touch data/stop_requested.flag
  - （KillSwitch により ExecutionEngine 停止を意図する場合は data/kill.flag を作成）

---

必要に応じて README にインストール手順（requirements.txt の追加）、設定ファイルのテンプレート（.env.example）、CI/デプロイ手順、ExecutionEngine の詳細設計（pid / graceful shutdown / logging）などを追加することを推奨します。追加したい内容があれば教えてください。