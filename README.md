KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群をまとめた小規模なフレームワークです。  
主な機能は以下の通りです。

- 実行エンジン（ExecutionEngine）による発注・注文管理・リスク管理
- 監視コンポーネント（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading 用の分離された SQLite DB と検証レポート生成
- DuckDB を用いた時系列データ（prices_daily / raw_financials 等）を使ったファクター計算
- ニュースを LLM（OpenAI）でスコアリングして ai_scores に保存
- 市場レジーム判定（ETF MA + マクロニュースの LLM 評価）
- Streamlit ベースの監視ダッシュボード

特徴
----
- 環境（development / paper_trading / live）に応じた動作分岐
- Paper Trading は本番 DB と完全分離（デフォルト: data/paper_trading.db）
- 監視は本番の monitoring DB を用いる（Environment に依存しない）
- フラグファイル（data/stop_requested.flag / data/kill.flag）でプロセス間制御
- OpenAI API 呼び出しは例外耐性（リトライ・フォールバック）あり
- DuckDB を利用した高速なファクター演算・集計

セットアップ
----------
1. Python を用意（推奨: 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （もし requirements.txt がある場合）pip install -r requirements.txt
4. プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くことで環境変数を自動読み込みします。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（要点）
-------------------
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定モード（instant|partial|never|reject。デフォルト: instant）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_PATH / PID_FILE_PATH: フラグファイル / PID ファイルのパス（デフォルトは data 以下）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

サンプル .env（抜粋）
-------------------
例:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=paper_trading
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

起動・使い方
------------

1) 監視プロセス（Monitoring）
- 監視ループを起動する（ポーリング + DB ログ保存）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（デフォルト 60 秒）。
- 停止方法:
  - data/stop_requested.flag ファイルを作成すると安全にループが終了します（実行中の run_monitoring が検知して終了）。
  - kill.flag は ExecutionEngine を強制停止させるために KillSwitch が書き込むためのフラグです（ExecutionEngine 側で処理）。

2) 実行エンジン（ExecutionEngine）
- 起動:
  - python -m kabusys.run_execution
- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と分離）。
- 停止:
  - data/stop_requested.flag が検知されるとエンジンは停止します。
- PID 管理:
  - 実行時に data/execution.pid（デフォルト）を利用します。不正な PID ファイルは SystemMonitor により検出・削除されます。

3) Paper Trading 検証レポート
- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合: --db data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で指定することも可）
- 出力: 標準出力に稼働率・注文成功率・レイテンシ等のサマリと PASS/FAIL 判定を表示

4) 監視ダッシュボード（Streamlit）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで DB を開き、Positions / Orders / System / Overview タブを表示します。

5) AI 関連（ニュース NLP / レジーム判定）
- ライブラリ関数（Python から呼び出す）:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 事前準備: OPENAI_API_KEY 環境変数か api_key 引数が必要です。
- 動作: raw_news / news_symbols / prices_daily / market_regime / ai_scores 等の DuckDB テーブルを参照・更新します。

注意点 / 動作仕様
-----------------
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込みます。OS 環境変数が優先され、.env.local は上書き読み込みされます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 監視 DB（monitoring）:
  - init_monitoring_db() は冪等でテーブルを作成し、必要に応じて簡単なマイグレーション（カラム追加）を行います。
- ログ・アラート:
  - AlertManager は LINE Push API へ通知します。CHANNEL / USER が未設定の場合は送信をスキップしてログに記録します。クールダウン（デフォルト 30 分）あり。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出します（psutil を利用）。権限不足などで失敗した場合は警告を出してスキップします。
- フラグファイル:
  - data/stop_requested.flag: 手動停止（監視/実行の共通停止フラグ）
  - data/kill.flag: KillSwitch による ExecutionEngine 停止シグナル（リスク条件で書き込まれる）
  - PID ファイルは data/execution.pid（デフォルト）に保存／検査されます

ディレクトリ構成（抜粋）
---------------------
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                 # 環境変数/.env 読み込みと Settings
   ├─ run_monitoring.py         # 監視ループ起動スクリプト
   ├─ run_execution.py          # 実行エンジン起動スクリプト
   ├─ tools/
   │  └─ paper_verification_report.py
   ├─ ai/
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   ├─ monitoring/
   │  ├─ __init__.py
   │  ├─ monitoring_db.py
   │  ├─ system_monitor.py
   │  ├─ trade_monitor.py
   │  ├─ risk_monitor.py
   │  ├─ alert_manager.py
   │  ├─ kill_switch.py
   │  ├─ monitoring_engine.py
   │  └─ streamlit_dashboard.py
   ├─ execution/
   │  ├─ order_manager.py
   │  ├─ reconciler.py
   │  └─ ... (broker / engine / repository 等)
   ├─ portfolio/
   │  ├─ portfolio_builder.py
   │  ├─ position_sizing.py
   │  └─ risk_adjustment.py
   ├─ research/
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   ├─ utils/
   │  └─ process_priority.py
   └─ data/                      # データ・フラグファイル（実行時に生成されることが多い）

開発者向けメモ
--------------
- 単体テストは関数分割と純粋関数設計（portfolio, research 等）に配慮して実装されています。OpenAI や外部 API 呼び出しはモジュール内のラッパー関数を patch してテストしやすく設計されています。
- DuckDB / SQLite を使う関数は接続オブジェクトを受け取る設計なので、テスト用の一時 DB を渡して実行できます。
- .env のパースは細かいケース（quoted values、export プレフィックス、インラインコメント）に対応しています。特殊ケースの挙動は config._parse_env_line を参照してください。

トラブルシューティング
---------------------
- DB が開けない / モジュール起動時に SQLite がロックされる:
  - 監視と実行が同じファイルを開いている場合はロックが生じる可能性があります。paper_trading モードでは paper DB が分離されるため混同に注意してください。
- OpenAI 呼び出しで 429 / 5xx が出る:
  - モジュール内でリトライ実装がありますが、API キーやネットワーク状態、レート制限を確認してください。
- PID ファイルが残ってプロセスが起動しない:
  - data/execution.pid を確認。古い PID が指すプロセスが存在しない場合、SystemMonitor が検出して削除しますが手動で削除しても問題ありません。

ライセンス / コントリビュート
----------------------------
（ここにはプロジェクトのライセンス情報や貢献方法を記載してください）

最後に
------
この README はコードベースの主要な振る舞い・エントリポイント・運用上の注意点をまとめたものです。実運用時は .env を正しく管理し、Paper Trading で十分に検証してから live 環境での運用を行ってください。README に書かれていない詳細はソースコード内の docstring を参照してください。