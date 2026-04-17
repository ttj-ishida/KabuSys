KabuSys
=======

日本株自動売買システムの小規模モノリポジトリ（ライブラリ + 実行スクリプト群）。
本 README はコードベース（src/kabusys 以下）を対象とした概要、機能、セットアップ、
および主要な使い方の手引きです。

プロジェクト概要
----------------
KabuSys は以下の主要機能を持つ自動売買システムのコンポーネント群です。

- Execution: ブローカー API 経由の注文管理・発注エンジン（ExecutionEngine / OrderManager 等）
- Monitoring: システム／注文／リスクの常時監視（SystemMonitor / TradeMonitor / RiskMonitor 等）、アラート（LINE）や KillSwitch による安全停止
- Portfolio: 銘柄選定・重み計算・ポジションサイズ算出（等重・スコア重み・リスクベース）
- Research: ファクター計算、将来リターン/IC 計算などの研究用モジュール（DuckDB 経由）
- AI: ニュースの NLP（OpenAI）を使ったセンチメントスコア付与、レジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit ベース監視ダッシュボード など
- Utilities: 設定管理（.env 読み込み）やプロセス優先度ユーティリティ 等

主な設計方針:
- データアクセスは DuckDB（リサーチ系）と SQLite（監視・注文ログ）を使用
- Paper Trading モードは本番 DB と分離（data/paper_trading.db）
- 外部 API（OpenAI / ブローカー / LINE）呼び出しは明示的に制御・フェイルセーフ化

機能一覧
--------
- SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度の監視とログ化
- TradeMonitor: 滞留注文（stale）や約定価格の異常検出
- RiskMonitor: ドローダウン・ポジション上限監視、リスクログ記録
- KillSwitch: しきい値超過時に data/kill.flag を書き込み、Execution の停止を誘発
- AlertManager: LINE Messaging API へプッシュ通知（クールダウン管理）
- MonitoringEngine: 複数モニタの周期実行とアラート連携
- ExecutionEngine / OrderManager / Reconciler: 発注・状態同期・リコンシリエーション
- Portfolio module: 銘柄選定・重み付け・ポジションサイズ計算（純粋関数）
- Research module: momentum / volatility / value ファクター、将来リターン、IC、統計サマリ
- AI module: news_nlp（OpenAI でニュースをまとめて銘柄別スコア化）、regime_detector（MA + LLM で市場レジーム判定）
- Tools:
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - streamlit_dashboard: streamlit で監視ダッシュボード表示

セットアップ手順
--------------
前提:
- Python 3.9+ を想定（利用するパッケージに合わせて適宜調整してください）
- system には duckdb, sqlite3 が利用可能
- optional: OpenAI API を使う場合は API キーが必要

1. リポジトリをクローン / ソース配置
   - ソースは src/kabusys 以下に配置されています。
   - プロジェクトルートに data ディレクトリを作成してください（例: data/monitoring.db などを格納）。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 代表的な依存 (例):
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそれを利用してください）

4. 環境変数 / .env
   - 設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV: 起動環境（development | paper_trading | live）デフォルト: development
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. data ディレクトリの作成
   - 実行前に data ディレクトリを作成しておくと便利です:
     mkdir -p data

使い方
------
以下は主な実行方法・利用例です。プロダクション環境では systemd や supervisord 等でプロセス管理することを想定しています。

1. 監視プロセスの起動（run_monitoring.py）
   - 監視ループを起動します（Monitoring -> SQLite/duckdb 接続、SystemMonitor を定期実行）。
   - 実行:
     python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（正の整数、デフォルト 60）
   - 停止:
     - プロジェクトルート/data/stop_requested.flag を作成するとループは検知して終了します（run_monitoring/run_execution と共通）。

2. Execution エンジンの起動（run_execution.py）
   - ブローカークライアントを生成して ExecutionEngine を起動します。
   - 実行:
     python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合:
     - MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます。
   - 停止:
     - data/stop_requested.flag を置く（または kill.flag を監視ロジックで利用）ことで Engine に停止シグナルを送る実装になっています。

3. Paper Trading 検証レポート
   - ツール: kabusys.tools.paper_verification_report
   - 実行例:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   - 出力: 稼働率、注文成功率、送信率、レイテンシ等の集計と PASS/FAIL 判定

