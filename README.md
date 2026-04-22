# KabuSys

日本株向け自動売買システムのライブラリ兼実行スクリプト群です。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI 補助（ニュースセンチメント・レジーム判定）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- 発注エンジン（実取引 / ペーパートレード） — run_execution.py
- 監視プロセス（プロセス生存・資源使用率・データ鮮度・リスク監視） — run_monitoring.py, MonitoringEngine
- ポートフォリオ選定・重み付け・ポジションサイジング（純粋関数として実装）
- リサーチ用ファクター計算（DuckDB に対する SQL と Python の組合せ）
- AI を用いたニュースセンチメント評価および市場レジーム判定（OpenAI API）
- 設定ウィザード（.env 作成）・設定検証 CLI・紙上検証レポート生成ツール

設計上の特徴:
- 環境変数ベースの設定（.env 自動ロードあり）
- 本番・ペーパートレード DB の分離
- フラグファイルによる外部からの停止命令（kill.flag / stop_requested.flag 等）
- ログは stdout と日次ローテーションファイルに出力

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化（実口座 / モック切替）
  - リスク管理（max_position_pct, max_utilization 等）
  - 注文管理・照合（OrderManager, Reconciler, OrderRepository）
- Monitoring
  - SystemMonitor（CPU/メモリ/Disk、データ鮮度、PID監視）
  - TradeMonitor（滞留注文・約定異常などの検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に合致した場合 data/kill.flag を書き込み停止指示）
  - MonitoringEngine（各種モニタを束ねてポーリング）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクターキャップ適用・レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計サマリ
- AI
  - ニュース NLP（OpenAI でセンチメントを算出して ai_scores に書き込み）
  - 市場レジーム判定（ETF MA200 乖離 + マクロセンチメント）
- ツール類
  - .env ウィザード（python -m kabusys.config_setup）
  - 設定検証（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## 要件（主な依存）

- Python 3.9+
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時。必須ではない）
- SQLite（組み込み）
- OpenAI を使う場合は API キー（環境変数 OPENAI_API_KEY）

（プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは必要に応じて pip install duckdb psutil openai pyyaml

3. .env の初期作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - J-Quants リフレッシュトークン、kabuAPI パスワードなどを入力
   - 生成された .env は Git にコミットしないでください（秘密情報を含むため）

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. データディレクトリ作成（自動的に作られますが手動で作成しておくと良い）
   - mkdir -p data logs

---

## 主要な環境変数（抜粋とデフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject） デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） デフォルト: INFO
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使うとき必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） デフォルト: 60

監視・制御用ファイル:
- data/execution.pid: ExecutionEngine の PID（実行時に使用）
- data/kill.flag: KillSwitch が書き込む停止フラグ
- data/stop_requested.flag: run_monitoring/run_execution が監視する停止フラグ（外部からの即時停止用）

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動: KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。本番/ペーパーで DB は分離されます。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番 sqlite_path を監視用 DB として使用します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

- AI ニューススコア/レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY が必要（もしくは引数で渡す）

- カスタム監視の単体実行（テスト用）
  - MonitoringEngine をプログラムから組み立てて run_once() を呼ぶことで一回だけ実行可能

---

## 実行制御（Kill Switch / Stop）

- run_execution.py / run_monitoring.py はプロジェクトの data/stop_requested.flag を監視します。ファイルが存在すると安全に停止します。
- KillSwitch は RiskMonitor の結果などを基に data/kill.flag を書き込みます。ExecutionEngine は起動時に kill.flag を確認したり、実行中に kill.flag の存在で停止することができます（設定に依存）。
- ExecutionEngine は起動時に PID ファイル（data/execution.pid）を使用します。

---

## ログ

- ログは標準出力（stdout）とファイルに出力されます。ログファイルはデフォルトで logs/<app_name>.log に日次ローテート（30日保持）されます。
- setup_logging(app_name="execution") を利用して統一的に設定されます。

---

## データベース

- DuckDB: 分析用時系列データ（prices_daily など）、パブリックリサーチ機能は DuckDB 接続を受け取る
  - デフォルトパス: data/kabusys.duckdb
- SQLite: 監視ログ・トレードログ（monitoring.db）およびペーパートレード専用 DB（paper_trading.db）
  - 監視 DB スキーマは monitoring_db.init_monitoring_db により自動生成・マイグレーションされます

---

## ライブラリ的利用

KabuSys は純粋関数・モジュールを多数提供しています。例:

- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- リサーチ
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- AI
  - from kabusys.ai import score_news

多くの関数は DuckDB 接続や簡潔な引数を受け取り、副作用を持たない実装が意識されています（ユニットテストが容易）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・ディレクトリの概観（src/kabusys 下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - data/ （実行時に利用される。DB/flag/pid 等）
  - logs/ （ログ出力先）

---

## 注意点 / 運用上のヒント

- KABUSYS_ENV を live にする際は設定や LINE 通知周りの有無を慎重に確認してください（validate_config に live 向けの追加チェックあり）。
- run_monitoring や run_execution は stop flag（data/stop_requested.flag）で安全終了できます。手動で削除/作成して制御してください。
- ペーパートレード時は PAPER_TRADING_SQLITE_PATH に別 DB を使うため、本番データと混ざりません。
- OpenAI を使う機能は外部 API に依存します。API キーやレートリミット、レスポンス不備には注意して下さい。API 呼び出しはリトライロジックを持ちますが、失敗時はフェイルセーフ（0.0 等）で続行する設計です。
- ログディレクトリの作成に失敗した場合はファイル出力が無効化され stdout のみになります（warning が出ます）。

---

## 貢献 / テスト

- 新しい機能を追加する際はユニットテストを追加してください。多くの関数は副作用が少なく単体テスト可能です（AI 呼び出しはモック推奨）。
- .env に秘密情報を入れたままコミットしないでください。

---

必要ならば README に載せるコマンド例や環境変数一覧をさらに詳しく追記します。どの部分を拡張したいか教えてください。