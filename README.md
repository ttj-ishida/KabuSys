README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を収めた Python コードベースです。本リポジトリは以下のような機能群を提供します。

- 注文実行エンジン（ExecutionEngine） — 本番／ペーパートレード両対応
- 監視（Monitoring） — システム状態、注文の滞留・約定異常、リスク監視、Kill Switch
- ポートフォリオ構築ユーティリティ — 候補選定、重み計算、ポジションサイズ算出
- リサーチ／ファクター計算 — モメンタム、ボラティリティ、バリュー等
- AI 補助モジュール — ニュースの NLP スコア化／市場レジーム判定（OpenAI を利用）
- 各種ユーティリティ・CLI — .env ウィザード、設定検証、ペーパートレード検証レポート など

主な機能一覧
-------------
- 環境設定ウィザード（kabusys.config_setup）
  - 対話形式で .env を生成・更新します。
- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml の存在・基本妥当性チェックを行います（--strict モードあり）。
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV に応じて実環境／ペーパートレードを切替え。ペーパートレード時は MockBrokerClient を使用しデータは data/paper_trading.db に保存。
  - 停止フラグ（data/stop_requested.flag）や Kill Switch（data/kill.flag）に対応。
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可（デフォルト 60 秒）。
  - 監視ログは sqlite（Settings.sqlite_path）に永続化。Monitoring は環境に関わらず本番 sqlite_path を使用します。
- モニタリングサブコンポーネント
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、データ鮮度をチェック
  - TradeMonitor: 注文滞留、約定価格の異常を検出
  - RiskMonitor: ドローダウン・ポジション上限を監視しアラート/Kill Switch へ連携
  - MonitoringDB: SQLite を用いた永続層（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオユーティリティ（kabusys.portfolio）
  - 候補選定、等重/スコア重み付け、セクターキャップ適用、ポジションサイズ計算（単元丸め・リスク制約対応）
- リサーチ（kabusys.research）
  - DuckDB を用いたファクター計算、将来リターン、IC 評価、統計サマリー
- AI 機能（kabusys.ai）
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に保存
  - regime_detector: ETF の MA とマクロニュースの LLM センチメントを合成して市場レジームを判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを出力

前提・依存関係
---------------
- 推奨 Python バージョン: 3.10+
- 必須/推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（config YAML の検証を行う場合）
- その他: SQLite は標準ライブラリで利用

セットアップ手順
---------------
1. リポジトリをクローンしワークディレクトリへ移動
   - git clone ... && cd <repo>

2. Python 仮想環境を準備・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成。
     - 最低限必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - OpenAI を使う場合: OPENAI_API_KEY を設定
     - 例（.env）:
       JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
       KABU_API_PASSWORD=your_kabu_api_password_here
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 問題があれば表示されます。--strict を付けると警告も失敗扱いになります。

使い方（主要コマンド）
--------------------
- ExecutionEngine 起動（本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替）
  - 環境例（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行時の挙動:
    - PaperTrading: settings.is_paper=True → MockBrokerClient を使用、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - Live/Development: settings.sqlite_path（data/monitoring.db 等）を使用
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid に PID を書きます。停止は stop flag（data/stop_requested.flag）作成で行います

- Monitoring 起動
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（本番 sqlite_path）を使ってログを書きます（環境に関わらず本番 DB を参照する点に注意）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）

- AI 機能（スクリプトから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection（DuckDBPyConnection）
    - target_date: date オブジェクト
    - api_key: OpenAI API key（未指定なら環境変数 OPENAI_API_KEY を参照）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止・Kill 機構
----------------
- run_execution/run_monitoring はプロジェクトルートの data/stop_requested.flag をチェックして終了します（run_execution は起動時にもチェック）。
- Kill Switch は data/kill.flag を書き込むことで ExecutionEngine に止めるシグナルを送ります（KillSwitch クラスを通じて監視側で書き込まれます）。
- PID 管理:
  - 実行エンジンは data/execution.pid に PID を書きます。
  - SystemMonitor は PID ファイルの stale を検知すると削除・ログ記録します。

設定・環境変数（主なもの）
-------------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意・デフォルト有:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - OPENAI_API_KEY: OpenAI 利用時に必要
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
  - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings で上書き可能

ディレクトリ構成（主要ファイルと説明）
------------------------------------
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス。環境変数読み込み・.env 自動ロード・検証ロジックの一部。
  - config_setup.py
    - .env を対話式に生成/更新するウィザード。
  - validate_config.py
    - 起動前の設定検証 CLI。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト（本番/ペーパー切替）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
  - tools/
    - paper_verification_report.py
      - ペーパートレード DB の検証レポート生成。
  - ai/
    - news_nlp.py
      - raw_news を OpenAI で評価して ai_scores に書き込む。バッチ処理・リトライ・バリデーションあり。
    - regime_detector.py
      - マクロ記事 + ETF MA を使って市場レジーム（bull/neutral/bear）を判定し保存。
  - monitoring/
    - monitoring_db.py
      - SQLite に対する永続化層（テーブル作成・CRUD ヘルパー）。
    - system_monitor.py
      - CPU/メモリ/ディスク、データ鮮度、プロセスチェック。
    - trade_monitor.py
      - 注文滞留・約定異常検出。
    - risk_monitor.py
      - ドローダウン・ポジション上限監視。
    - kill_switch.py
      - kill.flag の書き込み/削除ロジック。
    - monitoring_engine.py
      - 複数モニタを束ねてポーリングしアラートや Kill Switch を実行。
    - alert_manager.py
      - （アラート送信の抽象化。ファイルは途中で切れている可能性があります）
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py 等
      - 実際の注文管理／ブローカ抽象化／リスク管理ロジック（実装詳細は各ファイル参照）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
      - 候補選定、重み付け、ポジションサイズ算出、セクター上限対応、レジーム乗数
  - research/
    - factor_research.py
    - feature_exploration.py
      - DuckDB を用いたファクター・将来リターン・IC・統計サマリー等
  - data/ （実行時に使用されることが多い想定）
    - monitoring.db（デフォルト SQLITE_PATH）
    - paper_trading.db（ペーパートレード用）
    - kabusys.duckdb（デフォルト DUCKDB_PATH）
    - kill.flag / stop_requested.flag / execution.pid などのフラグ・PID ファイル

注意事項・運用メモ
-----------------
- 監視（Monitoring）は監視用 DB（Settings.sqlite_path）にログを書きます。run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用するので、本番データと分離したい場合は DB パスを適切に設定してください。
- ペーパートレードは paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）で分離されます。ペーパートレード環境では run_execution は MockBroker を利用し、本番 DB を汚しません。
- OpenAI API を使う機能は API キーが必須です。API 呼び出し時のエラーはリトライやフォールバック実装がありますが、キーが無いと実行できません。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- Python の型表記や Union 型（|）を使用しているため Python 3.10 以上を推奨します。

問い合せ・貢献
---------------
- ドキュメントやコードの改善、バグ報告、機能追加提案は Pull Request / Issue を通じてお願いします。
- 各モジュールには docstring と詳細な注釈が付されています。まずはそれらを参照の上で変更してください。

以上が README の概要です。必要であれば、実行例（具体的なコマンド群）、.env.example のテンプレート、CI / デプロイ手順（systemd / supervisor 用ユニット例）などを追加で作成できます。どの内容を優先して追加しますか？