4. Streamlit 監視ダッシュボード
   - 起動方法:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only 接続で監視 DB を表示します（positions / recent orders / latest system status / risk logs）。

5. AI 機能
   - news_nlp.score_news(conn, target_date, api_key=None)
     - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定
     - raw_news / news_symbols を集約して ai_scores テーブルへ書き込み
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF(1321) MA200 乖離とマクロセンチメントを合成して market_regime に書き込み
   - どちらも API 呼び出しはリトライやフォールバック処理を含み、失敗時は安全に継続する設計

設定（Settings）
----------------
config.py の Settings クラスで多くの設定を環境変数から読み込みます。主なプロパティ:

- env / is_live / is_paper / is_dev — KABUSYS_ENV（development|paper_trading|live）
- sqlite_path / paper_sqlite_path / duckdb_path — DB パス
- pid_file_path / kill_flag_path / kill_flag_clear_on_start
- paper_fill_mode — Paper Trading 時の fill 挙動（instant|partial|never|reject）
- CPU / memory / disk 閾値（CPU_THRESHOLD_PCT 等）
- ログレベル（LOG_LEVEL）

重要: Settings._load_env_file によりプロジェクトルートの .env, .env.local が自動で読み込まれます（OS 環境変数を優先）。テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

データベースとマイグレーション
----------------------------
- monitoring_db.init_monitoring_db(conn) は必要なテーブルを冪等に作成し、簡単なマイグレーション（列追加）も行います。run_monitoring/run_execution 実行時に自動で呼ばれます。
- DuckDB は prices_daily / raw_financials / raw_news 等のテーブルを用いてリサーチ・AI 処理を行います。DuckDB ファイルは Settings.duckdb_path で指定します。

注意点 / 運用上のポイント
-------------------------
- process priority / CPU affinity の設定には psutil を使用しています。権限やプラットフォームにより実行できない場合は警告を出してスキップします。
- MONITOR_POLL_INTERVAL は環境変数で上書きできます（整数、1 以上推奨）。
- stop_requested.flag（data/stop_requested.flag）があると run_* スクリプトは起動・ループ中に検知して安全に終了します。
- KillSwitch はリスク条件（ドローダウン等）で data/kill.flag を作成し、Execution 側がこれを検知して安全にシャットダウンできるよう設計されています。
- OpenAI 呼び出しは利用回数・レートリミットに注意し、API キーは安全に管理してください。

ディレクトリ構成
----------------
src/kabusys の主なファイル・パッケージ（抜粋）:

- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py  — ExecutionEngine 起動スクリプト
- config.py         — 環境変数 / Settings 管理
- __init__.py       — パッケージメタ情報

パッケージ:
- kabusys/monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- kabusys/execution/
  - order_manager.py
  - reconciler.py
  - （Broker API / ExecutionEngine 等が含まれます）
- kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- kabusys/research/
  - factor_research.py
  - feature_exploration.py
- kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- kabusys/tools/
  - paper_verification_report.py
- kabusys/utils/
  - process_priority.py

（上記は主要ファイルの抜粋です。完全なファイル一覧は src/kabusys 以下を参照してください）

追加情報 / トラブルシューティング
---------------------------------
- SQLite / DuckDB のパスに関する権限・ディレクトリ存在確認を行ってください。data フォルダが存在しないとファイル作成に失敗することがあります。
- LINE 通知が機能しない場合は token / user_id の設定とネットワーク接続（API エンドポイント）を確認してください。
- OpenAI 呼び出しのロギングは警告や例外の詳細を出力します。API キーが未設定だと AI 関連関数は ValueError を投げます（呼び出し側で捕捉してください）。

ライセンス / 貢献
-----------------
本リポジトリのライセンス情報やコントリビュート手順はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合は管理者へ問い合わせてください）。

最後に
------
この README はコード中のドキュメント文字列および設計コメントに基づいて作成しています。運用前に .env の設定、データディレクトリ、DB の初期化と外部 API キーの確認を必ず行ってください。必要であれば起動用 systemd ユニットや supervisord の設定ファイルも用意してください。