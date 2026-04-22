KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視用ユーティリティ群を含む小規模なパッケージです。  
主な目的は以下を提供することです。

- 売買実行エンジン（ExecutionEngine）とペーパートレード切替
- システム監視（SystemMonitor）・リスク監視（RiskMonitor）・アラート管理
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- ニュース NLP（OpenAI を用いたニュースセンチメント算出）
- 各種ユーティリティ（設定ウィザード・設定検証・レポート生成）

主な特徴
--------
- 実行環境切替: KABUSYS_ENV により development / paper_trading / live を選択可能。paper_trading 時は MockBroker を使用し、本番 DB と分離された data/paper_trading.db を利用。
- .env ウィザード: 対話式に .env を生成・更新する config_setup CLI。
- 設定検証: 起動前に必須環境変数や config/*.yaml の存在を確認する validate_config CLI。
- 柔軟なログ設定: logs/<app>.log に日次ローテーションでログ出力（TimedRotatingFileHandler）。
- モニタリング: system_status / trade_logs / risk_logs / positions / dashboard を保持する SQLite ベースの監視 DB。
- ニュース NLP / レジーム判定: OpenAI（gpt-4o-mini 等）を利用したセンチメント評価機能（API キー必要）。
- 分析用 DB: DuckDB を使った価格・財務データのファクター計算・リサーチ機能。

セットアップ
-----------
1. Python と依存パッケージのインストール
   - Python 3.9+ を推奨
   - 必要パッケージ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml 検証を行う場合）
   - 例:
     pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

2. プロジェクトルートで .env を用意
   - 対話式ウィザードを使う（推奨）:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルートに配置）。主なキー:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（data/paper_trading.db）
     - OPENAI_API_KEY — ニュース NLP / レジーム判定 に必要（使用する場合）
     - LOG_LEVEL — INFO 等

   - ウィザード実行後は python -m kabusys.validate_config で検証してください。

3. ディレクトリと権限
   - data/ および logs/ は自動作成されますが、必要に応じて手動で作成・書き込み権限を確認してください。
   - PID / flag ファイルのパス（デフォルト: data/execution.pid, data/kill.flag, data/stop_requested.flag）に対する書込み権限も必要です。

使い方（主要 CLI / API）
-----------------------

各スクリプトはパッケージモジュールとして実行可能です（プロジェクトルートで）。

1. 環境設定ウィザード
   - .env を対話的に作成/更新:
     python -m kabusys.config_setup

2. 設定検証
   - .env と config/*.yaml の基本チェック:
     python -m kabusys.validate_config
   - 警告も失敗にする（--strict）:
     python -m kabusys.validate_config --strict

3. 実行エンジン（ExecutionEngine）
   - 本番 / 開発 / ペーパートレードの起動:
     python -m kabusys.run_execution
   - ペーパートレード時（KABUSYS_ENV=paper_trading）: MockBroker を使用し記録は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ。起動前に data/stop_requested.flag が存在すると起動しません。
   - 停止: data/stop_requested.flag を作成すると起動中のエンジンが検出して停止します（また kill.flag は ExecutionEngine 停止のために monitoring が書き込むことがあります）。

4. 監視プロセス（Monitoring）
   - SystemMonitor をポーリングして監視を行う:
     python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60 秒）。
   - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使います（環境に関わらず）。

5. ペーパートレード検証レポート
   - レポート生成:
     python -m kabusys.tools.paper_verification_report
   - 期間指定:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスを直接指定:
     python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

6. ニュース NLP / レジーム判定（API）
   - OpenAI API を利用する機能:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB 接続（duckdb.connect(...)）を受け取り、ai_scores / market_regime テーブルなどへ書き込みます。
   - api_key を引数で与えるか、環境変数 OPENAI_API_KEY を設定してください。

7. 研究・ポートフォリオ API
   - リサーチ:
     - kabusys.research.calc_momentum(conn, date)
     - kabusys.research.calc_volatility(conn, date)
     - kabusys.research.calc_value(conn, date)
     - kabusys.research.calc_forward_returns(...)
     - kabusys.research.calc_ic(...)
   - ポートフォリオ:
     - kabusys.select_candidates(...)
     - kabusys.calc_equal_weights(...)
     - kabusys.calc_score_weights(...)
     - kabusys.calc_position_sizes(...)
     - kabusys.apply_sector_cap(...)
     - kabusys.calc_regime_multiplier(...)

   例（簡易）:
   from pathlib import Path
   import duckdb
   from datetime import date
   conn = duckdb.connect("data/kabusys.duckdb")
   records = kabusys.research.calc_momentum(conn, date.today())

運用上のポイント / 注意事項
-------------------------
- .env の自動読み込み:
  - config module はプロジェクトルート（.git または pyproject.toml がある階層）を探して .env を自動ロードします（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 重要環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。validate_config でチェックされます。
  - OPENAI_API_KEY はニュース NLP / レジーム判定に必要（未設定時は該当機能がエラーを投げる）。
- DB とロギング:
  - デフォルト DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db
  - ログ: logs/<app>.log（アプリ名は run_execution/run_monitoring などで設定）
- Kill Switch / Stop Flags:
  - monitoring は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます。ExecutionEngine は data/stop_requested.flag の存在で停止を検知します。設定により起動時に kill.flag を自動クリアする動作が設定可能（KILL_FLAG_CLEAR_ON_START）。
- 権限:
  - プロセス優先度や CPU affinity を設定するために psutil を使用します。アクセス権限が不足すると警告が出ますが、処理は継続します。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys をルートとした構成の抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — レジーム判定（OpenAI + MA200）
  - monitoring/
    - monitoring_db.py       — SQLite（監視用テーブル）初期化・ラッパ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文/約定の監視（省略コードあり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 制御
    - alert_manager.py       — アラート送信管理（省略）
  - execution/
    - execution_engine.py    — 実行エンジン（省略）
    - order_manager.py       — 注文管理（省略）
    - broker_factory.py      — ブローカークライアント生成（Mock/実口座）
    - order_repository.py    — 注文永続化（省略）
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・資金配分
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — IC/統計量 等
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ロギング初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

補足
----
- この README ではコードの主要機能と利用方法の概要を示しました。各モジュールの詳細な使い方や引数仕様はソースコード内の docstring を参照してください。  
- 本パッケージは実際の発注・資金運用を行うためのサンプル実装を含みます。live 環境での運用前には設定・ガード条項（LINE 通知や kill flag の運用等）を十分に確認してください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- ライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）。

質問や補足の要望があれば、どのコマンドやモジュールの詳細を追加で記載するか教えてください。