README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのサンプル実装です。
主な目的は以下です。

- 自動発注エンジン（ExecutionEngine）と監視（Monitoring）機能の提供
- ポートフォリオ構築・ポジションサイジング・リスク制御のライブラリ
- DuckDB を用いたリサーチ／ファクター計算ツール
- OpenAI を利用したニュース NLP / レジーム判定モジュール（AI 部分は外部 API に依存）
- ペーパートレード用の完全分離 DB と検証レポート生成ツール

本リポジトリは、起動スクリプト、設定管理、監視ロジック、取引ログ永続化、研究用モジュール等で構成されています。

主な機能一覧
-------------
- Execution
  - ExecutionEngine を起動して発注ワークフローを実行
  - paper_trading モードでは MockBrokerClient を使い、専用 SQLite（data/paper_trading.db）に記録
  - PID ファイル / stop フラグでの制御
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - システム稼働率やデータ鮮度、滞留注文・約定異常・ドローダウン監視
  - Kill Switch による停止フラグ（data/kill.flag）生成と通知連携
- 設定管理
  - .env の自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式ウィザード（kabusys.config_setup）で .env 作成・更新
  - 設定検証 CLI（kabusys.validate_config）で起動前チェック
- 研究・分析
  - DuckDB を用いたファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、統計サマリ
- AI（オプション）
  - ニュースのセンチメント評価（OpenAI を利用）
  - マーケットレジーム判定（ETF MA とマクロニュースの LLM 評価の合成）
- ユーティリティ
  - ロギング一元化（logs/<app>.log、日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提（推奨）
-------------
- Python 3.10+
- 必要パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（設定 YAML の厳密チェックをする場合）
- 実行ユーザーにログ・data ディレクトリ作成権限

セットアップ手順
----------------
1. リポジトリを取得して開発環境に入る
   - git clone ... && cd <repo>
2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - あるいは最低限: pip install duckdb psutil
   - OpenAI 機能を使う場合: pip install openai
   - PyYAML が必要なら: pip install pyyaml
   （requirements.txt がある場合はそれを利用してください）
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI を使う場合）
     - LOG_LEVEL（デフォルト INFO）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict
6. 初回の DB 初期化は、run_execution / run_monitoring 実行時に自動で行われます（monitoring DB テーブル作成等）。

使い方（スクリプト起動例）
--------------------------
- ExecutionEngine を起動
  - 本番（KABUSYS_ENV を live に設定している場合は注意して起動）:
    - python -m kabusys.run_execution
  - ペーパートレード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合、MockBrokerClient が使われ、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で調整:
    - MONITOR_POLL_INTERVAL=<秒> python -m kabusys.run_monitoring
    - デフォルトは 60 秒。0 以下や不正な値は無視されて 60 秒にフォールバックします。
  - 監視は MonitoringEngine を内部で用い、MonitoringDB（SQLite）と DuckDB に接続します。
  - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使う設計です（監視履歴は共通 DB）。
- 停止制御
  - data/stop_requested.flag（プロジェクトルートの data 配下）を作成すると run_monitoring/run_execution のループは検知して安全に停止します。
  - Kill Switch（kill.flag）:
    - KillSwitch により data/kill.flag が書き込まれると ExecutionEngine に停止シグナルとして扱われます。
    - Settings.kill_flag_clear_on_start が 1 に設定されていると起動時に自動で kill.flag をクリアします（本番では 0 推奨）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH（指定がなければ env / デフォルト）

AI 機能の注意点
----------------
- OpenAI API キーが必要（OPENAI_API_KEY / 引数で指定可能）。
- API 呼び出しはネットワーク障害やレート制限に対してリトライ実装がありますが、失敗時はフェイルセーフ（0.0等）で継続します。
- テスト時は _call_openai_api をモックできます（unit test 用 hook が用意されています）。
- AI 機能は production で使う場合コストやレスポンスの安定性に注意してください。

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒。デフォルト 60）
- OPENAI_API_KEY: OpenAI 利用時に必要
- KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）

ディレクトリ構成
----------------
以下は主なファイル・ディレクトリの抜粋（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env 自動ロード、Settings クラス
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前の設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - portfolio/
    - __init__.py
    - portfolio_builder.py     — 候補選定・等分/スコア加重配分
    - position_sizing.py       — 株数決定・投下資金スケーリング・単元丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py        — SQLite を用いた監視データ永続化
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム状態・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch 実装（kill.flag 書き込み）
    - ...（TradeMonitor / AlertManager 等が想定される）
  - execution/
    - execution_engine.py     — 実行エンジン（主ループ）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - research/
    - __init__.py
    - factor_research.py      — momentum / volatility / value 等のファクター
    - feature_exploration.py  — forward returns / IC / summary 等
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し・集約ロジック）
    - regime_detector.py      — レジーム判定
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py

ログ・データ配置（デフォルト）
------------------------------
- logs/<app_name>.log — 日次ローテーション（デフォルト 30 日保持）
  - app_name は run_monitoring/run_execution 等で指定 (例: "execution", "monitoring")
- data/
  - monitoring.db (default: SQLITE_PATH)
  - paper_trading.db (default: PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (default: DUCKDB_PATH)
  - execution.pid (PID ファイル)
  - kill.flag / stop_requested.flag — 停止フラグ

開発者向けメモ / 備考
--------------------
- 設定の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。テストで自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring は監視用テーブル（monitoring_db.init_monitoring_db）を起動時に確実に作成します（冪等）。
- Paper Trading は本番 DB と分離されるよう設計されています（設定により変更可）。
- OpenAI 周りはネットワーク例外・429 等に対する再試行ロジックを実装していますが、商用運用時はレート・コスト管理に注意してください。
- 重要な安全策（Kill Switch、KILL_FLAG_CLEAR_ON_START 等）に関する警告は validate_config で検出されます。本番環境では validate_config の実行を推奨します。

よく使うコマンドまとめ
--------------------
- .env 作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 報告:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 責任範囲
--------------------
本コードはサンプル実装です。実運用での使用は自己責任です。取引・資金管理に関する実運用は慎重に評価し、必要な安全対策・テストを十分に行ってください。

お問い合わせ / 変更
------------------
実装に関する質問や改良提案はリポジトリの issue を利用してください。