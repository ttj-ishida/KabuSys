KabuSys
======

概要
--
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリは以下の主要機能を持ち、実運用（live）・ペーパートレード（paper_trading）・開発（development）を切り替えて利用できます。

- 注文実行エンジン（ExecutionEngine）
- 監視・アラート機能（Monitoring）
- ポートフォリオ構築（候補選定・配分・株数決定）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 運用支援ツール（環境設定ウィザード、設定検証、ペーパートレード検証レポート）

主な機能
--
- Execution
  - 本番 / ペーパートレード両対応（KABUSYS_ENV により分岐）
  - ブローカークライアント抽象化（MockBroker を用いた paper_trading）
  - リスク管理（ポジション上限、利用率、ドローダウン等）
  - 注文管理・再突合（reconciler, order_manager 等）
- Monitoring
  - システム状態監視（CPU/メモリ/ディスク、Execution プロセスの存否）
  - 注文滞留・約定異常の検出
  - リスク監視（ドローダウン・ポジション数上限）
  - Kill Switch（所定条件で data/kill.flag を書き込み Execution を停止）
  - LINE へのアラート送信（AlertManager）
- Portfolio
  - 候補選定、等配分 / スコア加重、リスクベース配分
  - セクター上限適用、レジームに応じた乗数処理
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン、IC、統計サマリ等
- AI
  - ニュース記事をまとめて OpenAI に投げ、銘柄毎センチメントを ai_scores に書き込み
  - マクロニュース + ETF MA に基づく日次レジーム判定
- ツール
  - 環境設定ウィザード（.env の対話的生成）
  - 設定検証 CLI（.env と config/*.yaml のチェック）
  - Paper Trading 検証レポート生成

前提 / 依存
--
コード内インポートから確認される主な外部依存：
- Python 3.9+（typing 構文を想定）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- requests（LINE API 用）
- PyYAML（config 検証で存在すれば YAML の内容検証を行うが必須ではない）
- sqlite3（標準ライブラリ）

セットアップ
--
1. リポジトリをクローン
   - git clone ... / または提供されたソースを取得

2. Python 仮想環境の作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests
   - （検証用に PyYAML を入れる場合）pip install pyyaml

4. 環境変数（.env）を準備
   - 対話式ウィザードで作成可能:
       python -m kabusys.config_setup
   - またはリポジトリルートに .env を作成して環境変数を設定する。
   - 自動ロード: プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local は自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数（抜粋・デフォルト）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant|partial|never|reject）デフォルト: instant
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を有効にする場合に設定
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）デフォルト: INFO
- KILL_FLAG_PATH / PID_FILE_PATH 等のファイルパスも Settings から上書き可能

設定の検証
--
- 対話式で .env を作る:
    python -m kabusys.config_setup
- 設定検証（.env と config/*.yaml の存在・基本整合性をチェック）:
    python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

基本的な使い方 / 実行コマンド
--
- ExecutionEngine（発注系）を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に保存されます。live にする場合は設定を十分確認してください。
  - run_execution は data/execution.pid に PID を書き、 data/stop_requested.flag があると起動しない（停止フラグ管理）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）をオーバーライド可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを記録します。

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
      python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。指定がなければ PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を参照。

- AI 機能（プログラム API として利用）
  - ニューススコアリング:
      from kabusys.ai import score_news
      score_news(conn, target_date, api_key=...)
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date, api_key=...)
  - いずれも OpenAI API キー（OPENAI_API_KEY）を要します。

運用上の注意
--
- Paper trading モードを活用して実際の発注を行わずにロジック検証が可能です（KABUSYS_ENV=paper_trading）。
- 本番運用（KABUSYS_ENV=live）の場合は LINE 通知や Kill Switch、KILL_FLAG_CLEAR_ON_START の設定を慎重に確認してください。validate_config の live ガードが参考になります。
- kill.flag（デフォルト data/kill.flag）を書き込むと ExecutionEngine に停止シグナルを送れます。KillSwitch はリスク監視で自動的に書き込むことができます。
- PID ファイル / stop_requested.flag / kill.flag の管理に注意してください（起動スクリプトがこれらを検査／作成／削除します）。

ディレクトリ構成（主要ファイル）
--
以下は src/kabusys 配下の主要モジュール一覧（コードベースに含まれるファイルの抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 # .env 自動読み込み / Settings クラス
  - config_setup.py           # .env 対話ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - execution/                 # 発注関連（order_manager, broker_factory, execution_engine 等）
    - (複数ファイル: order_manager, order_repository, execution_engine, risk_manager, reconciler 等)
  - monitoring/
    - monitoring_db.py
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
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/                      # 実行時に使われるデータディレクトリ（DB, pid, flags 等）

（注）上記は現在提供されている主要ソースの抜粋です。execution 以下の具象実装や broker クライアント等は別ファイル群に実装されています。

開発メモ / デバッグ
--
- ログ出力は標準 logging を使用。LOG_LEVEL で制御。
- Monitoring / Execution は PID ファイルや flag ファイルを介してプロセス間連携するため、 data ディレクトリ配下のファイルを直接操作することで起動・停止を試験できます。
- validate_config と config_setup をまず実行して、.env と config/*.yaml（必要なら）を整えてください。
- DuckDB のスキーマ（prices_daily など）を整備してから research / ai モジュールを実行する必要があります。

ライセンス / バージョン
--
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリルートの LICENSE を参照してください（本 README には含まれません）。

問い合わせ・貢献
--
- バグ報告や機能提案は issue を立ててください。
- 開発に参加する場合はまずローカルで config_setup → validate_config → unit test を順に実行して環境を整えてください。

以上が KabuSys の概要・セットアップ・使い方およびディレクトリ構成の要約です。必要であれば .env のサンプルテンプレートや起動スクリプトの具体的な実行例（systemd ユニット例、docker-compose 例など）を別途作成します。どの情報を詳細化したいか教えてください。