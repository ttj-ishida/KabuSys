KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのプロジェクトです。
主な機能は次のとおりです。

- 発注・実行エンジン（ExecutionEngine） — 実口座 / ペーパートレード対応
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ機能（ファクター計算、前方リターン、IC 計算、統計サマリー）
- AI モジュール（ニュース NLP による銘柄スコアリング、レジーム判定）
- 運用サポートツール（.env ウィザード、設定検証、Paper Trading レポート）
- DuckDB / SQLite を用いたデータ管理とログ

ユースケースの例:
- ローカル開発（KABUSYS_ENV=development）でのシミュレーション・研究
- ペーパートレード（KABUSYS_ENV=paper_trading）での動作検証（本番 DB と分離）
- 本番運用（KABUSYS_ENV=live）

主な機能一覧
-------------
- Execution
  - BrokerClientFactory によるブローカ抽象化（paper_trading 時は MockBrokerClient を使用）
  - RiskManager / OrderManager / Reconciler を組み合わせた ExecutionEngine
  - 起動中の停止フラグ (data/stop_requested.flag / data/kill.flag) による安全停止

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス・データ鮮度監視
  - TradeMonitor: 発注ログの監視（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン / ポジション上限監視、リスクイベント記録
  - MonitoringEngine: 各モニタを束ね、KillSwitch/AlertManager と連携

- Portfolio
  - 候補選定（score / rank ベース）
  - 等金額・スコア加重配分
  - ポジションサイズ計算（リスクベース、単元株丸め、aggregate cap）
  - セクター上限・レジーム乗数

- Research / Tools
  - ファクター計算 (momentum, volatility, value)
  - 特徴量探索（forward returns / IC / summary）
  - Paper Trading 検証レポート生成スクリプト

- AI
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメント集約と ai_scores への書込み
  - regime_detector: ETF (1321) の ma200 とマクロ記事の LLM センチメントを合成して daily market regime を判定

セットアップ手順
----------------
1. 必要環境
   - Python 3.9+
   - 推奨: 仮想環境（venv / poetry / pipenv 等）

2. 依存ライブラリ（代表）
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   - その他（requirements.txt がある場合はそちらを使用してください）

   例:
   - pip install -r requirements.txt
   - あるいは最低限:
     - pip install duckdb psutil openai

3. .env の作成（対話式ウィザード推奨）
   - 下記コマンドでウィザードを実行すると .env を生成／更新できます:
     - python -m kabusys.config_setup
   - ウィザード実行後は設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

4. 環境変数の主なキー（抜粋・デフォルト）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート用（任意）
   - 監視用:
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒, デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などは Settings クラスで参照

5. データディレクトリ
   - data/ 以下に DB・フラグファイル・pid などを保存します。必要であれば事前に作成してください（多くの起動処理で自動作成されます）。

使い方
------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 本番 / ペーパー共通起動モジュール:
    - python -m kabusys.run_execution
  - 注:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient による発注が行われます。
    - 起動前に data/kill.flag が存在すると起動を停止します（Kill Switch）。

- Monitoring 起動（常駐）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path を使用して監視ログを記録します（KABUSYS_ENV に依らず）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ライブラリ呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection（duckdb.connect()）
    - target_date: date オブジェクト
    - api_key: 省略時は環境変数 OPENAI_API_KEY を使用
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に DuckDB 接続と API キーを渡します

- ログ
  - ログは logs/<app_name>.log に日次ローテーションで保存されます（logs/ ディレクトリが作成できない場合はコンソール出力のみ）。
  - 起動スクリプトは共通の logging 設定ユーティリティを使用します: kabusys.utils.logging_setup.setup_logging

運用上の注意
------------
- Kill Switch / Stop Flag
  - リスク条件で自動的に data/kill.flag が書き込まれると ExecutionEngine は停止されます（kill.flag は手動削除か設定による自動クリア）。
  - data/stop_requested.flag は起動中の run_* スクリプトで検出されるとループを終了します（外部からの安全停止シグナルとして使用）。

- DB 分離
  - ペーパートレード時は paper_trading 用の SQLite を使用して本番データと完全に分離します。

- OpenAI API
  - news_nlp・regime_detector は OpenAI を利用します。API キーは OPENAI_API_KEY 環境変数または関数引数で指定してください。
  - API 呼び出しはリトライ・フォールバックロジックを含んでおり、失敗時は安全にフォールバックする設計です（例: macro_sentiment=0.0）。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/設定管理（.env 自動ロード処理含む）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュース NLP スコアリング
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (想定)
- execution/
  - execution_engine.py    — 実行エンジン本体
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - risk_manager.py
  - reconciler.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- data/
  - pipeline.py, stats.py (想定)
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

サンプルコマンドまとめ
--------------------
- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

ライセンス / 貢献
----------------
本 README はコードベースの説明用です。実際の公開リポジトリではライセンスファイル（LICENSE）やコントリビューションガイド（CONTRIBUTING.md）を追加してください。

補足
----
- 実運用時は KABUSYS_ENV=live の設定・API キー・LINE 通知先などを慎重に管理してください。
- 本 README はリポジトリ内のモジュール実装に基づくサマリです。詳細な API 使用方法は各モジュールの docstring を参照してください。