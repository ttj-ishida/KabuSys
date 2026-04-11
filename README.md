README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なシステムです。本リポジトリには以下の主要コンポーネントが含まれます。

- 発注エンジン（ExecutionEngine）: シグナルに基づく発注、ブローカー連携、リスク管理、再同期（Reconciliation）。
- 監視（Monitoring）: システム稼働状況・注文異常・リスク（ドローダウン等）を監視し、ログ化・アラート・kill フラグ書き込みを実施。
- ポートフォリオ構築（Portfolio）: 候補選定、配分重み、ポジションサイズ算出、セクター制限、レジーム係数等の純粋関数群。
- リサーチ（Research）: DuckDB 上の時系列データからファクターや将来リターン、IC 計算等を行うモジュール。
- AI 統合（AI）: OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・市場レジーム判定の実装（フェイルセーフ＆リトライあり）。
- ダッシュボード: Streamlit ベースの監視ダッシュボード。

特徴
----
- 明確に分離されたモジュール設計（execution / monitoring / research / ai / portfolio）。
- DuckDB と SQLite を併用（時系列分析は DuckDB、監視ログ等は SQLite）。
- Paper Trading モード（KABUSYS_ENV=paper_trading）により発注処理を本番 DB と完全に分離。
- OpenAI API を用いたニュース NLP とレジーム判定をサポート（API 失敗時はフェイルセーフで継続）。
- kill.flag による ExecutionEngine の安全停止、PID ファイルによるプロセス存在確認。
- Streamlit ダッシュボードで監視データを可視化可能。

必須依存パッケージ（主なもの）
--------------------------------
（実行前に以下は必ずインストールしてください）

- python 3.10+
- duckdb
- psutil
- openai
- requests
- streamlit

開発環境では以下のような requirements.txt を用意すると便利です（簡易例）:
- duckdb
- psutil
- openai
- requests
- streamlit

セットアップ手順
----------------
1. リポジトリをクローンし、プロジェクトルートで作業します。
2. 仮想環境を作成して有効化します（例: python -m venv .venv && source .venv/bin/activate）。
3. 依存パッケージをインストールします:
   - pip install -r requirements.txt
   - または個別に pip install duckdb psutil openai requests streamlit
4. 環境変数設定:
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
5. 必須環境変数（代表例）を設定します（.env に記載する想定）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（development | paper_trading | live）
   - 任意: SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, PAPER_FILL_MODE, LOG_LEVEL
6. データベースファイル（data/ 以下）は初回起動時に自動で必要な監視テーブルが作成されます（init_monitoring_db を使用）。

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: 動作環境（development, paper_trading, live）。paper_trading 時は発注処理で MockBroker を使用し、paper SQL ファイルを利用します。
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）。
- DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）。
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）。
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）。不正値（0以下等）の場合デフォルトにフォールバック。
- PID_FILE_PATH: ExecutionEngine が起動時に書き込む PID ファイル（デフォルト: data/execution.pid）。
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）。
- PAPER_FILL_MODE: paper_trading の Mock ブローカーでの約定挙動（instant | partial | never | reject）。

使い方（実行例）
----------------

前提: ルートで PYTHONPATH=src を通すか、パッケージとしてインストールしてください。
例: PYTHONPATH=src python -m kabusys.run_monitoring

1) 監視ループを起動（本番的に 1 回常駐させる）
   - PYTHONPATH=src python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。
   - 注意: monitoring は KABUSYS_ENV にかかわらず sqlite_path を使用します（監視 DB は本番パスを使う設計）。

2) ExecutionEngine を起動（当日のセッションを実行）
   - PYTHONPATH=src python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を指定すると mock ブローカーを使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使います。
   - 起動時に PID ファイルを書き、終了時に削除（挙動は Settings で制御）。

3) Streamlit ダッシュボードで監視結果を閲覧
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - monitoring DB が読み取り専用で開かれます。MonitoringEngine 起動後にデータが表示されます。

4) AI 処理（ニュースセンチメント / レジーム判定）を呼び出す
   - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を引数に取る関数です。
   - 例（簡易的な呼び出し）:
     from pathlib import Path
     import duckdb
     from datetime import date
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, date(2026, 3, 20), api_key="sk-...")

5) その他
   - .env/.env.local は Settings モジュールがプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みします。
   - 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

