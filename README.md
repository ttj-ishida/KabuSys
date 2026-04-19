README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買 / リサーチ / モニタリングを行うためのシンプルなフレームワークです。  
主な機能は以下の通りです。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理の実行
- 監視モジュール（MonitoringEngine）: システム状態・注文状態・リスクの定期チェックとアラート、Kill Switch
- ポートフォリオ構築: 候補選定・重み付け・ポジションサイズ算出・セクター制限
- ファクター / リサーチ: momentum, volatility, value 等のファクター計算・特徴量解析
- AI モジュール: ニュースの NLP スコアリング、レジーム判定（OpenAI API 使用）
- ツール: .env 初期化ウィザード、設定検証 CLI、Paper Trading 検証レポート生成

設計方針のハイライト
- DuckDB と SQLite を用途に応じて使い分け（分析用に DuckDB、監視/注文ログに SQLite）
- Paper Trading は本番 DB と分離（data/paper_trading.db を使用）
- 環境依存は .env / 環境変数で管理。自動ロード機能あり（プロジェクトルート検出）
- ログ設定は共通ユーティリティで統一（コンソール + 日次ローテーションファイル）

機能一覧
--------
- 実行 / 発注
  - Broker クライアント抽象化（本番/モック切り替え）
  - OrderManager / OrderRepository / Reconciler / RiskManager 等の組立て
  - ExecutionEngine によるセッション実行
- 監視
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス死活検出
  - TradeMonitor: 注文の滞留や約定異常の検出（コード内に実装あり）
  - RiskMonitor: ドローダウン検出・ポジション上限監視
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止
  - AlertManager（実装箇所に応じて LINE 等へ通知）
- ポートフォリオ構築
  - 候補選定（スコア順）、等重み・スコア加重、リスクベースの単元株丸め・投下資金スケーリング
  - セクターキャップ適用、レジームに応じた乗数
- Research
  - ファクター計算（momentum/volatility/value）
  - 将来リターン計算・IC 計算・統計サマリー
- AI
  - news_nlp.score_news: raw_news を LLM（OpenAI）でスコアリングし ai_scores に書き込み
  - regime_detector.score_regime: ETF とマクロニュースを混合して市場レジームを判定
- ツール
  - config_setup: .env を対話的に作成・更新
  - validate_config: .env と config/*.yaml の基本検査
  - tools.paper_verification_report: Paper Trading の稼働・注文成功率・レイテンシ等のレポート

セットアップ手順
----------------
前提:
- Python 3.9+（ソースに型記述あり）
- SQLite / DuckDB を使用（duckdb パッケージを利用）
- OpenAI を使う機能は OPENAI_API_KEY が必要
- 依存パッケージ（代表例）: duckdb, psutil, openai, PyYAML（任意: 設定検証で使用）

1. リポジトリをクローン
   - git clone … && cd <project>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （設定検証で YAML を使う場合）pip install pyyaml

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用

4. .env の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは .env を直接作成（.env.example を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

6. 必要ディレクトリ作成
   - data/ と logs/ は起動時に自動作成されることが多いですが、権限等で失敗する場合は手動で作成してください。

主要な環境変数（代表）
--------------------
- JQUANTS_REFRESH_TOKEN : J-Quants API（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABUSYS_ENV           : 実行環境 (development | paper_trading | live)（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録
- SQLITE_PATH           : 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH           : DuckDB（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL             : ログレベル（例: INFO）
- LOG_DIR               : ログ保存先（デフォルト: logs/）
- OPENAI_API_KEY        : OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL : 監視ループのポーリング間隔（秒、既定 60 秒。無効値はデフォルトにフォールバック）
- KILL_FLAG_PATH        : kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（"1" で有効。production では推奨しない）

使い方（コマンド例）
------------------
- .env を対話式で作る:
  - python -m kabusys.config_setup

- 設定を検証:
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
    - 補足:
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（秒、デフォルト: 60）
      - monitoring はどの KABUSYS_ENV でも settings.sqlite_path（本番用監視 DB）を使用する
      - 停止: data/stop_requested.flag を作成するとループ終了（または Ctrl+C）

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
    - 補足:
      - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
      - 起動時に data/stop_requested.flag が存在すると起動をスキップ
      - 実行中の PID は data/execution.pid に書き込まれる
      - 停止シグナルは data/stop_requested.flag または Kill Switch により行える

- Paper Trading 検証レポートの生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH （デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 関連（OpenAI API キーが必要）
  - news_nlp.score_news / regime_detector.score_regime はライブラリ API として呼び出す:
    - 例: from kabusys.ai.news_nlp import score_news
      - score_news(conn, target_date, api_key="...")
    - 注意: API キーは OPENAI_API_KEY 環境変数か引数で渡す必要あり

ログ・ファイル
--------------
- ログはデフォルトで logs/ 下に app_name.log（例: execution.log, monitoring.log）として日次ローテーションで出力されます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御します。

停止・Kill Switch
-----------------
- 手動停止フラグ:
  - data/stop_requested.flag — run_monitoring / run_execution がこれを検知して終了
- Kill Switch:
  - monitoring モジュール（KillSwitch）がリスク条件を満たすと data/kill.flag に理由を書き込み、
    ExecutionEngine 側はこのフラグを検知して安全停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番環境では推奨されません。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主要モジュール（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env の読み込みと Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 操作用の永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - monitoring/                （上記）
  - tools/
    - paper_verification_report.py

（注）上記は実装上の主要モジュールを抜粋したものです。細かい補助モジュールや実装ファイルが他にも存在します。

開発・運用に関する注意
--------------------
- Paper Trading 用 DB と本番監視 DB は分離されています。paper_trading モード時は settings.paper_sqlite_path を使用するため、本番データを汚染しません。
- Monitoring は settings.sqlite_path（本番監視 DB）を常に使用します（環境に依存しない仕様）。
- AI 機能は外部 API（OpenAI）に依存します。API 呼び出しはリトライやフェイルセーフが組み込まれていますが、API キーの適切な管理・レート制御に注意してください。
- ログディレクトリ・DB ファイルのディレクトリ作成に失敗する場合、ファイルハンドラはスキップされコンソール出力のみになります。権限やパスを事前に確認してください。
- MONITOR_POLL_INTERVAL に 0 や負の値を指定すると無効としてデフォルト（60 秒）にフォールバックします。

貢献・拡張
----------
- BrokerClient の実装差し替え、アラート送信先（LINE, Slack 等）の追加、ポートフォリオ構築アルゴリズムの拡張、strategy モジュールの追加などが想定されます。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）に合わせて research/ai モジュールを調整してください。

ライセンス・バージョン
----------------------
パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）  
ライセンス情報はリポジトリルートの LICENSE を確認してください（ない場合はプロジェクト方針に従って追加してください）。

補足（よくあるコマンドまとめ）
------------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 監視開始: python -m kabusys.run_monitoring
- 実行エンジン開始: python -m kabusys.run_execution
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

以上。必要なら README に含めるチュートリアルや .env.example のテンプレート、起動例ログ、依存関係ファイル（requirements.txt）の推定内容なども追加できます。必要なものを教えてください。