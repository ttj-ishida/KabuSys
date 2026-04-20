KabuSys
=======

日本株向け自動売買フレームワーク（モジュール群）
バッチ/常時監視・発注・リスク管理・ポートフォリオ構築・リサーチ・AI（ニュースNLP / レジーム判定）などを含むライブラリ／実行スクリプト群です。

プロジェクト概要
---------------
KabuSys は日本株自動売買システムのコア機能群をモジュール化したコードベースです。主な役割は次のとおりです。

- ExecutionEngine（発注エンジン）：ブローカークライアント経由で注文を管理・送出
- Monitoring（監視）：システム状態・注文状況・リスクを定期チェックしアラート・Kill Switch を管理
- Portfolio（ポートフォリオ構築）：銘柄選定・重み付け・株数算出
- Research（リサーチ）：ファクター計算・特徴量解析
- AI：ニュースのセンチメント評価（OpenAI を利用）や市場レジーム判定
- Tools：ペーパートレード検証レポート生成などのユーティリティ
- 設定ユーティリティ：.env のウィザード生成と起動前検証 CLI

機能一覧
--------
主要機能（抜粋）:

- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に作成
- 起動前設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数、DBパス、config/*.yaml の存在や YAML パース（PyYAML があれば）を確認
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し paper_trading 用 DB に分離
  - PID ファイル / 停止フラグ監視対応
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - システム/トレード/リスクの各モニタをポーリングして DB に永続化・アラートトリガ
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト: 60 秒）
  - 監視は環境に関わらず production の sqlite_path を使用（監視 DB は共有）
- Kill Switch（data/kill.flag）による ExecutionEngine 停止シグナルの生成
- Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）
- ニュース NLP（OpenAI）での銘柄毎センチメント算出と ai_scores への書き込み
- 市場レジーム判定（ETF + マクロニュースを LLM と組み合わせて daily 判定）
- ポートフォリオ構築（候補選定、等重/スコア重み、リスク調整、株数算出）
- ログ設定ユーティリティ（console + 日次ローテートファイル）

セットアップ手順
----------------
1. Python 環境を準備
   - 依存ライブラリの例: duckdb, psutil, openai, PyYAML（任意; validate_config の YAML 検証で使用）
   - requirements.txt がある場合はそれに従ってインストールしてください（例: pip install -r requirements.txt）。

2. プロジェクトルートに移動して .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - ウィザードで生成された .env は絶対に Git にコミットしないでください。

3. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     python -m kabusys.validate_config --strict

4. DB の初期化
   - run_execution/run_monitoring 実行時に必要なテーブルは自動作成（init_monitoring_db）されます。
   - Paper Trading モードでは paper_trading 用 SQLite（既定: data/paper_trading.db）を使用します。

5. OpenAI を利用する機能を使う場合
   - 環境変数 OPENAI_API_KEY を設定してください（ai.news_nlp、ai.regime_detector が利用）。
   - API キーは .env または環境変数で設定可能。

使い方（実行例）
----------------
- 実行エンジン（ExecutionEngine）起動:
  - 本番/開発/ペーパートレードは KABUSYS_ENV で切り替え
  - 例（通常起動）:
    KABUSYS_ENV=development python -m kabusys.run_execution
  - Paper Trading:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    （この場合、MockBrokerClient を使用し、データは data/paper_trading.db に記録されます）

- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使い、環境に依存せず本番パスを参照します。

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

重要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード。allowed: development, paper_trading, live（デフォルト: development）
  - paper_trading のときは発注はモックかつ専用 DB に分離
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード ("instant" | "partial" | "never" | "reject")（デフォルト: "instant"）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイルの出力先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動でクリアするか（"1" で有効、デフォルト "0" 推奨）
- KILL_FLAG_PATH, PID_FILE_PATH: 各種ファイルパスは Settings で上書き可能

停止フラグ / PID / Kill Switch の挙動
------------------------------------
- 停止要求 (停止フラグ)：
  - プロセスの停止は data/stop_requested.flag（run_monitoring/run_execution が参照する）や data/kill.flag（KillSwitch が生成）などのフラグファイルで制御します。
- PID ファイル:
  - ExecutionEngine は起動時に PID ファイルを作成（設定でパスを指定可能）。
- KillSwitch:
  - RiskMonitor の判定に基づき kill.flag を書き込み、ExecutionEngine の停止トリガになります。

ログ
----
- 共通のロギング設定ユーティリティを提供（kabusys.utils.logging_setup.setup_logging）
  - コンソール stdout と日次ローテートファイル（logs/<app_name>.log）を併用
  - デフォルト保有世代: 30 日

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     — 市場レジーム判定（ETF + マクロニュース）
    - monitoring/
      - monitoring_db.py       — SQLite 監視 DB 層
      - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
      - system_monitor.py      — システム状態 / データ鮮度監視
      - trade_monitor.py       — （※実装ファイルあり）注文監視
      - risk_monitor.py        — ドローダウン / ポジション上限監視
      - kill_switch.py         — kill.flag 書き込み
      - alert_manager.py       — （※アラート送信管理）
    - execution/
      - execution_engine.py    — ExecutionEngine（本体）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (上記と重複)
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

開発メモ / 注意事項
------------------
- .env は秘密情報（API キー等）を含むため絶対に VCS にコミットしないでください。
- validate_config で PyYAML がインストールされていないと config/*.yaml の内容検証はスキップされます（警告）。
- run_monitoring は MONITOR_POLL_INTERVAL の値が不正（0以下や非数）の場合、デフォルト 60 秒にフォールバックします。
- run_execution は paper_trading モード時に paper_trading 用 DB を使用し、本番 DB と分離します。
- OpenAI 呼び出し部分はネットワーク・レート制限等を想定してリトライとフォールバックロジックを持っていますが、API キーや利用量には注意してください。
- process_priority を起動時に "high" に設定しますが、OS 権限や環境によっては設定に失敗する場合があります（警告ログが出ます）。

ライセンス・バージョン
--------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現行: 0.1.0）。

お問い合わせ
------------
コードベースに関する質問や機能追加の要望はリポジトリの Issue / PR を通してください。

以上がこのリポジトリの主要な README 相当の説明です。必要に応じて実際の環境や要件に合わせて手順（依存パッケージ名や Python バージョン、requirements.txt の整備等）を追記してください。