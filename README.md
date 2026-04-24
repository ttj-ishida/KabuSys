# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
このリポジトリはトレーディング実行・監視・リサーチ・ポートフォリオ構築・AI ベースのニュース解析などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム向けユーティリティ群です。主な目的は以下です。

- 発注エンジン（ExecutionEngine）による注文送信／注文管理
- 監視（Monitoring）機能：システム状態、注文ログ、リスク監視、Kill Switch
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ算出）
- リサーチ（ファクタ計算、フォワードリターン、IC など）
- AI 補助（ニュース NLP によるセンチメント評価、市場レジーム判定）
- ツール群（設定ウィザード、設定検証、ペーパー検証レポート生成）

設計方針の例：
- 本番とペーパートレードを分離（ペーパートレードは専用 SQLite を使用）
- DuckDB を分析用 DB、SQLite を運用ログ／監視用 DB に使用
- .env による設定、CLI ウィザードと検証ツールを提供
- OpenAI を利用した NLP 機能は API キーが必要（フェイルセーフ有）

---

## 主な機能一覧

- Execution
  - ExecutionEngine（実際の／モックのブローカー連携）
  - OrderManager / Reconciler / RiskManager（発注管理・再整合・リスク管理）
  - Paper trading 用に MockBrokerClient と専用 DB を利用

- Monitoring
  - SystemMonitor：CPU／メモリ／ディスク、データ鮮度、Execution プロセス監視
  - TradeMonitor：注文の滞留・異常を検知
  - RiskMonitor：ドローダウン・ポジション上限を監視・アラート記録
  - MonitoringEngine：各モニタ統合、Kill Switch 判定、アラート発行
  - Monitoring DB：SQLite に監視ログ・注文ログ・リスクログを永続化

- Portfolio（純粋関数）
  - 候補選定（スコア順）
  - 重み計算（等分・スコア加重）
  - セクター上限適用
  - ポジションサイズ計算（ロット丸め、利用可能現金でスケーリング）

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン計算、IC（スピアマン）算出、ファクター統計

- AI
  - news_nlp: OpenAI でニュースをスコアリングし ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースを合成して市場レジーム判定

- ユーティリティ
  - 設定ウィザード（config_setup）
  - 設定検証（validate_config）
  - ログ設定ユーティリティ（logging_setup）
  - プロセス優先度／CPU affinity 設定ユーティリティ（process_priority）
  - 各種 CLI ツール（paper_verification_report など）

---

## セットアップ手順

前提：
- Python 3.10+（型ヒントで Union 表記等を使用）
- SQLite は標準ライブラリで利用可能
- 必要な外部パッケージ（例）

推奨インストール（venv を利用）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai
   - PyYAML を導入すると config/*.yaml の検証が可能：
     - pip install pyyaml

※ requirements.txt がある場合はそれを利用してください（本サンプルでは同梱されていません）。

3. プロジェクトルートに .env を作成
   - `python -m kabusys.config_setup` を実行すると対話式ウィザードで .env を生成できます。
   - もしくは手動で以下最小 .env を作成（実運用では秘匿情報を設定）:

例（.env 最小例）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

4. DB / ディレクトリの準備
   - ログディレクトリ（デフォルト: logs/）および data/ を作成（多くは自動作成されますが権限に注意）
   - ペーパートレード用 DB を使う場合は data/paper_trading.db を作成（空ファイルで問題ありません）

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数が設定済みか、主要ファイルパスの親ディレクトリが存在するか等をチェックします。

---

## 環境変数（主なもの）

必須（実行機能による）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション／設定:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: Execution は MockBrokerClient を使用し paper_sqlite_path を使用
  - live: 本番モード（注意）
- DUCKDB_PATH: 分析用 DB（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 実行時に kill.flag を自動クリアするか（0/1）

ファイル・フラグ:
- data/kill.flag: Kill Switch 発動時に書き込まれるファイル（ExecutionEngine は存在を検出して停止）
- data/stop_requested.flag: run_execution / run_monitoring 停止用フラグ（スクリプトは検出して終了）
- data/execution.pid: ExecutionEngine の PID ファイル（起動時に作成）

---

## 使い方（主なコマンド）

- 設定ウィザード（初期 .env を対話式作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告も FAIL とする）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパーデータベースに記録します（本番 DB と分離）。
    - 停止は data/stop_requested.flag の作成で指示可能。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を参照（環境にかかわらず）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI スコアリング／レジーム判定（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、内部で ai_scores / market_regime テーブルへ書き込みます。
  - API キーは引数または環境変数 OPENAI_API_KEY で指定

ログ出力:
- デフォルトは stdout と日次ローテートされたファイル（logs/<app_name>.log）
- ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します

停止 / Kill Switch:
- RiskMonitor 等が条件を満たすと data/kill.flag が書かれ、ExecutionEngine は起動中にこれを検出して停止します
- KillSwitch は冪等的で、既に flag がある場合は再書き込みしません

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (想定)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py (想定)
    - stats.py (想定)
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はリポジトリに含まれる公開された主要モジュールの一覧です。一部ファイル名はコードからの抽出に基づきます）

---

## 開発時の注意点 / 補足

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブルとカラムを作成／追加します（簡易マイグレーション対応あり）。

- ペーパートレード分離
  - KABUSYS_ENV=paper_trading の場合、Execution は paper_sqlite_path を使用し本番 DB と完全分離します。

- OpenAI API 使用
  - API 呼び出しにはネットワークエラーやレート制限に対するリトライ実装が組み込まれていますが、API キー・使用量に注意してください。

- ローカル開発
  - .env は絶対に Git にコミットしないでください（config_setup も README 内にそれを注意書きしています）。
  - validate_config により起動前に主要な設定不備を検出できます。

---

この README はコードの概観をまとめたものです。各モジュールの詳細な使い方や API（例えば ExecutionEngine の設定オプション、OrderRepository の API、RiskManager のパラメータ等）は各モジュールの docstring を参照してください。必要であれば、各コンポーネント別の詳しいドキュメントも作成します。