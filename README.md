README — KabuSys (日本株自動売買システム)
=====================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのシステムです。
主要コンポーネントは発注エンジン（ExecutionEngine）、監視プロセス（Monitoring / SystemMonitor）、
ファクター計算・研究モジュール、ニュース NLP（OpenAI）によるセンチメント評価などを含みます。

主な特徴
--------
- 実行環境分離: KABUSYS_ENV により development / paper_trading / live を切替可能
  - paper_trading 時は MockBrokerClient を使用し、paper_trading DB に記録（本番 DB とは分離）
- ExecutionEngine: ブローカー、リスク管理、オーダー管理、再整合（reconciler）を備えた発注実行
- Monitoring: システムリソース監視・データ鮮度チェック・リスク監視・Kill Switch 発動機構
- AI 連携: OpenAI を使ったニュースセンチメント評価（news_nlp）・レジーム判定（regime_detector）
- 研究用モジュール: ファクター計算（momentum, volatility, value）、特徴量解析、IC 計算
- ユーティリティ: ログ設定ユーティリティ、プロセス優先度設定、設定ウィザード・検証 CLI
- ペーパートレード検証レポート生成ツール（tools/paper_verification_report）

前提条件 / 依存関係
------------------
最低限必要なパッケージ（例）:
- Python 3.9+
- duckdb
- openai
- psutil
- PyYAML（config 検証を行う場合に推奨）

インストール例:
- 仮想環境作成:
  python -m venv .venv
  source .venv/bin/activate
- 必要パッケージをインストール:
  pip install duckdb openai psutil PyYAML

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. .env 作成:
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - または手動で .env を作成（.env.example がある場合は参照）
5. 設定検証（起動前に実行推奨）:
   python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     python -m kabusys.validate_config --strict
6. 必要なディレクトリを作成:
   - data/ （実行中に DB・フラグファイル等を格納）
   - logs/ （ログ出力先。自動作成される場合あり）
7. DuckDB / SQLite の DB ファイルは設定に従って指定（デフォルト: data/kabusys.duckdb, data/monitoring.db）

環境変数と重要な設定
--------------------
必須（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（主なもののみ抜粋）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 用）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LOG_LEVEL / LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの注文約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

最小 .env 例:
JQUANTS_REFRESH_TOKEN=your_token
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
OPENAI_API_KEY=your_openai_key  # AI を使わないなら不要

実行方法
--------
- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、
    PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に停止させるには data/stop_requested.flag を作成するとエンジンは安全に停止します。
  - 実行時は data/execution.pid が使用・書き込みされます。

- Monitoring（SystemMonitor 起動）:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
  - 監視は Settings.sqlite_path（本番監視 DB）を使用（環境にかかわらず）
  - data/stop_requested.flag が存在すると監視ループを終了します

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD
    --to YYYY-MM-DD
    --db PATH  （PAPER_TRADING_SQLITE_PATH をオーバーライド）

- AI / 研究機能（ライブラリとして利用）:
  - news_nlp: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research: kabusys.research.calc_momentum / calc_volatility / calc_value など
  これらは DuckDB 接続（duckdb.connect(...)）と target_date（datetime.date）を受け取ります。

停止・Kill Switch
----------------
- run_execution/run_monitoring の停止:
  - data/stop_requested.flag を作成すると両スクリプトは検知してシャットダウンします
- Kill Switch:
  - KillSwitch は監視条件（ドローダウン超過やポジション上限超過）を満たすと
    data/kill.flag（デフォルトパスは Settings.kill_flag_path）を書き込み、
    ExecutionEngine に停止シグナルを送ります。
  - 本番環境では KILL_FLAG_CLEAR_ON_START の自動クリア設定に注意してください（危険）。

ログ
----
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。
- ログレベルは LOG_LEVEL 環境変数か setup_logging の引数で制御します。
- ログのローテーションは日次（30日保持）です。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数/設定読み込みロジック
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor 起動スクリプト

- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- monitoring/
  - monitoring_db.py         — SQLite 永続化層
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

- utils/
  - logging_setup.py         — 統一ログ設定
  - process_priority.py      — プロセス優先度 / CPU affinity

- tools/
  - paper_verification_report.py

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では設定ミスが致命的になり得ます。validate_config の実行と .env の管理に注意してください。
- .env は絶対にリポジトリにコミットしないでください。
- OpenAI API の呼び出しはコストがかかります。API キーの管理と利用頻度に注意してください。
- monitoring は稼働状態の検出や Kill Switch を通じて発注エンジン停止を行いますが、想定外のケースを必ずテストしてください。

開発メモ / 拡張ポイント
---------------------
- position_sizing や risk_adjustment は将来的に銘柄別の lot_size 等をサポートするよう拡張可能です。
- news_nlp と regime_detector は OpenAI SDK のバージョン変化に対して堅牢性を持たせていますが、API 変更には注意。
- DuckDB / SQLite のスキーマ変更は monitoring_db.init_monitoring_db のマイグレーション部分にて処理しています。

ライセンス / 貢献
-----------------
- 本 README はコードベースの抜粋に基づく概要ドキュメントです。貢献や詳細ドキュメントはリポジトリの追加資料（Design doc / PortfolioConstruction.md など）を参照してください。

付録 — よく使うコマンド例
-----------------------
- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config

- 実行エンジン起動（ペーパートレード）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視起動:
  python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。README に示した手順で環境を整え、まずは development / paper_trading モードで動作確認することを推奨します。問題があればエラーログを確認し、validate_config とログ出力を手掛かりにトラブルシュートしてください。