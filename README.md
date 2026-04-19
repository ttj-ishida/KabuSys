KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤ライブラリです。  
主な目的は以下のとおりです。

- 日次のファクター計算・リサーチ（DuckDB を使った price/financial データ処理）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- ExecutionEngine（発注エンジン）と Monitoring（監視）コンポーネントの起動スクリプト
- Paper Trading（モックブローカー）を経由した検証用ワークフロー
- ニュース NLP（OpenAI）を用いたセンチメント評価・市場レジーム判定
- 監視・アラート（kill switch / risk monitor / system monitor）機能

バージョン: 0.1.0

主な機能
--------
- 環境設定ウィザード（.env の対話的作成 / 更新）: kabusys.config_setup
- 起動前設定検証 CLI: kabusys.validate_config（--strict オプションあり）
- ExecutionEngine 起動スクリプト: run_execution.py（本番/ペーパートレード分離）
- Monitoring 起動スクリプト: run_monitoring.py（定期ポーリング、監視ログ永続化）
- 監視永続化: SQLite ベースの monitoring_db（system_status / trade_logs / risk_logs / positions / dashboard）
- Paper Trading 検証レポート生成: tools.paper_verification_report
- Portfolio モジュール: 候補選定 / 等重・スコア重み / ポジション数決定 / セクター制約・レジーム乗数
- Research モジュール: momentum / volatility / value / forward returns / IC / 統計サマリー
- AI モジュール: news_nlp（OpenAI を用いた銘柄別ニューススコアリング）、regime_detector（市場レジーム判定）
- ユーティリティ: ログ設定（logging_setup）、プロセス優先度・CPU affinity 設定（process_priority）

前提・依存
----------
最低限の環境例（プロジェクトにより変化します）:

- Python 3.9+（typing, match 等の利用状況に応じて要件を調整してください）
- 必須 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config yaml 検証を行う場合に必要）
- SQLite（Python 標準 sqlite3 を使用）
- ネットワーク接続（kabuステーション API / J-Quants / OpenAI を利用する場合）

セットアップ手順
----------------
1. リポジトリをクローン／配置する

2. 仮想環境を作成して依存をインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使用してください（本リポジトリには含まれていません）。

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 他に LOG_LEVEL, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH 等が設定可能

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合:
     - python -m kabusys.validate_config --strict

5. DB 初期化は起動スクリプトが行います
   - run_execution/run_monitoring が起動時に必要なテーブルを作成します（init_monitoring_db）

環境変数（主要）
----------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- オプション（代表例）:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
  - OPENAI_API_KEY: OpenAI を使う機能で必須
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill flag を自動クリアするか（"1"でクリア）

使い方（よく使うコマンド）
-------------------------
- .env の対話作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine の起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動時にプロセス優先度を "high" に設定します。
    - 停止は data/stop_requested.flag の作成で検知します（スクリプト側で stop を検出）。

- Monitoring の起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き（秒）
  - Monitoring は環境にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを書きます。
  - 停止は data/stop_requested.flag を置くことで検知・終了します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH により既定の DB を指定可能

- AI 系 (ニューススコア・レジーム判定)
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数に引数で渡してください。
  - 関数は kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を直接呼び出して利用できます。

停止・Kill Switch
-----------------
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。
- KillSwitch の評価は MonitoringEngine 側で行われ、閾値超過（例: ドローダウン、ポジション数超過）時に書かれます。
- ExecutionEngine 起動時は KILL_FLAG_CLEAR_ON_START 設定によって kill.flag を起動時に自動削除する設定が可能（デフォルトは 0）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
- logging の設定は kabusys.utils.logging_setup.setup_logging を通じて統一されています。
- コンソールログは stdout に出力されます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主な構成（抜粋）です:

- kabusys/
  - __init__.py                — パッケージ初期化（__version__）
  - config.py                  — 環境変数・設定管理（.env 自動ロード含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前検証 CLI

  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定

  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化 / 永続化クラス
    - system_monitor.py        — システム状態 & データ鮮度チェック
    - trade_monitor.py         — （発注 / 約定）監視ロジック
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書込みロジック
    - alert_manager.py         — アラート送信（LINE など）
    - monitoring_engine.py     — 複数監視を束ねるエンジン

  - execution/                 — 発注エンジン実装（Engine, OrderManager, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算・キャップ・スケーリング
    - risk_adjustment.py       — セクター上限・レジーム乗数

  - research/
    - factor_research.py       — momentum/volatility/value の計算
    - feature_exploration.py   — forward returns / IC / summary

  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA + LLM）

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

補足 / 実装上の注意
-------------------
- Monitoring のデフォルトポーリング間隔は 60 秒（MONITOR_POLL_INTERVAL で変更可）。0 以下は無効としてデフォルトにフォールバックします。
- run_monitoring は「環境に関係なく」本番の sqlite_path を使用して監視ログを書き込みます（意図的な設計）。
- run_execution は KABUSYS_ENV が paper_trading の場合、paper_trading 用 DB を使用して本番 DB と分離します。
- OpenAI 呼び出しはリトライロジック・レスポンスバリデーションを備えていますが、API キーが未設定の場合は ValueError を送出します。
- DuckDB を用いたリサーチ関数は DuckDB 接続を受け取り SQL を実行します。データ投入は別途データパイプラインが必要です（prices_daily / raw_financials / raw_news 等のテーブルを想定）。

ライセンス / コントリビューション
---------------------------------
- 本 README 内ではライセンスは明示していません。実リポジトリでは LICENSE を参照してください。
- バグ報告・改善提案は issue / PR ベースでお願いします。

問い合わせ
---------
- 実装上の疑問や追加ドキュメントが必要な箇所があれば、具体的なファイル名・関数名を指定して質問してください。README やサンプル .env、起動手順の補足を作成します。