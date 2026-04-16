KabuSys — 日本株自動売買システム（README）
=================================================

概要
----
KabuSys は日本株向けの自動売買・バックオフィス・監視・リサーチ機能を備えたPythonベースのプロジェクトです。本リポジトリは以下の主要領域を含みます。

- 実行エンジン（ExecutionEngine）: ブローカーとやり取りして発注・注文管理・リスク管理を行う
- 監視（Monitoring）: プロセス・システム状態、注文滞留、ドローダウン等を定期監視しログ／アラートを生成
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ計算、セクター制限などの純粋関数群
- リサーチ（Research）: DuckDB を用いたファクター計算・特徴量解析
- AI / NLP モジュール: ニュースのセンチメント評価や市場レジーム判定（OpenAI 利用）
- ツール群: Paper Trading 検証レポート生成、Streamlit ダッシュボード 等

主な機能
---------
- 定期ポーリングによるシステム監視（CPU / メモリ / ディスク / データ鮮度）
- 注文滞留・約定価格異常検出、ドローダウン・ポジション上限の自動検出とログ記録
- Kill switch による安全停止フラグの書き込み（ExecutionEngine 停止トリガ）
- ExecutionEngine の起動・停止、起動時のリコンシリエーション（ブローカーと注文／ポジション照合）
- Paper Trading モード（本番 DB と分離した専用 SQLite に記録、MockBroker を使用）
- DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントとレジーム検出（フェイルセーフ実装）
- Streamlit ダッシュボードでの監視データ可視化
- Paper Trading 検証レポート生成（稼働率・注文成功率・レイテンシ等の指標）

セットアップ
-----------
1. Python 環境
   - Python 3.9+ を推奨（プロジェクトが依存するパッケージに合わせて調整してください）

2. 依存パッケージ（例）
   - pip install duckdb psutil requests openai streamlit
   - 実運用では requirements.txt を用意して pip install -r requirements.txt を推奨

3. プロジェクトルート
   - このリポジトリをチェックアウト後、プロジェクトルート（pyproject.toml または .git がある場所）が自動で検出されます。

4. データディレクトリ作成
   - data ディレクトリを作成（デフォルトの DB / PID / フラグファイルはここを使用します）
     mkdir -p data

5. 環境変数 / .env
   - 自動で .env / .env.local を読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須: 以下の環境変数を設定してください（用途に応じて .env に記載）
     - JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必要な場合）
     - KABU_API_PASSWORD: kabuステーション API パスワード（本番接続時）
     - OPENAI_API_KEY: OpenAI API を利用する場合に必須（news_nlp / regime_detector）
   - 任意 / デフォルト値:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視ログ用）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時専用）
     - PID_FILE_PATH, KILL_FLAG_PATH 等（Defaults: data/execution.pid, data/kill.flag）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
   - .env のパースはシェル風（export やクォート等の一般的な記法に対応）です。

初期化
-----
- 監視 DB テーブルは run_monitoring または run_execution 起動時に自動作成（init_monitoring_db）されます。
- DuckDB のテーブル（prices_daily / raw_financials 等）は別途 ETL で投入してください（本リポジトリにはデータ投入用コードの一部が含まれますが、外部データ準備は利用者側で行う必要があります）。

使い方（主なコマンド）
--------------------

1. 監視プロセス起動（Monitoring）
   - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
   - 実行例:
     - python -m kabusys.run_monitoring
   - 停止:
     - プロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了します。

2. 実行エンジン起動（ExecutionEngine）
   - KABUSYS_ENV によって実行挙動が変わります。
     - paper_trading: MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。本番 DB と分離。
     - live / development: 設定に応じて本番 API に接続
   - 実行例:
     - python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成すると実行中のエンジンへ停止指示が送られます。
     - KillSwitch（監視ロジック）により data/kill.flag が書かれると ExecutionEngine は安全に停止される設計です。

