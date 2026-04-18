KabuSys — 日本株自動売買システム
=================================

このリポジトリは「KabuSys」と呼ばれる日本株自動売買／リサーチ基盤の一部実装です。  
本 README はコードベース（src/kabusys 以下）の主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
---------------
KabuSys は以下の機能を備えた自動売買／研究プラットフォームのコンポーネント群です（このコードベースはフルスタックの一部）:

- 実行エンジン（ExecutionEngine）と注文管理（発注・リスク管理・照合）
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制限）
- リサーチ：ファクター計算（モメンタム・ボラティリティ・バリュー等）、特徴量探索
- AI モジュール：ニュースを LLM でスコアリング、レジーム判定
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度設定
- ツール：Paper Trading の検証レポート生成など

主な設計方針のポイント
- 本番データとペーパートレードを分離（paper_trading 環境は専用 SQLite を使用）
- ルックアヘッドバイアス回避のため日付/時間の扱いに配慮
- 外部 API（OpenAI 等）呼び出し時はリトライ・フェイルセーフを組み込み
- ロギングは統一的に設定（console + 日次ローテートログ）

機能一覧
---------
- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、環境変数優先）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]
- 実行関連
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - 監視ループ起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による ExecutionEngine 停止（Kill Switch）
  - 監視ログ永続化（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
- ポートフォリオ構築
  - 候補選定、等重配分・スコア加重配分、リスクベースのポジションサイジング
  - セクターキャップ適用、レジーム乗数
- AI
  - ニュース NLP（OpenAI）で銘柄別センチメントを ai_scores に書き込み
  - レジーム判定（ETF MA200 とマクロニュースの LLM スコアを組合せ）
- リサーチ
  - DuckDB を使ったファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・特徴量統計
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------

前提
- Python 3.9+ を想定（duckdb や openai 等の互換性に注意）
- システムにより psutil 等のネイティブ依存があるためビルド環境（pip, C コンパイラ等）を用意してください。

1. リポジトリをクローン
   - 任意の場所にクローンし、ルートを作業ディレクトリとします（プロジェクトルート判定は .git または pyproject.toml を使用します）。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須例（プロジェクトに requirements.txt がある場合はそれを利用してください）:
     - pip install duckdb psutil openai
   - オプション:
     - PyYAML（config/*.yaml の内容検証に使用）: pip install PyYAML

   （注）実際の requirements は本 README の元コードに記載がないため、実行時に不足エラーが出たパッケージを追加してください。

4. 環境変数の設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ...
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の挙動）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - MONITOR_POLL_INTERVAL（監視ループの秒数上書き）
   - 作成後、設定検証を実行:
     - python -m kabusys.validate_config
     - strict モード: python -m kabusys.validate_config --strict

5. データディレクトリ
   - ログ: デフォルト logs/ に書き出されます（setup_logging が作成）
   - DB/フラグ: data/ 配下に監視 DB・kill.flag・pid ファイル等が配置されます。権限やパスを書き換える場合は .env を編集してください。

使い方（主要コマンド）
--------------------

- 設定ウィザード
  - python -m kabusys.config_setup
    - 対話式で .env を生成・更新します。

- 設定検証
  - python -m kabusys.validate_config [--strict]
    - .env と config/*.yaml の存在／妥当性をチェックします。
    - --strict をつけると警告も失敗扱い（exit 1）になります。

- 監視ループ起動（本番的に常駐する監視プロセス）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で設定可能（デフォルト 60）
    - 停止はプロジェクトルート/data/stop_requested.flag の作成で検知して終了します。

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
    - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag の作成や kill.flag による停止処理が組み込まれます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / レジーム判定 / NLP
  - OpenAI API を利用する関数群は OPENAI_API_KEY を環境変数で指定してください。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を DuckDB 接続と target_date を与えて呼ぶ設計です。

ログと監視・フラグ
-----------------
- ログ: kabusys.utils.logging_setup.setup_logging により stdout と logs/<app_name>.log（日次ローテート）が使われます。ログレベルは LOG_LEVEL 環境変数または引数で制御します。
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution でポーリング中に検知して安全に停止します。
  - Kill Switch: KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。KILL_FLAG_CLEAR_ON_START を使って起動時の自動クリア挙動を制御できます（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
-------------------------------

（リポジトリの src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite テーブル定義・永続化層
    - system_monitor.py      — システム状態 / データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — （存在する場合）取引監視ロジック
    - monitoring_engine.py   — 各 Monitor を束ねる
    - kill_switch.py         — kill.flag を管理
    - alert_manager.py       — （アラート送信ロジック、存在すれば）
  - execution/
    - broker_factory.py      — ブローカークライアント生成
    - execution_engine.py    — ExecutionEngine 本体
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
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（LLM + MA200）
  - data/                   — 実行時に生成されるデータ（DB、pid、flag 等）
  - logs/                   — ログファイル（設定により変更可）

注意事項 / ベストプラクティス
----------------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも明記）。
- KABUSYS_ENV を "live" に設定する際は十分に設定を確認してください（validate_config が警告を出します）。
- 本番環境での Kill Switch 設定や KILL_FLAG_CLEAR_ON_START の値は慎重に扱ってください（誤動作で自動クリアすると危険）。
- OpenAI API を利用する機能は API レート制限やコストが発生します。API キー管理とコスト監視を行ってください。
- paper_trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH）。ペーパートレードを行うことで実際の発注を避けられます。

トラブルシューティング
----------------------
- 依存モジュールが足りない / import error が出る場合は不足パッケージ（duckdb, psutil, openai, PyYAML など）をインストールしてください。
- ログファイルが作成されない場合は LOG_DIR / filesystem の書き込み権限を確認してください。失敗するとコンソールのみでログを出力します。
- run_execution / run_monitoring が即終了する場合は data/stop_requested.flag が存在していないか確認してください。

最後に
------
この README はコードベースに含まれる実装（docstring / コメント）に基づいて作成しました。実際の運用では追加のコンフィグレーション、デプロイ周りの仕組み（systemd / supervisor / Docker 等）、さらにテスト・CI/CD を整備することを推奨します。必要であれば、セットアップ用の requirements.txt や Dockerfile、起動スクリプト例も作成できますので、その場合は教えてください。