README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームです。本リポジトリは取引実行、監視、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント／レジーム判定）などのモジュール群を含みます。設計方針としては「本番ロジックと研究ロジックの分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（APIエラー時は安全側にフォールバック）」を重視しています。

主な機能
--------
- ExecutionEngine: 発注・リスク管理・注文再整合（paper_trading モードあり、paper_trading は本番 DB と分離して data/paper_trading.db に記録）
- Monitoring: システムリソース・データ鮮度・注文の健全性・リスク（ドローダウン、ポジション上限）を定期チェック。Kill Switch により危険時に ExecutionEngine を停止可能
- Portfolio construction: 候補選定、重み計算（等配分・スコア加重）、ポジションサイズ決定、セクター上限・レジーム乗数適用
- Research: ファクター（Momentum / Volatility / Value 等）計算、将来リターン・IC 計算、統計サマリ
- AI: ニュースからのセンチメントスコアリング（OpenAI 使用）と市場レジーム判定（ma200 + マクロセンチメント）
- ユーティリティ:
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

前提（依存）
-------------
少なくとも以下のパッケージが必要です（プロジェクトにより増減します）:
- Python 3.8+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の内容検証を行う場合に必要）
- （その他、実行環境に応じた追加依存がある場合があります）

セットアップ手順
---------------
1. リポジトリをクローン / 配布ファイルを配置
2. 仮想環境作成・依存インストール（例）
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt
   （requirements.txt がない場合は必要パッケージを個別に pip install）
3. .env の作成
   - 対話ウィザードで生成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （本番 OpenAI を使う場合）OPENAI_API_KEY
     - KABUSYS_ENV: development / paper_trading / live
4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格扱いしたい場合: python -m kabusys.validate_config --strict
5. データディレクトリとログディレクトリの準備
   - デフォルトで data/ と logs/ が使われます。設定で変更可能（DUCKDB_PATH/SQLITE_PATH/LOG_DIR）。
   - 必要なら手動でディレクトリ作成: mkdir -p data logs

主要な環境変数（主なもの）
-------------------------
（デフォルトはコード注釈・Settings を参照）
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — AI モジュールを使うときに必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading のフィルモード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch の flag ファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（"1" で有効）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

使い方（主要スクリプト）
-----------------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading に設定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - 実行中に data/stop_requested.flag を作成すると安全に停止します

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を変更可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を監視 DB として使用します
  - 停止は data/stop_requested.flag を作成するか Ctrl+C

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュール（プログラム的に呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジームスコア:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

ログ・プロセス管理
-----------------
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力（30日分保持）
- setup_logging() を全スクリプトで使用して統一されたロギング設定を行っています
- 起動時に set_process_priority("high") を呼んでプロセス優先度を上げようとします（権限により失敗する場合は警告）

監視・Kill Switch の概要
------------------------
- Monitoring 系:
  - SystemMonitor: CPU/MEM/DISK、Execution プロセスの PID 存在チェック、データ鮮度チェック（duckdb の prices_daily）
  - TradeMonitor: trade_logs テーブル等を監視（遅延注文の検出、約定異常等）
  - RiskMonitor: ダッシュボードのハイウォーターマークを使ったドローダウン監視・ポジション数監視。閾値超過時に risk_logs に記録
  - KillSwitch: RiskMonitor 等の結果を評価して data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る（起動時に ExecutionEngine が kill.flag を検出し停止）
- run_monitoring / MonitoringEngine は _STOP_FLAG（data/stop_requested.flag）を監視して終了

ディレクトリ構成（主なファイル）
--------------------------------
（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定読み込みロジック (.env 自動ロード等)
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py      — レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite ベースの監視永続化層
    - system_monitor.py
    - trade_monitor.py        — （実装ファイルは存在、監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — アラート送信（LINE など）管理（コード内参照）
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py       — BrokerClient の生成（Mock / 実ブローカー切替）
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                     — デフォルトの DB / flag / pid など（プロジェクトルート直下）
    - monitoring.db           (デフォルト SQLITE_PATH)
    - paper_trading.db        (paper_trading 用)
    - kabusys.duckdb          (デフォルト DUCKDB_PATH)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/                     — デフォルトのログ出力先（LOG_DIR）

補足・注意
-----------
- .env は絶対にリポジトリにコミットしないでください（config_setup.py の出力にもその注意書きがあります）
- Monitoring は監視 DB（SQLite）を用いて状態を永続化します。init_monitoring_db() は既存 DB に対して冪等でスキーマを作成・マイグレーションを行います
- AI（OpenAI）を利用する機能は API キーが必要です。失敗時には多くの箇所でフェイルセーフ（スコア 0.0、スキップ等）を取る設計ですが、期待どおりに動作させるには正しいキーとネットワーク接続が必要です
- paper_trading モードは本番 DB とは分離されます（PAPER_TRADING_SQLITE_PATH）。実ブローカー接続時は十分に注意してください（KABUSYS_ENV=live）

開発・デバッグ
---------------
- 個別モジュールのユニットテストや一時実行には Python REPL や単体スクリプトで各関数を呼び出してください（duckdb 接続はローカルファイルを指定）
- validate_config.py や config_setup.py を先に実行して設定の齟齬を早期に検出してください
- ログは logs/ 以下に出るため、問題解析時は該当アプリケーション（execution / monitoring 等）のログを参照してください

ライセンス・バージョン
---------------------
- このリポジトリのバージョンはパッケージ定義に従います: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルート（LICENSE 等）を参照してください（本ドキュメントでは未記載）。

お問い合わせ・貢献
-----------------
不具合報告や改善提案は issue を作成してください。プルリクエストは歓迎します。コードスタイルや設計方針に従って変更してください。

以上です。README の追加情報（環境変数の詳細、運用手順、デバッグ事例など）を入れたい場合は利用目的に合わせて追記できます。