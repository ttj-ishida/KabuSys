README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株の自動売買／バックテスト／リサーチを想定した小型のフレームワークです。  
このリポジトリには、以下の主要機能を提供するモジュール群が含まれます。

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
- 監視／アラート（System/Trade/Risk Monitor）と監視ループ（run_monitoring / MonitoringEngine）
- 環境設定ウィザード（config_setup）と設定検証 CLI（validate_config）
- Paper Trading 検証レポート生成ツール
- ポートフォリオ構築、ポジションサイズ計算、リスク調整等の純粋関数群（portfolio）
- ファクター計算・特徴量探索（research）
- ニュース NLP / 市場レジーム判定（AI モジュール）

主な機能
----------
- 環境変数ベースの設定管理（.env の自動ロード、Settings クラス）
- 実行エンジンの起動／停止管理（PID ファイル、stop フラグ、kill flag）
- 監視ループ：システム状態・データ鮮度・注文滞留・ドローダウン等の定期チェック
- 監視ログの永続化（SQLite via MonitoringDB）
- Paper Trading と Live 環境の明確な分離（paper_trading では専用 SQLite を使用）
- DuckDB を用いたファクター計算・リサーチ用クエリ
- OpenAI（gpt-4o-mini 等）を使ったニュースのセンチメントスコアリングとレジーム判定（API 呼び出しはフェイルセーフ）

セットアップ手順
----------------
1. Python 環境を作成
   - 推奨: Python 3.10+ を仮想環境で用意する。
     例:
       python -m venv .venv
       source .venv/bin/activate

2. 依存ライブラリをインストール
   - 必要なライブラリのうち主なもの:
     - duckdb
     - psutil
     - openai
     - (オプション) PyYAML（config/*.yaml の検証に使用）
   - requirements.txt がある場合はそれを使ってください。指定がない場合は above を個別インストールします。
     例:
       pip install duckdb psutil openai pyyaml

3. プロジェクトルートの確認
   - config/*.yaml や .git / pyproject.toml をプロジェクトルートに配置してください。
   - .env をプロジェクトルートに作成します（config_setup を使用すると対話的に作成できます）。

4. 環境変数（.env）設定
   - 最低限必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う設定例:
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=... （AI 機能を使う場合）
   - 注意: .env は絶対にバージョン管理にコミットしないでください。

設定ウィザード / 検証
--------------------
- 対話式ウィザードで .env を作る:
    python -m kabusys.config_setup

- 設定の事前検証（.env と config/*.yaml をチェック）:
    python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）扱いになります。

使い方（主なスクリプト）
-----------------------

1) 監視ループ（SystemMonitor）起動
   - 監視は常時実行され、MonitoringDB（SQLite）へログを書き込みます。
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（秒）。デフォルト 60 秒。
   - 実行:
       python -m kabusys.run_monitoring
   - 停止:
     - プロセス側で KeyboardInterrupt（Ctrl+C）で停止、
     - またはプロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

2) 実行エンジン（ExecutionEngine）起動
   - 本番 / ペーパートレードの挙動は KABUSYS_ENV に依存。
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
   - 実行:
       python -m kabusys.run_execution
   - 停止:
     - 同様に KeyboardInterrupt、あるいは data/stop_requested.flag を作成するとエンジンに停止命令が届きます。
   - PID ファイルは data/execution.pid（デフォルト）に作成されます。

3) Paper Trading 検証レポート
   - Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等のレポートを出力します。
   - 実行例:
       python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB パス: data/paper_trading.db。--db で上書き可。環境変数 PAPER_TRADING_SQLITE_PATH も使用可。

4) AI 系（ニュース NLP / レジーム）
   - ai.news_nlp.score_news(conn, target_date, api_key=None)
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - OPENAI_API_KEY 環境変数を設定するか、関数引数で API キーを渡してください。
   - 呼び出しは DuckDB 接続（duckdb.connect(...) の返り値）を渡して使用します。

運用上のフラグ / ファイル
-------------------------
- data/stop_requested.flag
  - 起動中の run_monitoring や run_execution が存在チェックして終了処理を行うための停止フラグ（任意のファイル）。
- data/kill.flag
  - KillSwitch が書き込む停止フラグ。ExecutionEngine に停止シグナルを与える目的。存在すると ExecutionEngine を停止させる構成になっています。
- data/execution.pid（デフォルト）
  - 実行エンジンの PID を書き込むファイル。SystemMonitor はこの PID を参照してプロセス生存チェックを行います。
- .env / .env.local
  - Settings モジュールはプロジェクトルートの .env を自動的に読み込みます（OS 環境変数を保護）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY（AI 機能を使用する場合）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト 60）

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（Settings）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (未掲載の部分あり)
  - utils/
    - process_priority.py
    - __init__.py
  - execution/                — 発注関連（OrderRepository など、スクリプトから利用）
  - data/                     — 実行時生成されるファイル（DB / flags / pid など）
  - config/                   — system_config.yaml 等（config_setup が参照）

運用・開発の注意点
------------------
- .env は絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。
- Monitoring / Execution はデータベースファイルを共有しないよう設計されています（paper_trading は分離）。
- OpenAI など外部 API 呼び出しはフェイルセーフ（失敗時は続行、デフォルト値でフォールバック）を基本方針としています。
- system_monitor は PID ファイルを使って ExecutionEngine の生存を確認します。PID ファイルが壊れていると自動で削除されアラートを発行します。

開発向けヒント
----------------
- config/*.yaml が存在しないと警告になります。テンプレートは scripts/generate_config.py 等で生成できる想定です。
- PyYAML がない場合は YAML 検証をスキップするため、validate_config はその点を考慮しています。
- テスト時は AI API 呼び出し部分（_call_openai_api など）をモックすることが可能です（コード内でその旨コメントがあります）。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）。
- バグ報告・機能提案は Issue を立ててください。

以上がこのコードベースの概要と基本的な使い方です。必要があれば、特定モジュール（例: ExecutionEngine、OrderRepository、AlertManager）の使い方や設計詳細の README も作成します。どの項目を深掘りしましょうか？