3. Paper Trading 検証レポート
   - CSV/DB から期間を指定して検証レポートを標準出力に生成します。
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - 指定 DB を使う場合: --db path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

4. Streamlit 監視ダッシュボード
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で接続し、Positions / Orders / System / Overview を参照できます。

5. AI / NLP 機能
   - OpenAI API キー（OPENAI_API_KEY）が必要です。news_nlp.score_news や regime_detector.score_regime が主なエントリポイントです。
   - 注意: API 呼び出しはレート制限・エラーに対してリトライやフェイルセーフ処理が実装されていますが、API キー未設定時は ValueError を投げます。

プロセス制御とフラグ
-------------------
- 停止フラグ:
  - data/stop_requested.flag : run_monitoring / run_execution が監視する停止フラグ（ファイル存在で停止）
- Kill フラグ:
  - data/kill.flag : KillSwitch が作成することで ExecutionEngine 停止をトリガ
- PID:
  - data/execution.pid : ExecutionEngine の PID ファイル（process check に使用）
- これらのファイルは data フォルダ下に置かれるのがデフォルトです。パスは Settings 経由で上書き可能（PID_FILE_PATH / KILL_FLAG_PATH）。

設定項目（Settings で参照される主な環境変数）
--------------------------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート送信用（AlertManager）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視ログ SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py — 環境変数の読み込み・Settings クラス
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — 市場レジーム判定（OpenAI）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（init + CRUD）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード（起動スクリプト）
- portfolio/
  - portfolio_builder.py — 候補選定・スコア順ソート
  - risk_adjustment.py — セクター上限・レジーム乗数
  - position_sizing.py — 発注株数計算（単元丸め、リスクベース等）
- research/
  - factor_research.py — モメンタム・ボラ・バリュー等の計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- execution/
  - order_manager.py, reconciler.py, ... — 発注管理・リコンシリエーション等
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring_db / その他のモジュール群（必要に応じて参照）

運用上の注意
-----------
- 実行時のプロセス優先度設定はプラットフォーム依存および権限制限を受けます（psutil を使用）。権限不足時は警告を出してスキップします。
- OpenAI を用いる箇所は外部 API 呼び出しを伴うため、API キー・課金やレート制限に注意してください。モジュール側でリトライやフェイルセーフ（失敗時に 0.0 等でフォールバック）が実装されていますが、運用ポリシーは利用者側で策定してください。
- Paper Trading を使うときは必ず KABUSYS_ENV=paper_trading にして、実データベースと分離された PAPER_TRADING_SQLITE_PATH を利用してください。
- monitoring_db のマイグレーション（新カラム追加等）は起動時に自動的に行われますが、バックアップを取ってから運用することを推奨します。

トラブルシューティング
----------------------
- DB が開けない / ファイルが見つからない:
  - data ディレクトリの存在とパーミッションを確認し、設定されたパス（DUCKDB_PATH / SQLITE_PATH）を確認してください。
- OpenAI 関連で ValueError が出る:
  - OPENAI_API_KEY が未設定です。環境変数または引数で API キーを渡してください。
- プロセス優先度設定失敗や CPU affinity が設定されない:
  - 権限不足か OS 非対応の可能性があります（ログに警告が出ます）。
- 停止してもプロセスが残る:
  - data/stop_requested.flag と data/kill.flag の存在・内容を確認し、必要なら pid を確認して手動で終了してください（最終手段として kill）。

補足
----
- 本 README はコードベース（src/kabusys/*.py）を参照して要点をまとめたものです。各モジュールの詳細な使用方法や引数仕様は該当ファイルの docstring / コメントを参照してください。
- 実運用環境では適切な権限管理、ログ収集、監査、バックアップ方針を整備してください。

以上。必要であれば、README に含めるサンプル .env.example、より詳しい起動手順（systemd ユニット例や Dockerfile、CI 設定など）を追記できます。どの情報を追加しますか？