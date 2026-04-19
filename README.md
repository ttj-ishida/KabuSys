README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワークです。本リポジトリは以下の主要機能を持ち、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP を組み合わせて運用・検証を行えるよう設計されています。

- バックテスト用の DuckDB を使ったファクター計算・研究モジュール
- 実運用／ペーパートレード用 ExecutionEngine（ブローカークライアント差し替え可）
- 監視コンポーネント（System / Trade / Risk モニタ）と Kill Switch
- OpenAI を使ったニュースセンチメント評価（AI モジュール）
- 環境設定ウィザードと設定検証ツール
- Paper Trading の検証レポート生成ツール

バージョン
----------
パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

主な機能一覧
-------------
- Execution（実行エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - RiskManager / OrderManager / Reconciler を組み合わせた実行フロー
  - ペーパートレード時は MockBrokerClient を使い DB を完全分離（data/paper_trading.db）
- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク、データ鮮度、実行プロセスの存在チェック
  - TradeMonitor：発注ログの滞留/異常チェック（trade_logs）
  - RiskMonitor：ドローダウン監視・ポジション上限監視、ダッシュボード更新
  - KillSwitch：閾値超過で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記を束ねてポーリング
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額・スコア重み配分
  - セクター制限・レジーム乗数・ポジションサイズ計算（単元株丸め等）
- Research（リサーチ）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリ
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）でニュースを集約して銘柄ごとにセンチメントスコアを生成
  - マクロニュース + ETF ma200 乖離で市場レジーム判定（bull/neutral/bear）
- Utils / ツール
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティ
  - 環境設定ウィザード（.env 作成支援）、設定検証 CLI
  - Paper Trading 検証レポート生成スクリプト

前提・依存
----------
想定 Python バージョン: 3.10 以上（注: ソースで | 型注釈を使用）

主要依存（例）:
- duckdb
- psutil
- openai（OpenAI の新 v1 SDK を使用する想定）
- PyYAML（設定検証時の YAML 検証は任意）
- （標準ライブラリ）sqlite3, logging, threading 等

インストール例:
- 要件ファイルがあれば: pip install -r requirements.txt
- 個別インストール例:
  pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate.bat  # Windows

3. 依存パッケージのインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は上記主要依存を個別にインストール）

4. .env の作成
   推奨: 対話式ウィザードで作成
   python -m kabusys.config_setup

   代表的な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   その他主要変数（任意 / 推奨）:
   - KABUSYS_ENV (development | paper_trading | live)
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
   - LOG_LEVEL
   - LOG_DIR
   - OPENAI_API_KEY（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番でのアラート用）

5. 設定検証
   python -m kabusys.validate_config
   --strict を付けると警告も FAIL 扱いになります。

使い方
------
起動スクリプト（CLI）:
- 監視ループを起動
  python -m kabusys.run_monitoring

  補足:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60 秒）
  - run_monitoring は monitoring 用の sqlite_path（settings.sqlite_path）を環境にかかわらず使用します
  - 停止はプロジェクトルート/data/stop_requested.flag の存在で検知

- 実行エンジン（ExecutionEngine）を起動
  python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）
  - 起動時のプロセス優先度を high に設定します
  - 起動前に data/stop_requested.flag が既に存在すると起動をスキップします
  - 実行中は data/execution.pid に PID を書きます。停止は stop flag を作成する、または ExecutionEngine の内部ロジックで kill.flag を検出します

- 環境設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

  主要閾値（スクリプト内定数）:
  - 稼働率（uptime）: 閾値 99.0%
  - 注文成立率（fill_rate）: 閾値 90.0%
  - 送信率（send_rate）: 閾値 95.0%
  - P95 レイテンシ: 200 ms

プログラムから呼び出す主要 API
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡してニュースセンチメントスコアを ai_scores テーブルへ書き込みます
- kabusys.research.calc_momentum / calc_volatility / calc_value
  - DuckDB 接続と target_date を渡してファクター計算します
- kabusys.portfolio.* 関数群
  - 候補選定、配分、ポジションサイズ計算等

運用メモ
--------
- Kill Switch / 停止制御
  - KillSwitch は settings.kill_flag_path（デフォルト data/kill.flag）に文字列を書き、ExecutionEngine 側がそれを検出して停止します
  - run_monitoring / run_execution はプロジェクトルート/data/stop_requested.flag の存在でループ終了を検知します
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します

- DB 分離
  - 通常の監視ログ（monitoring）は settings.sqlite_path（data/monitoring.db デフォルト）を使用します
  - ペーパートレード時は別 DB を使用（PAPER_TRADING_SQLITE_PATH）

- ログ
  - ログは logs/<app_name>.log に日次ローテートで出力されます（デフォルト logs/）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一されます

- プロセス優先度 / CPU affinity
  - 起動スクリプトは set_process_priority("high") を呼び出して優先度を上げます（psutil を使用）
  - set_cpu_affinity 関数でコアピニングも可能（管理者権限などにより失敗する場合があります）

環境変数一覧（抜粋）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要／運用系:
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY: AI（ニュース / レジーム）を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先ディレクトリ
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH: 実行エンジンの PID ファイルパス
- KILL_FLAG_PATH: kill.flag のパス
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py     — 共通ログ設定
    - process_priority.py  — 優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
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
    - news_nlp.py           — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成

補足
----
- プロジェクトルートに .env.example や config/*.yaml などのテンプレートがある想定です（validate_config で参照）。
- OpenAI 周りは API 呼び出しに依存するため、API キー、レート制限、ネットワークの安定性に留意してください。失敗時はフェイルセーフ動作（0.0 フォールバック、スキップ等）が多く組み込まれています。
- DuckDB / SQLite のファイルはデフォルトで data/ 下に置かれます。運用環境ではマウント / 永続化を適切に設定してください。

貢献
----
バグ報告・改善提案は issue を立ててください。新機能は設計文書（PortfolioConstruction.md / StrategyModel.md）に沿って追加してください。

ライセンス
---------
（ここにプロジェクトのライセンス情報を追記してください）

--- End of README ---