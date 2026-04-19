README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。本リポジトリは以下の主要機能を含みます。

- 発注・実行エンジン（ExecutionEngine） — 本番 / ペーパートレード対応
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算・特徴量解析（DuckDB 経由）
- AI ベースのニュース分析（OpenAI を利用したセンチメントスコアリング）
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）
- 統一的なログ設定、プロセス優先度設定ユーティリティ

特徴
----
主な特徴（抜粋）:

- 本番 / ペーパーの DB 分離（PAPER_TRADING 時は data/paper_trading.db を使用）
- 監視データは SQLite（data/monitoring.db）に永続化、DuckDB は分析用
- Kill Switch により重大リスク（大幅ドローダウン等）で実行エンジンを停止可能
- OpenAI（gpt-4o-mini）を用いたニュース NLP と市場レジーム判定（API キー必須）
- 設定ウィザードと検証 CLI により起動前チェックを容易に実施可能
- ログは stdout + 日次ローテートファイル出力（logs/*.log）

前提条件
----
- Python 3.10+（型ヒントに union 型等を使用）
- DuckDB（python duckdb パッケージ）
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config の YAML 検証を行う場合）
- （任意）その他ライブラリは requirements.txt を用意している場合はそちらを参照

インストール（開発用）
----
1. リポジトリをクローン
2. 仮想環境を作成してアクティベート
3. 必要なライブラリをインストール
   - 例: pip install -r requirements.txt
   - ない場合は最低限: pip install duckdb psutil openai

環境設定 (.env)
----
プロジェクトルートに .env を配置することで環境変数を簡単に管理できます。自動ロード機能が有効な場合、.env / .env.local が起動時に読み込まれます（無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

推奨フロー:
1. ウィザードで初期 .env を作成:
   python -m kabusys.config_setup
2. 設定を検証:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

主要な環境変数（必須・代表）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う場合（news_nlp / regime_detector）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（PAPER_TRADING 時）
- LOG_LEVEL / LOG_DIR — ログ設定
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

デフォルトファイル・フラグ
- data/monitoring.db — 監視ログ（SQLite）
- data/paper_trading.db — ペーパートレード DB（PAPER_TRADING）
- data/execution.pid — 実行エンジンの PID ファイル（ExecutionEngine が使用）
- data/stop_requested.flag — run_* スクリプトの停止要求フラグ
- data/kill.flag — Kill Switch による停止フラグ（ExecutionEngine 側で監視）

セットアップ手順（例）
----
1. 仮想環境を用意
   python -m venv .venv
   source .venv/bin/activate

2. 依存関係をインストール
   pip install duckdb psutil openai pyyaml

3. .env を作成
   python -m kabusys.config_setup

4. 設定を検証（推奨）
   python -m kabusys.validate_config
   （--strict を付けると警告もエラー扱い）

使い方
----
起動スクリプト（主な CLI）
- 実行エンジン起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します。

- 監視ループ起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト: 60）。
  - 監視は常に本番の sqlite_path を参照します（環境にかかわらず）。

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config [--strict]

ツール
- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を使用

AI 機能
- kabusys.ai.score_news / regime_detector は OpenAI API キー（OPENAI_API_KEY）が必要です。
- score_news: news_nlp.score_news(conn, target_date, api_key=None)
- score_regime: ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ
----
ロギングは kabusys.utils.logging_setup.setup_logging で統一されます。標準出力（stdout）と日次ローテーションされるファイル（logs/<app_name>.log）へ出力されます。ログレベルは LOG_LEVEL 環境変数で制御できます。

停止・Kill Switch
----
- 実行停止: data/stop_requested.flag（run_* スクリプトはこのファイル存在をチェックして終了）
- Kill Switch: 異常（ドローダウン超過やポジション上限超過）を検出すると data/kill.flag を生成して ExecutionEngine 停止をトリガーします。KILL_FLAG_CLEAR_ON_START により起動時に自動クリアする設定もあります（本番では推奨しません）。

開発・テストのヒント
- .env の自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- AI 呼び出し部はテストで _call_openai_api をパッチしてモック可能
- DuckDB 接続を渡す設計なのでローカルでダミーデータを用意してユニットテストを作成しやすい

ディレクトリ構成
----
以下は主要なファイル／ディレクトリ（src/kabusys 以下）の概観です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数および .env 自動読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/               — 発注・実行関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

付記
----
- データベースやログのデフォルトパスは project root 配下の data/ および logs/ ですが、環境変数で上書き可能です。
- 本リポジトリのコードは外部 API（kabuステーション / J-Quants / OpenAI）へアクセスする部分を含むため、本番運用前に設定検証・十分なテストを行ってください。
- .env やシークレットは決してバージョン管理（Git）にコミットしないでください。

問題・貢献
----
不具合報告や改善提案は Issue を作成してください。プルリクエスト歓迎です。README に記載した手順で動作しない場合は、実行ログと再現手順を添えて報告してください。