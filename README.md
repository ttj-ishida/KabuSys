KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム（バックエンド・ライブラリ群）です。  
主な目的は以下です。

- 戦略・ポートフォリオ構築（ファクター計算・ポジションサイズ算出）
- 注文発行の実行エンジン（本番 / ペーパートレード切替）
- システム監視・リスク管理（Kill Switch、アラート）
- 研究用ユーティリティ（ファクター研究、特徴量探索）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- ペーパートレード検証レポート生成ツール

主な特徴
--------
- 環境切替: KABUSYS_ENV により development / paper_trading / live を切替可能
- Paper Trading は本番 DB と完全分離（data/paper_trading.db がデフォルト）
- 監視コンポーネントは SQLite（monitoring.db）と DuckDB（分析用 DB）を併用
- ニュース NLP・レジーム判定は OpenAI（gpt-4o-mini）によるセンチメント評価に対応
- フェイルセーフ設計: API エラー時はフォールバック動作（例: macro_sentiment=0）で継続
- CLI ツール: .env 作成ウィザード、設定検証、ペーパートレード検証レポート等

必要条件（依存）
----------------
以下は本リポジトリから読み取れる主な依存ライブラリです。実行環境に応じて適切にインストールしてください。

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config 検証で YAML のパースを行う場合に任意で必要）
- sqlite3（標準ライブラリ）

セットアップ手順
----------------
1. リポジトリをクローン / 配布パッケージを展開する。

2. Python 仮想環境を作成して依存をインストールする（例）:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそれを使ってください）

3. .env の作成（対話式ウィザード）:
   - python -m kabusys.config_setup
   これによりプロジェクトルートに .env を作成できます（Git に絶対コミットしないでください）。

4. 設定検証:
   - python -m kabusys.validate_config
   --strict を付けると警告も失敗として扱います:
   - python -m kabusys.validate_config --strict

5. DuckDB / SQLite の初期化は各スクリプト起動時に自動で行われます（必要なテーブルが無ければ作成されます）。

環境変数（主要）
----------------
必須（実行に必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY: OpenAI 呼び出しに必要（news_nlp / regime_detector）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効。注意: 本番では危険）

（validate_config.py / config.py によりより詳細な確認が行われます）

実行・使い方
------------

主なエントリポイント（スクリプト / CLI）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
    - 実行中は data/execution.pid に PID を書き、停止は data/stop_requested.flag を作ることで行えます。

- 監視ポーリング起動（SystemMonitor 単体）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（本番監視 DB）を常に使用します（環境に依らず本番 sqlite_path を参照）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を設定

プログラム的な利用例（ライブラリ関数）
- AI ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

- 研究用関数:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - calc_momentum(duckdb_conn, date(2026,4,1))

注意点 / 運用メモ
----------------
- Kill Switch / 停止フラグ:
  - KillSwitch は data/kill.flag に理由を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - run_execution は起動時に stop flag（data/stop_requested.flag）を確認し、存在する場合は起動しません。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で使うのは危険（自動で Kill Flag を消してしまうため）。

- DB 分離:
  - 監視系（monitoring）は常に sqlite_path（本番監視 DB）を使用します。
  - ペーパートレードは paper_sqlite_path を使用して本番データと完全分離されます。

- OpenAI 関連:
  - news_nlp / regime_detector は OPENAI_API_KEY が必要です。キー未設定時は関数が例外を投げます。
  - API 呼び出しはリトライやフォールバック処理を備えていますが、過度に大量呼び出しするとレート制限に掛かる可能性があります。

- プロセス優先度:
  - run_execution および run_monitoring は起動直後に set_process_priority("high") を実行してプロセス優先度を上げようとします（psutil を使用）。権限不足等で失敗することがありますが、警告を出して継続します。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 配下の主要モジュールとファイルです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
    - config.py                       — 環境変数 / Settings 管理
    - validate_config.py              — 設定検証 CLI
    - config_setup.py                 — .env 対話式ウィザード
    - tools/
      - paper_verification_report.py  — Paper Trading 検証レポート
    - ai/
      - news_nlp.py                   — ニュース NLP（OpenAI）
      - regime_detector.py            — 市場レジーム判定（OpenAI + MA）
      - __init__.py
    - research/
      - factor_research.py            — ファクター計算（momentum/value/volatility）
      - feature_exploration.py        — 将来リターン計算・IC 等
      - __init__.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - monitoring/
      - monitoring_db.py              — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py               — （未表示：アラート送信ロジック）
    - execution/                       — 発注関連（OrderManager 等、ここでは一部）
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - utils/
      - process_priority.py
    - data/                            — 実行時に利用されるデータディレクトリ（DB, PID, flags など）
      - monitoring.db (デフォルト)
      - kabusys.duckdb (デフォルト)
      - paper_trading.db (ペーパートレード用)

ドキュメント / 参照
-----------------
- 各モジュールの docstring に詳細な挙動や設計方針が記載されています。実装を確認する際は該当ファイルの先頭 docstring を参照してください。
- .env.example（プロジェクトに存在する場合）を参照して環境変数を準備してください。

トラブルシューティング
---------------------
- 設定検証でエラーが出る場合は validate_config の出力を確認し、必要な環境変数や config/*.yaml の有無を確認してください。
- OpenAI 周りで JSON パースエラーが頻発する場合は API レスポンスをログで確認し、プロンプトやモデルの変更を検討してください。
- プロセス優先度設定で AccessDenied が出る場合は権限（root や適切な権限）で実行するか、設定を無効にして運用してください。

貢献 / ライセンス
-----------------
この README はコードベースから抽出した情報に基づく簡易ドキュメントです。実際の運用ルール・ライセンス情報はプロジェクトルートのドキュメント（LICENSE / CONTRIBUTING など）を参照してください。

おわりに
--------
必要であれば、README に含める具体的なコマンドの例や systemd / supervisor 用の起動スクリプト例、CI 設定、テストの実行方法などを追加します。どの情報を優先して追加したいか教えてください。