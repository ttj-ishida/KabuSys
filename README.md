KabuSys
======

日本株向けの自動売買システム用ライブラリ／起動スクリプト群です。  
本リポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのモジュールを含み、コマンドラインから起動・設定ウィザード・検証・レポート生成が行えます。

主な目的
- 日次マーケットデータを用いたファクター計算・シグナル生成（Research）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- 発注実行エンジン（本番・ペーパー切替）
- 実行・発注の監視と Kill Switch（閾値超過で ExecutionEngine 停止）
- ニュースを用いた LLM ベースのセンチメント評価（OpenAI 経由）
- ペーパートレード検証レポート生成ツール

機能一覧
- config_setup.py：対話式で .env を生成・更新するウィザード
- validate_config.py：環境変数・config/*.yaml の起動前チェック（--strict オプションあり）
- run_execution.py：ExecutionEngine を起動（KABUSYS_ENV によりペーパー／本番切替）
- run_monitoring.py：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定）
- monitoring：MonitoringDB、SystemMonitor、RiskMonitor、TradeMonitor、KillSwitch、MonitoringEngine、アラート連携など
- portfolio：候補選定、重み計算、セクター制約、ポジションサイズ算出（純粋関数群）
- research：ファクター計算（momentum, volatility, value 等）・特徴量探索（IC, forward returns 等）
- ai：news_nlp（OpenAI でニュースをスコアリング）、regime_detector（MA + LLM で市場レジーム判定）
- tools.paper_verification_report：ペーパートレード DB から検証レポートを出力

前提・依存（主なもの）
- Python 標準の sqlite3（組み込み）
- duckdb
- psutil
- openai（AI モジュールを使用する場合）
- （任意）PyYAML：validate_config で config/*.yaml の検証を行う場合

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして作業ディレクトリへ
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt がある場合はそれを使用）
   - pip install duckdb psutil openai
   - （検証用）pip install pyyaml
   ※ 実行環境に合わせてバージョン固定してください。
4. .env を作成
   - 対話式で作る場合:
     - python -m kabusys.config_setup
   - 手動作成の場合は .env.example を参考に以下最低限の環境変数を設定：
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=（AI 機能を使う場合）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  （KABUSYS_ENV=paper_trading の場合）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict
6. 初回起動前に data/ ディレクトリなど必要なディレクトリが自動作成されます（ログ・DB も同様）。
7. ログは既定で logs/<app_name>.log（TimedRotatingFileHandler 日次回転、30日保存）と標準出力に出力されます。

主要な使い方（コマンド）
- 環境ウィザード（.env の作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine を起動（本番 or ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 備考: KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag（このファイルが存在するとループを終了します）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- ライブラリ呼び出し例（Python スクリプト内）
  - from kabusys.research import calc_momentum
  - from kabusys.ai import score_news
  - from kabusys.portfolio import calc_position_sizes

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - paper_trading: 発注は MockBroker によりペーパーで動作（DB は PAPER_TRADING_SQLITE_PATH）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1。production では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動読み込みを無効化

Kill Switch / 停止フラグ
- 実行エンジン停止シグナルは data/kill.flag を作成することで送ります（KillSwitch が書き込み）。
- 監視ループの即時停止には data/stop_requested.flag を作成します（run_monitoring/run_execution はこのファイルを検知して安全終了します）。
- ExecutionEngine は起動時に kill.flag をクリアするオプション（KILL_FLAG_CLEAR_ON_START=1）がありますが、本番では 0 を推奨します。

ログと DB（既定値）
- ログ: logs/<app_name>.log（stdout も出力）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db

開発者向けメモ
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある .env / .env.local を起動時に自動で読み込みます。
  - テストなどで自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config.py は .env および config/*.yaml の欠落・不整合を検出します。PyYAML がインストールされていると YAML の構文検査も行います。
- OpenAI 呼び出しはネットワーク／429／5xx に対してリトライ処理が組み込まれています（news_nlp、regime_detector）。
- logging 設定は kabusys.utils.logging_setup.setup_logging で統一しており、起動スクリプトはこれを最初に呼びます。
- process priority/CPU affinity：kabusy.utils.process_priority で Windows/Linux の差分を吸収して優先度設定します（権限不足時は警告で続行）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — Settings クラス（環境変数読み込み・検証・デフォルト）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・スケールダウン・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value ファクター計算
    - feature_exploration.py — forward returns / IC / summary utilities
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マーケットレジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py — SQLite 永続層（テーブル作成・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — Monitor を束ねるループ
    - trade_monitor.py — （存在する想定の）発注関係監視ロジック
    - alert_manager.py — （通知管理）
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

運用上の注意
- 本番（KABUSYS_ENV=live）では設定（LINE 通知設定や kill flag の挙動）を必ず確認してください。validate_config で本番向けの警告を出します。
- .env は機密情報を含むため Git にコミットしないでください。
- OpenAI を用いる機能は API 利用料が発生します。API キーの管理と呼び出し頻度に注意してください。
- DB マイグレーションは init_monitoring_db 等で一部自動対応しますが、バックアップ・移行手順は必ず確立してください。
- run_execution/run_monitoring はデーモン管理（systemd / supervisor / Docker 等）下で起動することを想定しています。ログ・PID ファイル・停止フラグの取り扱いを運用ドキュメントに反映してください。

ライセンス・バージョン
- パッケージバージョンは kabusys.__version__ に定義されています（現状 0.1.0）。
- ライセンス情報はリポジトリの LICENSE を参照してください（本 README には含めていません）。

問題報告・拡張
- 不具合や改善提案は Issue を立ててください。外部 API のエラー処理やデータ不足ケースに対するフォールバックは継続して改善する余地があります。

以上がこのコードベースの概要と基本的な使い方です。必要なら「セットアップ手順の詳細（systemd ユニット例、Dockerfile、CI 用のテスト方法）」や「各モジュールの API 仕様（関数シグニチャ）」「運用ガイド（ログローテーション・バックアップ）」を追記します。どのドキュメントを先に充実させたいか教えてください。