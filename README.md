README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。
本リポジトリには以下の要素が含まれます（抜粋）:

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視ループ（Monitoring）
- 環境設定ウィザード・設定検証ツール
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ）
- リサーチ用ファクター計算・特徴量解析
- ニュース NLP / レジーム判定（OpenAI を利用するモジュール）
- 監視 DB（SQLite）アクセス層・監視ロジック・アラート連携補助
- 開発 / 運用向けユーティリティ（ログ設定・プロセス優先度設定 等）
- ペーパートレード検証レポート生成スクリプト

特徴
----
- 環境分離: KABUSYS_ENV による dev / paper_trading / live 切替
  - paper_trading モードでは専用の SQLite（PAPER_TRADING_SQLITE_PATH）を利用し本番 DB と完全分離
- モジュール化:
  - portfolio: 候補選定・重み付け・ポジションサイズ計算（純粋関数）
  - research: DuckDB を用いたファクター計算・特徴量解析
  - ai: ニュースセンチメント（OpenAI）・市場レジーム判定（LLM を利用）
  - monitoring: システム・注文・リスク監視、Kill Switch 実装
- 運用支援:
  - .env ウィザード（config_setup.py）、設定検証 CLI（validate_config.py）
  - 日次ローテートファイルログとコンソール出力を統一する logging_setup
  - プロセス優先度設定や CPU affinity 設定ユーティリティ
- ペーパートレード検証ツール（レポート生成）は standalone 実行可能

動作要件（推奨）
----------------
- Python 3.10+
- 主要依存パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
  - PyYAML（config/*.yaml の構文チェックを行う場合、オプション）
- SQLite は標準ライブラリで利用

セットアップ手順
---------------
1. リポジトリをクローンする
   - 例: git clone ... && cd repo

2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - AI 機能を使わない場合は openai を省略しても動作するモジュール部分があります。

4. .env の初期作成
   - 対話式ウィザードを実行して .env を作成
     - python -m kabusys.config_setup
   - ウィザードでの主な必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV（development / paper_trading / live）
   - デフォルトの DB パス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）になる:
     - python -m kabusys.validate_config --strict

基本的な使い方
--------------
- ExecutionEngine（トレード実行ループ）起動
  - ライブ/ペーパーの切替は KABUSYS_ENV 環境変数で制御
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止
    - 実行中に stop フラグが立ったらスレッドを停止する
    - プロセス優先度を "high" に設定しようとします（管理権限が必要になる場合があります）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを書きます
  - 停止は data/stop_requested.flag を作成することで行います

- .env 自動ロード
  - config.py はプロジェクトルート（.git または pyproject.toml）を検出すると .env と .env.local を自動で読み込みます
  - 自動ロードを無効化する場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- ログ
  - デフォルトは logs/ ディレクトリに日次ローテートログ（例: logs/execution.log, logs/monitoring.log）
  - ログレベルは LOG_LEVEL 環境変数あるいは .env で制御
  - ログディレクトリは LOG_DIR 環境変数で変更可能

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力は標準出力にレポートを表示（稼働率、注文成功率、レイテンシ等の判定）

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API を利用するため、OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時に渡す必要があります
  - news_nlp.score_news / regime_detector.score_regime を使うことで ai_scores / market_regime テーブルへの書き込みが可能
  - API 呼び出しはリトライやフェイルセーフ処理が組み込まれています

運用・停止に関する補足
--------------------
- Kill Switch:
  - kabusys.monitoring.kill_switch は Settings.kill_flag_path（デフォルト data/kill.flag）にフラグファイルを書き込んで ExecutionEngine に停止シグナルを送る仕組みです
  - KillSwitch.evaluate はドローダウンやポジション上限超過を検出したときにフラグを作成します
  - Execution 側は stop フラグ（run_execution 内では data/stop_requested.flag）を監視して停止処理を行います
- 停止フラグファイル:
  - run_monitoring と run_execution の両方で data/stop_requested.flag を監視している箇所があります（停止要件に合わせた運用をしてください）
- プロセス優先度:
  - 実行時に set_process_priority("high") を呼び出します。権限によっては設定に失敗する（警告）ことがあります

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト
- config.py                — 環境変数 / 設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- tools/
  - paper_verification_report.py  — ペーパートレード検証レポート
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）
  - regime_detector.py      — 市場レジーム判定（OpenAI）
- portfolio/
  - portfolio_builder.py    — 候補選定・重み算出
  - position_sizing.py      — 発注株数決定
  - risk_adjustment.py      — セクター上限・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（momentum/value/volatility）
  - feature_exploration.py  — 将来リターン・IC・統計サマリ
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（テーブル作成・CRUD）
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        — （注文監視 - 実装参照）
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - kill_switch.py          — Kill Switch 実装
  - alert_manager.py        — （アラート送信管理 - 実装参照）
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity
- execution/                — Execution パッケージ（エンジン、OrderManager など）
- data/                     — 実行時に使われるデータファイル（DB / pid / flag）

主要な環境変数（代表）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI を使う機能で必要（news_nlp, regime_detector 等）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START — 本番で Kill flag を自動的にクリアするか（0/1、注意）

開発上の注意
------------
- DuckDB のクエリは prices_daily / raw_financials / raw_news 等のテーブルを参照します。ローカルでのリサーチ実行には適切な DuckDB スキーマとデータの準備が必要です。
- AI 機能は外部 API（OpenAI）に依存します。API レスポンスの不安定さを考慮したリトライやパース保護が実装されていますが、コストやレート制限に注意してください。
- .env を絶対にリポジトリにコミットしないでください（config_setup も README に明示しているとおり）。
- Python バージョンは 3.10 以上を推奨（| 型ヒント等で 3.10 構文を使用）。

トラブルシューティング
---------------------
- .env 自動ロードが期待どおりに動かない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- ログファイルが作成できない場合は書き込み権限と LOG_DIR を確認。ログディレクトリ作成に失敗するとコンソール出力のみになります（警告が出ます）。
- psutil によるプロセス優先度設定は権限不足で失敗することがあります（警告）。その場合も動作は継続します。

ライセンスとバージョン
---------------------
パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
ライセンス情報は本リポジトリに含まれる LICENSE ファイルを参照してください（なければ別途設定してください）。

以上。README の内容に不明点があれば、利用したいユースケース（ローカルデータでのリサーチ、ペーパートレード運用、本番接続など）を教えてください。具体的な例や起動手順をより詳細に案内します。