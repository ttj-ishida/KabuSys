README
======

概要
----
KabuSys は日本株の自動売買および研究用ユーティリティ群を含む Python パッケージです。本リポジトリは以下の主要機能を提供します。

- 実行エンジン（ExecutionEngine）と監視（Monitoring）コンポーネントの起動スクリプト
- 環境設定ウィザードと設定検証ツール
- ペーパートレード用の分離 DB と検証レポート生成
- ポートフォリオ構築・ポジションサイズ計算・リスク調整ロジック（純粋関数）
- DuckDB を使ったファクター計算・リサーチツール
- ニュースを用いた LLM ベースのセンチメントスコアリング（OpenAI 使用、オプション）
- ログ設定・プロセス優先度設定などのユーティリティ

特徴一覧
--------
主な機能と特徴：

- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用して paper_trading DB に記録）
  - run_monitoring.py：SystemMonitor をポーリングして監視ログを記録（MONITOR_POLL_INTERVAL により間隔を変更可能）
- 環境設定 / 検証
  - config_setup.py：対話式ウィザードで .env を作成・更新
  - validate_config.py：.env と config/*.yaml の簡易検証
- モニタリング
  - system_monitor, trade_monitor, risk_monitor, KillSwitch, MonitoringEngine による総合監視・アラート連携
  - 監視ログは SQLite（デフォルト: data/monitoring.db）へ永続化
- ペーパートレード検証レポート
  - tools/paper_verification_report.py：ペーパートレード DB を解析して PASS/FAIL 判定を出力
- リサーチ
  - research パッケージ：DuckDB 上の prices_daily/raw_financials を用いたファクター計算（Momentum/Volatility/Value）や IC 計算
- AI
  - ai.news_nlp / ai.regime_detector：OpenAI を使ったニュースセンチメントスコアリング／市場レジーム判定（API キー必須）
- ポートフォリオロジック
  - portfolio パッケージ：候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数など
- ユーティリティ
  - utils.logging_setup：統一的なログ設定（コンソール + 日次ローテートファイル）
  - utils.process_priority：クロスプラットフォームでプロセス優先度・CPU affinity を設定

セットアップ手順
----------------

1. リポジトリをクローン
   - リポジトリルートに pyproject.toml あるいは .git が存在する構成を想定しています。

2. Python 環境の準備（推奨）
   - Python 3.9+ を利用してください（ソース内記載の型注釈に基づく）。
   - 仮想環境の作成・有効化例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必須パッケージをインストール
   - main に必要な代表パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config で YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt は本コードベースに付属していません。上記は最低限の推奨パッケージです。

4. ディレクトリ作成
   - デフォルトで使用されるディレクトリ（存在しない場合は自動作成される箇所もありますが事前に作成しておくと安心です）:
     - data/ （SQLite / pid / flag 等）
     - logs/ （ログ出力先）
   - 例:
     - mkdir -p data logs

5. .env の作成
   - python -m kabusys.config_setup を実行すると対話式で .env を生成できます。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う設定（デフォルト値があるものの例）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO / DEBUG / ...
     - OPENAI_API_KEY: （AI モジュールを使うなら必須）

使い方
------

基本的なコマンド例:

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定のバリデーション
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（フォアグラウンド）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB（デフォルト: data/paper_trading.db）を使用します。本番設定 KABUSYS_ENV=live の場合は実際に発注が行われますので注意してください。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔 (秒) を環境変数でオーバーライド:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path（SQLITE_PATH, デフォルト data/monitoring.db）を使用します。

- 停止 / Kill Switch
  - kill.flag（デフォルト: data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送れます（KillSwitch が有効な場合）。
  - stop 请求フラグファイル（run_execution/run_monitoring で使用）:
    - data/stop_requested.flag（起動済みプロセスが存在すればこれを検出して終了します）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

主な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、デフォルト 60）
- PAPER_FILL_MODE（ペーパートレードの約定挙動: instant | partial | never | reject）

注意点・トラブルシューティング
- process_priority（高優先度設定）は OS 権限が必要な場合があります。psutil の実行が拒否されるケースでは警告が出ますが続行します。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（ログフォルダのパーミッションを確認してください）。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合、起動時に自動作成される場面もありますが、事前に作成しておくと安全です。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しは再試行ロジックを含みますが、キー未設定だと ValueError を送出します。
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を含む）を起点に .env と .env.local を自動で読み込みます。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------

以下は主要ファイル・モジュールの一覧（src/kabusys 以下）です。各ファイルに目的のコメントが含まれています。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定の読み込みロジック（.env 自動ロード含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動エントリ
  - run_monitoring.py        — SystemMonitor ポーリング起動エントリ
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）を使った銘柄別センチメント
    - regime_detector.py     — マクロ + ETF MA で市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ + DB ラッパー
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （コード内参照）注文関連の監視ロジック
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理・評価
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信）※実装参照
  - execution/
    - broker_factory.py      — ブローカークライアント生成
    - execution_engine.py    — ExecutionEngine（発注ループ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数決定・集約上限処理
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - utils/
    - __init__.py
    - logging_setup.py       — 統一ログ設定（stdout + 日次ローテート）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

開発者向けメモ
---------------
- 設計は「DB を渡して純粋関数で計算する」方針が多く採られており、テスト容易性が考慮されています（例: DuckDB 接続を引数に渡す等）。
- AI 関連関数は API 呼び出し部をテスト時に差し替えられるように設計されています（モック可能）。
- monitoring_db.py は DB マイグレーション（既存カラムチェック）を含み、冪等でテーブルを作成します。
- run_execution/run_monitoring はそれぞれ data/stop_requested.flag を検出して安全に終了します。

ライセンス・注意
----------------
- .env にはシークレット情報（API キー等）を含みます。絶対に Git 等へコミットしないでください。
- 本システムは自動売買を目的としているため、KABUSYS_ENV=live を用いる際は十分なテストと検証を行ってください。

以上が本コードベースの概要と利用手順です。追加で README に載せたい具体的なコマンド例や、各モジュールの詳細説明が必要であれば教えてください。