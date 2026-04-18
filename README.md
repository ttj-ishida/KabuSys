README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤ライブラリです。本リポジトリは次のような機能を持つモジュール群を含みます。

- 発注エンジン（ExecutionEngine）と監視（Monitoring）
- ポートフォリオ構築（候補選定、重み付け、株数算出）
- ファクター計算・研究ツール（DuckDB ベース）
- ニュース NLP / 市場レジーム判定（OpenAI を利用するモジュール）
- ペーパートレード用検証レポート生成ツール
- 環境設定ウィザード・設定検証 CLI、ロギング/プロセス優先度ユーティリティ

主な特徴
--------
- モジュール設計により運用用スクリプトと計算ロジックが分離
- DuckDB + SQLite を併用したデータ管理（分析用 / 監視用）
- Paper Trading モードで本番 DB と完全分離（data/paper_trading.db）
- OpenAI を用いたニュースセンチメント（ai.news_nlp）とレジーム判定
- .env ウィザード（config_setup）と起動前チェック（validate_config）で運用ミスを低減

必要な環境（推奨）
-----------------
- Python 3.9+（コードは型注釈等を使用）
- 外部パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイルチェック用、任意）
- SQLite（標準ライブラリに含まれます）

インストール（例）
-----------------
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール（requirements.txt がない場合は個別に）
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml

設定（.env）
-----------
1. 対話式ウィザードで .env を作成/更新
   - python -m kabusys.config_setup
   - ウィザード終了後、.env に保存されます。

2. 必須環境変数（最低限設定必須）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

3. 主な設定項目（デフォルト値は .env の説明や Settings クラス参照）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading モード時）
   - LOG_LEVEL: ログレベル（INFO 等）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
   - PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）

設定の検証
---------
起動前に設定を検証できます。

- 基本チェック:
  - python -m kabusys.validate_config

- 警告を厳格扱いにする（警告があれば exit 1）:
  - python -m kabusys.validate_config --strict

起動と使い方
------------

主要スクリプト
- 監視ループ
  - python -m kabusys.run_monitoring
  - 説明:
    - Monitoring のポーリングループを起動します。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
    - monitoring は実行環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用します。
    - 停止はプロジェクトルート/data/stop_requested.flag ファイルを作成すると検知して終了します。

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 説明:
    - ExecutionEngine を起動します。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せずに終了します。
    - 停止は stop_requested.flag の作成や kill.flag（KILL フラグ）で制御します。
    - 実行中は data/execution.pid に PID が書き込まれます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 説明:
    - paper_trading DB（デフォルト: data/paper_trading.db）を読み、稼働率・約定成功率・レイテンシ等のレポートを標準出力に出力します。

AI / リサーチ系
- ニュースセンチメント（ai.news_nlp.score_news）
  - OpenAI API キーが必要（OPENAI_API_KEY または api_key 引数）。
  - raw_news / news_symbols / ai_scores テーブルと連携しスコアを ai_scores に書き込みます。

- レジーム判定（ai.regime_detector.score_regime）
  - ETF(1321) の MA200 とマクロニュースの LLM センチメントを組み合わせて market_regime テーブルに書き込みます。
  - OpenAI API キーが必要。

運用上のポイント
- ログ
  - デフォルトで logs/ ディレクトリに日次ローテートログ（TimedRotatingFileHandler）を出力します。LOG_DIR 環境変数で変更可。
  - setup_logging() を各スクリプトで呼び出し統一されたログ出力を実現しています。

- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼び出し、実行プロセスの優先度設定を試みます（psutil に依存）。

- Kill Switch / Stop フラグ
  - KillSwitch（data/kill.flag）を用いて ExecutionEngine 停止を行います。KillSwitch は RiskMonitor の結果（ドローダウン超過等）で自動発火することがあります。
  - stop_requested.flag（data/stop_requested.flag）は manual stop を意図したフラグで、run_execution/run_monitoring が検知して安全に終了します。
  - KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合、起動時に既存の kill.flag を自動クリアします（本番では 0 を推奨）。

ディレクトリ構成（概略）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                    -- 環境変数 / Settings 管理
    config_setup.py              -- .env 対話式ウィザード
    validate_config.py           -- 起動前チェック CLI
    run_execution.py             -- ExecutionEngine 起動スクリプト
    run_monitoring.py            -- SystemMonitor 起動スクリプト
    tools/
      paper_verification_report.py
    ai/
      news_nlp.py
      regime_detector.py
    research/
      factor_research.py
      feature_exploration.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      kill_switch.py
      alert_manager.py
    execution/                    -- Execution 関連（broker, engine, order_manager 等）
    data/                         -- データ関連（pipeline, stats 等）
    utils/
      logging_setup.py
      process_priority.py

（注）上は主要ファイルの抜粋です。実コードを参照してさらに詳細な構成を確認してください。

よくある操作例
--------------
- .env を作成して検証する:
  1) python -m kabusys.config_setup
  2) python -m kabusys.validate_config

- ペーパートレード検証レポート（2026-04-01〜2026-04-10）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

- 監視プロセスをデバッグ目的で1回だけ実行:
  - python -c "from kabusys.monitoring.monitoring_engine import MonitoringEngine; print('use in tests')"
  （注）実行には Monitoring の各モニタ初期化が必要です。ユニットテストでは run_once を使って単体テスト可能です。

注意事項 / 運用上のヒント
------------------------
- .env は機密情報を含むため Git にコミットしないでください（config_setup もこの旨を警告します）。
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にしておくことを推奨します。
- OpenAI を利用する機能は API 呼び出しにコストとレイテンシが発生します。API キーとレート制限に注意してください。
- DuckDB / SQLite のパスは .env で調整できます。paper_trading モードでは paper_trading DB を使用して本番 DB と分離してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続する設計です（setup_logging の仕様）。

ライセンスと貢献
----------------
- 本リポジトリのライセンス情報はリポジトリルートにある LICENSE を参照してください（存在しない場合は内部ポリシーに従ってください）。
- バグ報告・機能提案は Issue を立ててください。Pull Request は歓迎します。

補足
----
本 README はコードベースから抽出した設計・使い方の要点をまとめたものです。各機能の詳細なパラメータや内部仕様は、該当するモジュール（例: ai/news_nlp.py、portfolio/position_sizing.py、monitoring/*.py）内のドキュメンテーションコメントを参照してください。必要であれば個別の使い方ドキュメント（API リファレンスや運用手順書）を追加できます。