README — KabuSys（日本株自動売買システム）
=====================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的としたパッケージです。本コードベースは以下の主要機能を提供します。

- 発注実行エンジン（ExecutionEngine）とブローカークライアントの抽象化（ペーパートレード対応）
- システム監視（プロセス稼働、リソース、データ鮮度）とアラート/Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制約）
- ファクター計算・研究ユーティリティ（Momentum / Volatility / Value 等）
- ニュースNLP とレジーム判定（OpenAI を用いたセンチメント評価）
- Paper Trading の検証レポート生成ツール
- 環境設定ウィザードと起動前検証ツール
- 汎用ユーティリティ（ログ設定、プロセス優先度設定など）

主な特徴（機能一覧）
-------------------
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py — SystemMonitor のポーリングループを起動（監視用 DB に書き込み）
- 設定関連
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env / config/*.yaml の事前検証 CLI
  - config.py — 環境変数読み込み / Settings 抽象化（デフォルト値とバリデーション）
- モニタリング
  - monitoring_db.py — 監視ログ用 SQLite スキーマと永続化ロジック
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py
- 発注・リスク
  - ExecutionEngine をはじめとする execution パッケージ（BrokerFactory、OrderManager、RiskManager など）
  - paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
- ポートフォリオ構築（純粋関数）
  - portfolio_builder, position_sizing, risk_adjustment
- リサーチ
  - research パッケージにファクター計算・特徴量解析ツール
- AI
  - ai.news_nlp (ニュースセンチメントのスコア化)
  - ai.regime_detector (マクロ + ETF ma200 乖離でレジーム判定)
- ツール
  - tools.paper_verification_report — Paper Trading の運用検証レポート出力

セットアップ手順
----------------

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必須パッケージのインストール
   - 依存一覧はプロジェクトの requirements.txt があればそれを使ってください:
     - pip install -r requirements.txt
   - 主要な外部依存（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（optional: validate_config の YAML 検証用）
   - sqlite3 は標準ライブラリです。

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に）。重要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - OPENAI_API_KEY（AI モジュール使用時）
     - PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の約定挙動
     - KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか（注意: 本番では 0 推奨）
   - env 自動ロード:
     - プロジェクトルート（.git or pyproject.toml の位置）を基に .env / .env.local を自動ロードします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告もエラーに含める厳密モード:
     - python -m kabusys.validate_config --strict

使い方（起動・運用）
-------------------

- ログ設定
  - ログ出力は標準出力と logs/<app_name>.log（日次ローテーション、30日分保持）に出力されます。
  - 環境変数: LOG_DIR, LOG_LEVEL で制御可能。
  - 起動スクリプトは共通ユーティリティ setup_logging を呼び出します。

- 実行エンジン（ExecutionEngine）
  - 起動:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が利用され、発注履歴は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます（本番DBと分離）。
    - 起動前に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中は data/execution.pid に PID を書きます（Engine の pid_file 引数で変更可能）。
    - 停止は data/stop_requested.flag を作成することで実行スレッドに終了を促します（run_execution が検知して engine.stop() を呼びます）。

- 監視プロセス（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - 環境変数 MONITOR_POLL_INTERVAL で秒単位のポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は sqlite_path（Settings.sqlite_path）に常に本番用パスを使用して書き込みます（Monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を参照する設計）。
  - run_monitoring は data/stop_requested.flag を検知するとループを終了します。

- Kill Switch（自動停止）
  - KillSwitch はリスク条件（ドローダウンやポジション上限など）に従って data/kill.flag を書き込みます。ExecutionEngine 側はこの kill.flag を読み取り停止します（設定により起動時に自動クリア可）。
  - KillSwitch.clear() で削除できます。環境変数 KILL_FLAG_CLEAR_ON_START による自動クリア設定は Settings から参照されます（本番では無効推奨）。

- Paper Trading 検証レポート
  - 使い方:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH を使用
  - 出力指標:
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（avg/max/P95）など

- AI モジュール（OpenAI）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡して銘柄ごとの ai_score を ai_scores テーブルへ書き込む。
    - OPENAI_API_KEY は環境変数か api_key 引数で与える。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメントを組み合わせて market_regime テーブルへ書き込む。
  - 注意点:
    - API 呼び出しに失敗した場合はフェイルセーフ（部分的にスキップ or デフォルト値）を行う設計。
    - 使用するモデルやリトライの挙動はモジュール内で定義されています。

停止・フラグファイル
-------------------
- data/stop_requested.flag
  - run_execution/run_monitoring の外部停止フラグ（存在するとメインループが終了します）。
- data/kill.flag
  - KillSwitch が書き込むフラグ。ExecutionEngine 側で検出し停止させる仕組み。
- data/execution.pid
  - run_execution が書き出す PID ファイル（Engine 側の pid_file）。

ディレクトリ構成（抜粋）
-----------------------
プロジェクトの主要ファイル構成（src/kabusys 以下の主要モジュール）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (ログや通知を管理するモジュールが含まれます)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...（発注ロジック一式）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

運用上の注意
------------
- 本番モード（KABUSYS_ENV=live）では設定ミスが重大な損失に繋がる可能性があります。validate_config の実行と LINE 通知等の設定確認を必ず行ってください。
- .env は機密情報（API キー・パスワード等）を含みます。絶対に Git にコミットしないでください（config_setup もヘッダで注意喚起しています）。
- Paper Trading は本番 DB と分離する設計ですが、設定ミスで混在しないよう各 DB パスを明確に設定してください。
- OpenAI API を利用するモジュールは API 使用量が発生します。API キー管理とコスト計画に注意してください。

トラブルシューティング
---------------------
- ログが出力されない/ログファイルが作成されない場合:
  - LOG_DIR のパーミッション、ディレクトリ存在、または setup_logging の実行順序を確認してください。
- psutil によるプロセス優先度設定が失敗する場合:
  - 実行ユーザーに権限がない、あるいはプラットフォーム未対応（例: 一部の BSD）である可能性があります。警告ログが出力されますが処理自体は継続します。
- OpenAI 呼び出しで JSON パースやレスポンス不整合が発生する場合:
  - レスポンスのバリデーションが失敗するとそのチャンクはスキップされます。ログを確認してください。

補足（開発向け）
----------------
- モジュールはできるだけ副作用を少なく純粋関数で実装する方針です（portfolio / research 等）。
- DuckDB を利用した分析処理は SQL と Python を組み合わせて実行します。
- テストやモックが容易になるよう、外部 API 呼び出しポイント（OpenAI など）はラップされ、テスト用に差し替え可能です。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ で管理しています（例: 0.1.0）。

最後に
-----
この README はコードベースの主要点をまとめたものです。細かい挙動や追加の CLI オプションは各モジュールの docstring と実装を参照してください。運用前に必ず validate_config と小規模なローカル実行（paper_trading モード）で動作確認を行ってください。