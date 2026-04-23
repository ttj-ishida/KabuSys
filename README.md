KabuSys — 日本株自動売買システム（README）
========================================

概要
----
KabuSys は日本株の自動売買を想定したサンプル/実装骨組みです。  
主な目的は次のとおりです。

- データ収集・研究（DuckDB を利用したファクター計算）
- ポートフォリオ構築（銘柄選定、重み付け、リスク調整、株数決定）
- 注文実行基盤（ExecutionEngine。本番 / ペーパートレード切替）
- 監視・アラート（System / Trade / Risk の監視と Kill Switch）
- AI 補助（ニュースセンチメント / レジーム判定：OpenAI を利用）
- 運用補助ツール（設定ウィザード、設定検証、紙トレード検証レポート 等）

特徴（機能一覧）
----------------
- 環境ごとの DB 分離
  - 通常（monitoring）: SQLite (デフォルト data/monitoring.db) を監視ログに使用
  - DuckDB: 分析用データベース（デフォルト data/kabusys.duckdb）
  - paper_trading 環境では専用 SQLite（デフォルト data/paper_trading.db）を使用
- ExecutionEngine
  - BrokerClientFactory により本番 or MockBroker を切替（KABUSYS_ENV）
  - リスク制御（RiskManager）、注文管理（OrderManager）、照合（Reconciler）を含む
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセスの監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン・ポジション上限監視
  - KillSwitch: しきい値超過時に data/kill.flag を作成して Execution を停止
  - MonitoringEngine: 各監視を束ねて定期ポーリング、アラート送信（AlertManager）
- ポートフォリオ構築
  - 銘柄選定、等重・スコア重み、セクター上限適用、レジーム乗数、ポジションサイジング
  - 単元株（lot）に合わせた丸め、aggregate cap によるスケール調整
- リサーチ / ファクター計算
  - momentum, volatility, value 等のファクターを DuckDB 上で計算
  - 将来リターン計算、IC（Spearman）の算出、統計サマリ
- AI モジュール（OpenAI）
  - news_nlp: ニュースを LLM（gpt-4o-mini 等）でセンチメント評価して ai_scores に記録
  - regime_detector: ETF（1321）MA とマクロニュースを組み合わせて日次レジーム判定
  - 失敗時はフェイルセーフ（スコア 0 や skip）で運用継続
- 運用ツール
  - 設定ウィザード: python -m kabusys.config_setup（対話式 .env 生成）
  - 設定検証: python -m kabusys.validate_config（.env と config/*.yaml をチェック）
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
前提
- Python 3.10+（typing の OR 演算子（|）などを使用）
- SQLite は標準ライブラリで利用可能
- OS によっては psutil の一部機能に管理者権限が必要

必須 / 推奨パッケージ（例）
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（validate_config の YAML 内容チェックに必要）

インストール例
- 仮想環境を作成してパッケージをインストールします（例）:
  - python -m venv .venv
  - source .venv/bin/activate  # Windows: .venv\Scripts\activate
  - pip install --upgrade pip
  - pip install duckdb psutil openai PyYAML

環境変数設定
- プロジェクトルートに .env を配置するか OS 環境変数で指定します。
- 主要な環境変数（キーとデフォルト）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（例）
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（詳細は Settings）

.env 作成支援
- 対話式で .env を作成する:
  - python -m kabusys.config_setup

設定検証
- .env と config/*.yaml の基本チェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります

使い方（主要スクリプト）
-----------------------
起動スクリプト
- 監視ループ起動（SystemMonitor を使う）:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60）
    - run_monitoring は常に production 用 sqlite_path（Settings.sqlite_path）を参照します
    - 停止: data/stop_requested.flag を作成するとループが終了します

- 実行エンジン起動（ExecutionEngine）:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のとき MockBrokerClient を使用し data/paper_trading.db に記録
    - 実行中は data/execution.pid が使われます
    - 停止フラグ: data/stop_requested.flag を作成するとエンジン停止をトリガーします
    - KILL スイッチは data/kill.flag によって Execution を停止させる仕組みです

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI 機能
- news_nlp.score_news / regime_detector.score_regime を呼び出す際は OPENAI_API_KEY を設定してください。
- API 呼び出しはバッチ・リトライ・レスポンス検証を備えていますが、API キー未設定時は例外になります。

ログ
- ログ出力は標準出力と日次ローテーションファイル（logs/<app_name>.log）に出ます。
- setup_logging() により統一的に設定されます。

運用ノート
- Kill Switch: RiskMonitor がしきい値を超えると KillSwitch が data/kill.flag を作成します。ExecutionEngine は起動時・実行中にこのフラグを参照して停止します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では推奨しません）。
- プロセス優先度は起動スクリプト内で set_process_priority("high") を呼びます。権限によっては設定できない場合があります。

ディレクトリ構成（主要ファイル）
------------------------------
（プロジェクト配下の src/kabusys を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + ETF MA）
  - data/
    - (データパイプライン / DuckDB 関連モジュールがここにある想定)
  - monitoring/
    - monitoring_db.py        — SQLite 監視ログ用 DB 層（テーブル初期化・アクセス）
    - system_monitor.py       — システム状態・データ鮮度チェック
    - trade_monitor.py        — 注文関連の監視（該当ファイルあり）
    - risk_monitor.py         — ドローダウン等の監視（実装あり）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - kill_switch.py          — kill.flag の管理・作成ロジック
    - alert_manager.py        — アラート送信（LINE 等。別ファイル想定）
  - execution/
    - execution_engine.py     — ExecutionEngine（エンジン本体）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py    — 銘柄選定、重み付け
    - position_sizing.py      — 株数決定・リスク制限・単元丸め
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — momentum / volatility / value 等の計算
    - feature_exploration.py  — 将来リターン・IC・統計
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/monitoring_db.py — 監視 DB 初期化・アクセス（上記と重複参照あるが実態は同階層）

（注）実際のファイル群は上記に加えてさらに細分化されている可能性があります。プロジェクトルートには .env.example や config/*.yaml、data/、logs/ などが想定されます。

よくある操作例
----------------
- .env を作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 監視開始:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン開始:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 停止（両プロセス共通）:
  - プロジェクトルートに data/stop_requested.flag を作成する（run_* スクリプトが検出して終了）
- Kill Switch を手動で作成（Execution を強制停止）:
  - echo "reason" > data/kill.flag

補足 / 注意
------------
- 本リポジトリは実運用に用いる場合、追加のセキュリティ（シークレット管理）、エラーハンドリング、テスト、監査ログ、可観測性（メトリクス）等の整備が必要です。
- OpenAI を使う機能は API の利用料金が発生します。rate limit やコストに注意してください。
- KABUSYS_ENV=live を設定する際は特に JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE 通知等の設定を慎重に確認してください（validate_config が警告を出します）。

以上。必要であれば README に含めるサンプル .env テンプレートや systemd / supervisor 用の起動例、requirements.txt の候補を追記します。どれを追加しますか？