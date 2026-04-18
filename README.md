README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主な目的は「ファクタ計算 → シグナル生成 → 発注（本番／ペーパートレード）→ 監視／アラート」までのワークフローをサポートすることです。  
このリポジトリにはエンジン起動スクリプト、監視（Monitoring）、ポートフォリオ構築・サイズ計算、ファクター計算、AI を利用したニュース解析／レジーム判定、各種ユーティリティが含まれます。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番／ペーパートレードを切り替え可能。paper_trading モードでは MockBrokerClient を使用して paper_trading.db に記録。
  - リスク管理（RiskManager）、OrderManager、Reconciler 等の組み合わせで発注を実行。
- Monitoring（監視）
  - システムリソース、データ鮮度、滞留注文や約定異常、ドローダウン・ポジション上限などを定期チェック。
  - kill.flag による外部停止（Kill Switch）・アラート発行。
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重／スコア重み、ポジションサイズ計算（単元丸め・集約上限考慮）など。
- リサーチ
  - DuckDB 接続を用いたファクター計算（Momentum/Volatility/Value 等）、将来リターン計算、IC 計算、統計サマリー。
- AI 機能（OpenAI）
  - ニュースのセンチメントスコアリング（ai_scores への書き込み）。
  - マクロ＋ETF MA 乖離による市場レジーム判定（market_regime への書き込み）。
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

前提・要件
-----------
推奨（主要な依存）:
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の内容検証を行う場合）
- sqlite3（標準ライブラリ）

インストール（例）
-----------------
1. 仮想環境を作る:
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール（requirements.txt があればそれを使用）:
   pip install duckdb psutil openai PyYAML

初期セットアップ（.env の作成）
------------------------------
1. 対話式ウィザードで .env を作成:
   python -m kabusys.config_setup

   - 主要項目（必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 実行環境:
     - KABUSYS_ENV = development | paper_trading | live
       - paper_trading: mock ブローカー・別 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
       - live: 本番（実発注）モード
   - その他:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN など

2. 設定検証:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）になります。

注意:
- 自動で .env をロードする仕組みがあり、プロジェクトルートにある .env / .env.local が読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 必須の環境変数が未設定の場合は起動時にエラーになります。

主要環境変数（抜粋とデフォルト）
--------------------------------
- KABUSYS_ENV: development | paper_trading | live (default: development)
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- LOG_DIR: logs
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0/1
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI を用いる機能で使用

実行方法
--------
- 監視ループ（Monitoring）
  - 説明: SystemMonitor を周期的に実行し、監視ログを SQLite に書き込む。MONITOR_POLL_INTERVAL（秒）でポーリング間隔を指定可能。
  - 注意: Monitoring は KABUSYS_ENV に関係なく常に sqlite_path（監視 DB）を使用します。
  - 実行:
    python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag ファイルを作成するとループが検知して終了します。Ctrl+C（KeyboardInterrupt）も有効。

- ExecutionEngine（発注エンジン）
  - 説明: ExecutionEngine を起動して当日のセッションを実行。paper_trading モードでは MockBroker を使用して PAPER_TRADING_SQLITE_PATH に記録します。
  - 実行:
    python -m kabusys.run_execution
  - 停止: data/stop_requested.flag を作成すると Engine が検知して安全に停止します。
  - PID ファイル: data/execution.pid に PID を書きます（設定可能）。

- .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

AI 機能（OpenAI）
-----------------
- ニュース NLP（センチメント算出）:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - 必要: OPENAI_API_KEY（引数 or 環境変数）
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 必要: OPENAI_API_KEY
- 注意: API 呼び出しはリトライやフォールバックを備えていますが、API キーは必須です。

ログ
---
- ログ出力は共通ユーティリティ kabusys.utils.logging_setup.setup_logging により管理されます。
- デフォルトは logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30 日分保持）とコンソール出力（stdout）。
- ログレベルは LOG_LEVEL 環境変数か引数で指定可能。

停止・キルスイッチ
------------------
- data/kill.flag: Kill Switch（ExecutionEngine 停止シグナル）。KillSwitch クラスが条件検出時にこのファイルを書き込みます。
- data/stop_requested.flag: run_monitoring / run_execution が存在を検知してループやスレッドを終了します。
- KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合、起動時に kill.flag を自動クリアする設定があります（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - broker_factory.py
    - execution_engine.py
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
    - news_nlp.py
    - regime_detector.py

（注）上記はリポジトリ内の主要モジュールを抜粋したものです。実装ファイルはさらに細分化されています。

開発上の注意点
--------------
- DuckDB 接続は多くのリサーチ関数で必要です（prices_daily / raw_financials / raw_news 等のテーブルを参照）。
- Monitoring の DB 初期化は冪等（init_monitoring_db）で実行されます。
- 設定ファイル（config/*.yaml）や .env のテンプレートは scripts 等で生成する想定です。validate_config は YAML の存在とパースチェック（PyYAML 必須）を行います。
- AI 機能は OpenAI API に依存するため、API 利用料・レート制限に注意してください。失敗時はフェイルセーフ（スコア 0.0 やスキップ）で続行する設計です。

サンプルコマンドまとめ
---------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視起動: python -m kabusys.run_monitoring
- エンジン起動: python -m kabusys.run_execution
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

サポート / 拡張
----------------
- 追加のログハンドラやメトリクス出力、ブローカー実装の切り替え、銘柄別単元情報取り込みなどは utils / execution / portfolio モジュールを拡張してください。
- テストや CI で自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードをスキップします。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

おわりに
--------
この README はリポジトリ内のスクリプトおよびユーティリティの使い方・構成の概要を示しています。開発を始める際はまず .env を作成し validate_config によるチェックを行ってください。実運用では logs ディレクトリや data ディレクトリ（DB・フラグファイル）へのアクセス権やバックアップ方針を整備することを推奨します。