README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ用ライブラリ兼実行フレームワークです。本リポジトリには以下の主要機能を含みます。

- 発注・ExecutionEngine（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ）
- ポートフォリオ構築（銘柄選定・ウェイト計算・ポジションサイズ）
- リサーチ用ファクタ計算（モメンタム・バリュー・ボラティリティ等）
- AI を用いたニュースセンチメント（OpenAI）・レジーム判定
- ユーティリティ（ログ設定・プロセス優先度設定等）
- ペーパートレード検証レポート生成ツール

この README はコードベース（src/kabusys 以下）に基づく運用手順・使い方をまとめたものです。

主な機能一覧
--------------
- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動（KABUSYS_ENV により本番/ペーパーを切替）
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングループを起動
- 設定支援
  - python -m kabusys.config_setup: .env の対話式ウィザードで生成/更新
  - python -m kabusys.validate_config: .env や config/*.yaml の検証 CLI
- 監視 / 安全装置
  - MonitoringEngine（system/trade/risk の定期チェック）
  - KillSwitch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を止める）
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスクに応じたレジーム乗数やセクターキャップ適用、発注株数算出など
- リサーチ
  - DuckDB を使ったファクター計算（momentum, value, volatility）や特徴量解析ユーティリティ
- AI モジュール
  - kabusys.ai.news_nlp: ニュースを OpenAI でスコアリングして ai_scores に書込む
  - kabusys.ai.regime_detector: MA とマクロニュースを組み合わせて market_regime を算出
- ツール
  - python -m kabusys.tools.paper_verification_report: ペーパートレード DB から検証レポートを出力

セットアップ手順
----------------
前提: Python 3.9+（ソースは型アノテーション等を使用）

1. リポジトリをクローン／配置
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出します。

2. 依存パッケージをインストール
   - requirements.txt があればそれを使ってください（無ければ最低限以下をインストール）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config/*.yaml の厳密チェックを行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要な環境変数（ウィザードにも出ます）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - KILL_FLAG_CLEAR_ON_START (0|1) — デフォルト: 0
     - OPENAI_API_KEY（AI 機能を利用する場合）
   - .env を手動で編集する場合は config_setup.py の出力フォーマットを参照してください。

4. 設定検証（起動前の推奨チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります。

5. ログディレクトリ
   - デフォルトで logs/ に日次ローテートログが作られます（LOG_DIR で変更可能）。

基本的な使い方
----------------

1. ExecutionEngine を起動（本番 or ペーパートレード）
   - KABUSYS_ENV によって動作モード切替:
     - paper_trading: MockBrokerClient を使用し data/paper_trading.db を使用（本番 DB と完全分離）
     - live: 実ブローカークライアントを使用
   - 起動:
     - python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成するとスレッドが安全に停止します
     - リスク条件で停止させるには監視側が data/kill.flag を書き込みます（KillSwitch）

2. Monitoring を起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
   - 監視は Settings.sqlite_path（monitoring DB）を使用して永続化します（監視は環境にかかわらず本番 sqlite_path を使用）

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

4. AI を使った処理
   - OPENAI_API_KEY を環境変数に設定するか、該当関数に api_key を渡す
   - ニューススコアリング（コード経由で呼び出し）
     - kabusys.ai.score_news(conn, target_date, api_key=None)
   - レジーム判定
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意: AI 呼び出しはネットワーク/API エラーに対してリトライやフェイルセーフ処理を実装していますが、API キーは必須です。

運用上のフラグ/ファイル
-----------------------
- data/stop_requested.flag:
  - run_monitoring / run_execution のループを停止させるためにチェックされます（プロセス側で確認）
- data/kill.flag:
  - KillSwitch が書き込み、ExecutionEngine に停止を促す（存在すれば起動時に確認して適切に動作）
- data/execution.pid:
  - ExecutionEngine の PID 保存先（Settings.pid_file_path で指定可能）
- DB:
  - DuckDB: data/kabusys.duckdb（デフォルト）
  - Monitoring SQLite: data/monitoring.db（デフォルト）
  - Paper-trading SQLite: data/paper_trading.db（デフォルト）

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- stdout に StreamHandler、ファイルに日次ローテート（logs/<app_name>.log）を出力します。
- LOG_DIR 環境変数や引数でログ先を変更可能。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主な構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数と Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースを OpenAI でスコアリング
    - regime_detector.py      — レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite のスキーマと永続化クラス
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （省略: 注文滞留などの監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - alert_manager.py       — （省略: 通知機能）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動・セッション管理）
    - order_manager.py       — 注文マネージャ
    - order_repository.py    — 注文の永続化
    - broker_factory.py      — ブローカークライアントのファクトリ（Mock含む）
    - risk_manager.py        — 発注前チェック（rate limit / drawdown 等）
    - reconciler.py          — 注文差分同期
  - portfolio/
    - portfolio_builder.py   — 候補選定・ウェイト計算
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
    - __init__.py

注意事項 / 運用上のヒント
------------------------
- KABUSYS_ENV を "live" に設定する前に、必ず validate_config で設定を確認し、LINE 通知設定等を整備してください（validate_config は live 時に注意喚起を行います）。
- ペーパートレード用 DB と本番監視 DB は分離されています（PAPER_TRADING_SQLITE_PATH）。
- AI 機能を利用する場合は OPENAI_API_KEY を適切に保護してください（.env を Git 管理しないこと）。
- run_execution/run_monitoring はプロセス優先度を "high" に設定して実行します（psutil による設定で失敗時は警告のみ）。
- ログディレクトリ作成に失敗した場合はコンソールログのみになります（ログ設定が適切にハンドリングします）。
- monitoring と execution は stop flag / kill flag の存在を確認して安全に停止する仕組みがあります。運用でフラグファイルを利用してプロセスを制御できます。

開発者向け
----------
- DuckDB 接続を渡す設計なので、リサーチ処理は高速にローカルで再現できます。
- テスト時は外部 API 呼び出し（OpenAI 等）をモックすることが想定されています（コード中に差し替えポイントあり）。
- config/*.yaml は PyYAML があればパース検証が行えます（validate_config）。

問い合わせ / 貢献
-----------------
バグ報告、機能提案、プルリクエストはリポジトリの Issue / PR 機能を利用してください。README に書かれていない実装詳細を確認したい場合は該当モジュールの docstring を参照してください。

以上。必要なら起動例や .env のテンプレートを追加で提供します。