監視・停止のメカニズム
--------------------
- PID ファイル: ExecutionEngine は起動時に PID を書き込み、SystemMonitor はその PID の存否をチェックしてプロセスが生存しない場合 stale PID として処理します。
- kill.flag: KillSwitch が条件を満たすと kill.flag を書き込みます。ExecutionEngine は起動時およびループ中にこのファイルを検出すると安全に停止します。Settings.kill_flag_clear_on_start により起動時の kill.flag 自動クリアを制御可能。

設計上の注意点 / 動作のヒント
------------------------------
- monitoring の init_monitoring_db() は冪等にテーブルを作成します。既存 DB に対する軽微なマイグレーション（例: dashboard.peak_value の追加）も含まれます。
- Paper trading は本番 DB と分離するため、KABUSYS_ENV=paper_trading のときは settings.paper_sqlite_path が利用されます。DuckDB は共通で使う想定の箇所がありますので運用上の注意が必要です（duckdb 内の prices_daily 等はリサーチ機能が参照します）。
- OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証を行いますが、APIキーが未設定だと例外が発生します。AI 機能を使う場合は OPENAI_API_KEY をセットしてください。
- プロセス優先度設定（set_process_priority）は psutil を使い、プラットフォーム差を吸収しますが、権限がない場合は警告が出てスキップされます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
  - パッケージ情報（__version__ 等）
- config.py
  - .env 自動読み込み、Settings クラス（環境変数管理）
- run_monitoring.py
  - SystemMonitor をポーリングで回す起動スクリプト（MONITOR_POLL_INTERVAL で間隔制御）
- run_execution.py
  - ExecutionEngine を起動するスクリプト（paper_trading モード対応）
- monitoring/
  - monitoring_db.py: SQLite テーブルの初期化および MonitoringDB ラッパー（永続化 API）
  - system_monitor.py: CPU/MEM/DISK/データ鮮度/プロセス生存を確認
  - trade_monitor.py: 滞留注文・約定異常を検出
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - kill_switch.py: kill.flag 制御
  - alert_manager.py: LINE へのプッシュ通知（クールダウン管理）
  - monitoring_engine.py: 各 monitor を束ねるループ
  - streamlit_dashboard.py: Streamlit ベースの監視 UI
- execution/
  - execution_engine.py: Signal Queue 型の発注エンジン（メインロジック）
  - order_manager.py: 発注状態遷移・ブローカー連携のラッパー
  - order_repository.py, order_record.py, broker_api.py, reconciler.py, risk_manager.py, ...（発注周りの実装）
- portfolio/
  - portfolio_builder.py: 候補選定・スコアソート
  - position_sizing.py: 発注株数計算（lot 単位丸め・リスク制限・スケーリング）
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: モメンタム/ボラティリティ/バリュー等の計算
  - feature_exploration.py: 将来リターン / IC / 統計サマリー
- ai/
  - news_nlp.py: ニュース記事の LLM によるセンチメント評価と ai_scores への書込み
  - regime_detector.py: ETF MA とマクロ NLP を合成したレジーム判定
- utils/
  - process_priority.py: プロセス優先度 / CPU affinity のユーティリティ
- research, data, etc.
  - data 側は DuckDB のテーブル（prices_daily, raw_financials, raw_news）を前提とする処理が多いです。

ライセンス / 貢献
-----------------
本 README はコードベースの説明のための参考ドキュメントです。実運用にあたっては必ずコード全体をレビューし、環境変数や DB パス、API キーの管理に注意してください。貢献や改善提案は PR または Issue を通じてお願いします。

付録: よく使うコマンド例
---------------------
- 開発実行（環境変数を .env で読み込む前提）:
  PYTHONPATH=src python -m kabusys.run_monitoring
  PYTHONPATH=src python -m kabusys.run_execution

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- DuckDB に対する AI 処理の手動実行（例）:
  PYTHONPATH=src python -c "import duckdb, datetime; from kabusys.ai.news_nlp import score_news; c=duckdb.connect('data/kabusys.duckdb'); print(score_news(c, datetime.date(2026,3,20), api_key='sk-...'))"

必要に応じて、この README をプロジェクト固有の運用手順・CI 設定・デプロイ手順に合わせて補強してください。