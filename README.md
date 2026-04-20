README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームの骨組みを提供する Python パッケージです。本リポジトリは以下の用途を想定しています。

- バックテスト／リサーチ（DuckDB を用いたファクタ計算・特徴量解析）
- 発注エンジン（ExecutionEngine）による注文送信（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk の定期チェック、Kill Switch）
- AI を使ったニュースセンチメント評価・レジーム判定（OpenAI API）
- ペーパートレード検証レポート作成ツール

設計方針の概略
- DB は分析用に DuckDB、履歴／監視ログ用に SQLite を利用
- 設定は .env ファイル（または環境変数）で管理。config_setup.py による対話式ウィザードあり
- 本番とペーパートレードは DB を分離（PAPER_TRADING_SQLITE_PATH）
- OpenAI を用いる機能は API キー必須。失敗時は安全側のフォールバック処理あり

主な機能一覧
-------------
- 実行関連
  - run_execution.py: ExecutionEngine を起動（本番 / paper_trading 切替）
    - paper_trading 環境では MockBrokerClient を使い data/paper_trading.db に記録
    - プロセス優先度を高く設定、PID ファイル管理、停止フラグ監視
- 監視関連
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録
    - MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）
    - 監視は常に production の sqlite_path を使用
  - monitoring/ : SystemMonitor, TradeMonitor, RiskMonitor、MonitoringEngine、KillSwitch、DB 永続化層（monitoring_db.py）
- 環境設定 / 検証
  - config_setup.py: .env を対話式に作成・更新
  - validate_config.py: .env と config/*.yaml の事前検証（--strict オプションあり）
- リサーチ / ポートフォリオ構築
  - research/: ファクター計算（momentum/value/volatility）、将来リターン・IC 計算、統計サマリー
  - portfolio/: 候補選定、重み算出、リスク調整、株数決定（単元丸め等）
- AI 関連
  - ai/news_nlp.py: raw_news を LLM（OpenAI）でスコアリングして ai_scores に書き込む
  - ai/regime_detector.py: ETF (1321) の MA とマクロニュースを組み合わせて市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して PASS/FAIL レポートを出力

セットアップ手順
----------------
1. リポジトリをクローン、作業ディレクトリに移動
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 本コードで利用されている主なパッケージ:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML — validate_config の YAML 検証に必要
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt が無い場合は上記を手動でインストールしてください。

4. .env の作成
   - 対話形式で生成: python -m kabusys.config_setup
   - もしくは .env.example を参照して手動で作成

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

環境変数（主要）
-----------------
主に .env に設定する主なキー（必須 / 任意の区別）:

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: 発注は MockBrokerClient（data/paper_trading.db 使用）
    - live: 本番モード

- DB / ログ
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR (デフォルト: logs/)
  - PID_FILE_PATH (デフォルト: data/execution.pid)

- AI
  - OPENAI_API_KEY (news_nlp / regime_detector で使用)

- 監視関連
  - MONITOR_POLL_INTERVAL (run_monitoring が参照、秒。デフォルト 60)
  - KILL_FLAG_CLEAR_ON_START (起動時 kill.flag の自動クリア: 0/1)
  - KILL_FLAG_PATH (デフォルト data/kill.flag)
  - その他閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

自動 .env ロード
- ライブラリは起動時にプロジェクトルート（.git または pyproject.toml のある場所）から .env と .env.local を自動で読み込みます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（起動例）
----------------
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（注文エンジン）起動
  - python -m kabusys.run_execution
  - 備考: KABUSYS_ENV=paper_trading の場合はペーパートレード DB を使用

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（例: export MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でデフォルト DB を変更可能

停止・フラグ
-----------
- stop_requested.flag
  - run_monitoring / run_execution は data/stop_requested.flag を監視しており、存在するとループを終了します（開発時の安全な停止手段）。

- kill.flag（Kill Switch）
  - KillSwitch が条件を満たすと data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。
  - Settings の KILL_FLAG_CLEAR_ON_START が 1 に設定されていると、起動時に自動で kill.flag をクリアする挙動になります（本番では 0 推奨）。

ディレクトリ構成
----------------
（src/kabusys 以下の主なファイル・モジュールを示します）

- kabusys/
  - __init__.py
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - config.py                      — 環境変数 / Settings 管理
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py             — SQLite スキーマ & 永続化層
    - system_monitor.py
    - trade_monitor.py             — （詳細省略）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py             —（アラート送信ロジック）
  - execution/
    - execution_engine.py          — ExecutionEngine（主ロジック）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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

注意事項・トラブルシューティング
--------------------------------
- OpenAI 機能を使う場合は OPENAI_API_KEY を設定してください。未設定だと例外や早期の中断が発生します（各モジュールは可能な範囲で安全にフォールバックしますが、API 呼び出しは不可）。
- validate_config を実行して JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須環境変数が設定されていることを確認してください。
- ログディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります（警告が出力されます）。
- run_execution は PID ファイル（デフォルト data/execution.pid）を使用します。複数インスタンス起動に注意してください。
- monitoring は監視用 SQLite を使用しますが、監視は常に settings.sqlite_path（production 想定）を参照します。ペーパートレード環境であっても監視データは本番用パスに書き込まれる点に注意してください。

ライセンス・貢献
----------------
- このリポジトリのライセンス情報はプロジェクトのルートに置かれた LICENSE ファイル等を参照してください。
- バグ報告や機能改善は Pull Request / Issue で歓迎します。

補足（内部設計メモ）
-------------------
- 設定読み込み: .env → .env.local の順に（OS 環境変数が優先）
- DB マイグレーション: monitoring_db.init_monitoring_db は既存スキーマに対して安全にカラム追加等を行います
- ポートフォリオ構築は純粋関数群として実装され、ユニットテストが容易な作りになっています

以上。必要があれば README に追記すべき運用手順（systemd/cron 用の起動例、Docker 化手順、CI 設定例など）を追加します。どの情報が必要か教えてください。