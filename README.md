# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・リサーチ・監視を行うためのモジュール群を提供します。  
本READMEはコードベース（src/kabusys 以下）をもとに、目的・機能・セットアップ・利用方法・ディレクトリ構成を日本語でまとめたものです。

注意: 実際にマーケット発注を行う機能を含みます。設定や本番環境での利用は十分に注意して行ってください。

---

## 概要

KabuSys は以下の主要コンポーネントを持つ統合システムです。

- ExecutionEngine（発注エンジン）: 実際の発注ロジック、リスク管理、リコンシリエーション等を担います。paper_trading（ペーパートレード）モードをサポート。
- Monitoring（監視）: システム状態、注文ログ、リスク指標を定期的にチェックしアラートや Kill Switch の発動などを行います。
- Portfolio（ポートフォリオ構築）: 候補選定、重み付け、ポジションサイジング、セクター制約などの純粋関数群。
- Research（リサーチ）: DuckDB 上の時系列データからファクター計算・特徴量解析を行うモジュール。
- AI（ニュース NLP / レジーム判定）: OpenAI を用いたニュースセンチメント算出やマクロセンチメント合成による市場レジーム判定。
- Tools（ユーティリティ）: ペーパートレード検証レポートなどの CLI ツール群。
- Utilities: ログ設定、プロセス優先度設定、設定読み込みなど共通ユーティリティ。

---

## 主な機能一覧

- 環境設定ウィザード（config_setup.py）: .env を対話式に作成・更新
- 設定検証 CLI（validate_config.py）: 起動前に必要環境変数・設定ファイルを検証
- ExecutionEngine:
  - 本番 / ペーパートレード分離（paper_trading 用専用 SQLite）
  - BrokerClientFactory によるブローカークライアント抽象化
  - リスク制御（RiskManager）, OrderManager, Reconciler 等の統合
- Monitoring:
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - TradeMonitor, RiskMonitor: 注文の滞留やドローダウンなどを検出
  - KillSwitch: 指定条件で data/kill.flag を書き、ExecutionEngine を停止
  - MonitoringEngine: 各モニタを束ねたポーリング実行
  - 永続ストレージ: SQLite（monitoring.db）ベースの monitoring_db モジュール
- Portfolio:
  - 候補選定（select_candidates）、等重/スコア重み（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ適用、レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- Research:
  - Momentum / Volatility / Value のファクター計算（DuckDB 使用）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ等
- AI:
  - news_nlp.score_news: raw_news を集約して OpenAI API により銘柄別センチメントを算出、ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF MA とマクロニュースセンチメントを合成して market_regime に記録
- Tools:
  - paper_verification_report: ペーパートレード DB から稼働率・約定率・レイテンシ等の検証レポートを生成

---

## 要件（推奨）

- Python 3.10 以上（型注釈に | 演算子、list[str] 等を使用）
- 必要なパッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - optional: PyYAML（config の YAML 検証で使用）
- SQLite（Python 標準ライブラリに含まれるため別途不要）

実行環境によっては追加のパッケージやシステムライブラリが必要となる場合があります。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - （YAML 検証を使う場合）pip install pyyaml

   ※ requirements.txt がある場合はそれを利用してください（本リポジトリに同梱されていない場合もあるため手動列挙しています）。

4. .env を作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で .env を作成

5. 設定を検証
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict

6. データディレクトリとファイル
   - デフォルトでは data ディレクトリ下に DB や PID/flag ファイルを作成します（例: data/monitoring.db, data/kabusys.duckdb）。
   - ログはデフォルト logs/ に出力されます。

---

## 主要環境変数（主なもの）

必須（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

運用（代表例）:
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading の場合、Execution は MockBrokerClient を使用し data/paper_trading.db に記録します
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒, run_monitoring で使用。デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH など（Settings で参照）

詳細は kabusys.config.Settings のプロパティを参照してください。

---

## 使い方

### .env 設定
- 対話式で .env を作る:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いにできます

### 実行（Production / Dev）
- ExecutionEngine を起動:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading にするとペーパートレード用 DB に記録され、本番 DB と分離されます。
    - 実行は data/stop_requested.flag により停止要求を監視します（停止フラグ検知でエンジンを停止）。
    - 起動時に PID ファイル（data/execution.pid など）を作成します。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用して監視ログを記録します（環境に依らず）。
    - 停止は data/stop_requested.flag を作成すると監視ループが終了します。

- Kill Switch / フラグ操作:
  - KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止を要求します。
  - ExecutionEngine 側では起動時に kill.flag をクリアする設定が可能（KILL_FLAG_CLEAR_ON_START=1、ただし本番では推奨しません）。

### Tools
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを直接指定できます（環境変数 PAPER_TRADING_SQLITE_PATH も利用可）。

### ライブラリ的利用（スクリプトではなく関数を呼ぶ）
- AI スコアリング（プログラムから呼ぶ例）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

- レジームスコア:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

- Research（ファクター計算）:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - calc_momentum(duckdb_conn, target_date)

- Portfolio 関数（純粋関数群）:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

---

## ログと運用ファイル

- ログ:
  - デフォルトは logs/ ディレクトリにアプリケーション別（execution.log, monitoring.log 等）で日次ローテーションされます。
  - setup_logging(app_name="...") でカスタマイズ可能。

- データ:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper_trading): data/paper_trading.db（paper_trading 時）
  - フラグ/PID:
    - data/stop_requested.flag: run_* スクリプトが監視する停止要求用フラグ
    - data/kill.flag: KillSwitch が書く停止用フラグ
    - data/execution.pid: ExecutionEngine の PID

---

## 開発者向けメモ / よくある操作

- 自動環境読み込み:
  - プロジェクトルートにある .env / .env.local は自動的に読み込まれます。不要であれば環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- 設定ファイルの YAML 検証:
  - validate_config は PyYAML がインストールされている場合、 config/*.yaml をパースして検証します。
- プロセス優先度:
  - run_* スクリプト起動時に set_process_priority("high") を呼び出して優先度を上げる処理が組み込まれています（psutil に依存、権限や OS により失敗することがあります）。
- テスト実行:
  - 各モジュールは純粋関数（portfolio や research 等）を多く含むためユニットテストが書きやすい設計です。API 呼び出し部分はモックしやすく実装されています（例: news_nlp の _call_openai_api をパッチする）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                # 環境変数読み込み・Settings
- config_setup.py          # .env 対話ウィザード
- validate_config.py       # 設定検証 CLI
- run_execution.py         # ExecutionEngine 起動スクリプト
- run_monitoring.py        # Monitoring 起動スクリプト

- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
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

- data/                    # （実行時に生成される）DB・PID・flag 等
- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py
  - process_priority.py

（上記は主要ファイルの抜粋です。実際のリポジトリで詳細をご確認ください。）

---

## 備考・運用上の注意

- 本番（KABUSYS_ENV=live）運用時は環境変数やキー管理、Kill Switch の設定（KILL_FLAG_CLEAR_ON_START を 0 にする等）を慎重に行ってください。
- OpenAI API を用いるモジュールは API キーと利用料が必要です。API 呼び出しは失敗耐性（リトライ・フォールバック）を備えていますが、運用方針を確認してください。
- DuckDB / SQLite スキーマは init_monitoring_db 等で初期化・マイグレーション処理を行いますが、バックアップやスキーマ変更時の運用手順を整備してください。

---

この README はコードベースの主要箇所を要約したものです。各モジュールの詳細な挙動やパラメータは該当ソースコード（src/kabusys 以下）やドキュメント（存在する場合）を参照してください。仕様変更や追加機能があれば README も随時更新してください。