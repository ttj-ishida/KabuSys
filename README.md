# KabuSys

日本株自動売買システムのサブモジュール群（ポートフォリオ構築、実行エンジン、監視、AI/NLP、リサーチツールなど）の実装を含むリポジトリ。  
この README はコードベースの主要コンポーネント、セットアップ、実行方法、およびディレクトリ構成を簡潔にまとめたものです。

注意: 実際のブローカー接続や OpenAI API 呼び出しを行う機能が含まれるため、本番運用前に設定・権限・テストを十分に行ってください。

──

目次
- プロジェクト概要
- 機能一覧
- 要件（依存）
- セットアップ手順
- 環境変数（主な設定）
- 使い方（起動コマンド例）
- 停止・フラグ管理
- 開発・デバッグのヒント
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買を目的としたモジュール群です。
- 本リポジトリには、実取引用・ペーパートレード用の ExecutionEngine、監視（Monitoring）機能、ポートフォリオ構築ロジック、リサーチ／ファクター計算、ニュース NLP（OpenAI を用いたセンチメント）などが含まれます。
- 設定は環境変数（.env / .env.local 経由で自動読み込み）で管理され、paper_trading（ペーパー）と live（本番）を分離する設計がされています。

機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading 用 DB に記録
  - リコンシリエーション（再起動時の注文同期）機能
  - リスク管理（RiskManager）やOrderManager を組み合わせた実行基盤
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor をまとめる MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - LINE によるアラート送信（AlertManager）
  - kill flag による ExecutionEngine 停止（KillSwitch）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- ポートフォリオ構築（portfolio）
  - 候補選択、等重/スコア加重の重み計算、リスク調整、ポジションサイジング（単元処理含む）
- リサーチ（research）
  - ファクター（モメンタム/バリュー/ボラティリティ）計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI / ニュース NLP（ai）
  - OpenAI を使ったニュースの銘柄別センチメント算出（score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

要件（主な依存）
- Python 3.9+（型ヒントの Union 表記等を利用）
- duckdb
- psutil
- requests
- streamlit（ダッシュボードを使う場合）
- openai（OpenAI SDK：gpt 系の呼び出しに利用）
- sqlite3（標準ライブラリ）
- その他：logging, pathlib 等（標準ライブラリ）

インストール例（仮想環境推奨）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 依存インストール（例）
   - pip install duckdb psutil requests streamlit openai

セットアップ手順
1. リポジトリルートに .env / .env.local を用意（必要なら .env.example を参考に作成）
   - 自動ロード: デフォルトで .env → .env.local の順で読み込まれます（OS 環境変数は保護）
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
2. 必要なディレクトリを作成
   - data/（DB ファイルや pid / flag 用）
     - data/monitoring.db（監視用 SQLite：デフォルト）
     - data/paper_trading.db（paper_trading 用 SQLite：paper 環境で使用）
     - data/kabusys.duckdb（DuckDB のパス。デフォルト: data/kabusys.duckdb）
3. 環境変数を設定（下記「環境変数」参照）

主な環境変数（Settings で参照されるもの）
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を有効にする場合
- PAPER_FILL_MODE: paper_trading 用の約定モード（instant | partial | never | reject）デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite のパス（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方（コマンド例）
- 監視ループを起動（監視データのポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して monitoring DB に書き込みを行います
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を read-only モードで開くよう推奨されています
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）
- AI / ツールの関数呼び出し（スクリプトから呼ぶ）
  - 例（regime_detector を直接呼ぶ）:
    - python -c "from datetime import date; import duckdb; from kabusys.ai.regime_detector import score_regime; conn=duckdb.connect('data/kabusys.duckdb'); print(score_regime(conn, date(2026,4,01)))"
  - News NLP のスコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - 注意: OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で渡す必要があります

停止・フラグ管理
- 実行エンジン停止:
  - KillSwitch: data/kill.flag にテキストを書き込むことで ExecutionEngine 停止シグナルを送る（KillSwitch は冪等的に書き込み）
  - run_execution / run_monitoring はプロセス内で data/stop_requested.flag の存在を監視し、存在すればループを終了します
- PID / スレッド管理:
  - 実行エンジンは起動時に pid ファイルを利用する（Settings.pid_file_path）
  - SystemMonitor は stale PID を検出するとファイルを削除しリスクログに記録

開発・デバッグのヒント
- .env 自動ロード:
  - .env / .env.local はプロジェクトルート（.git または pyproject.toml があるディレクトリ）で探索され自動読み込みされます
  - テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- ログ設定:
  - 各スクリプトは basicConfig(level=logging.INFO) を使っています。詳細ログが欲しい場合は LOG_LEVEL=DEBUG を環境変数で指定
- プロセス優先度:
  - set_process_priority("high") を実行します。psutil による優先度設定で失敗した場合は警告ログのみで続行します（権限に依存）
- DB マイグレーション:
  - init_monitoring_db() は冪等でテーブル・インデックスを作成します。既存 DB にカラム追加が必要な場合は自動で ALTER TABLE を試みます

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（Settings）
  - run_monitoring.py        — SystemMonitor のポーリングスクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — psutil を使ったプロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — monitoring 用 SQLite レイヤ（init, MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 Execution 関連モジュール…)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

補足（安全上の注意）
- 実口座を使う場合は KABU_API_PASSWORD 等の機密情報の取り扱いに注意してください。
- OpenAI API 呼び出しはコストが発生します。テストではモックやテストキーを用いることを推奨します。
- プロセス優先度変更や CPU affinity 設定は権限に依存し、システムに影響を与える可能性があります。権限・影響を理解してから使用してください。

ライセンス・コントリビュート
- 本 README 内にライセンス情報は含まれていません。適宜 LICENSE ファイルを作成してください。
- コントリビュート方法（PR / issue の流れ）はプロジェクトの方針に従ってください。

──

必要であれば、README に以下を追加できます:
- 具体的な .env.example（必須キーと推奨値）
- テストの実行方法（ユニットテスト / CI）
- よくあるトラブルシューティング（DB が開けない、psutil エラー等）

追加の要望があれば、どの情報を追記するか教えてください。