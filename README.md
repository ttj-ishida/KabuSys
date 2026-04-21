# KabuSys

日本株自動売買システムのコアライブラリ（README）。この README はリポジトリ内のスクリプト・モジュール群に基づいて作成しています。

主な内容：
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト／ツールの実行方法）
- ディレクトリ構成（主要ファイル一覧）
- 重要な環境変数・挙動メモ

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量探索）、AI を使ったニュース NLP／レジーム判定ユーティリティなど、トレーディングシステムを構成するコンポーネントを含みます。

設計方針の要点：
- 実行エンジンと監視を分離（stop/kill フラグで制御）
- DuckDB（分析）と SQLite（監視・履歴）を併用
- Paper trading（ペーパートレード）と Live（本番）を環境変数で切替
- OpenAI を用いたニュース解析／レジーム判定は外部 API に依存（APIキー必要）
- ロギングは統一的に設定（コンソール + 日次ローテーションファイル）

---

## 機能一覧

- 実行（Execution）
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（paper_trading では MockBrokerClient）
  - リスク管理、注文管理、リコンサイル（Reconciler）など

- 監視（Monitoring）
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
  - Kill Switch による ExecutionEngine 停止シグナル出力（data/kill.flag）

- ポートフォリオ構築（portfolio）
  - 候補抽出、重み計算（等分・スコア加重）
  - 単元丸めやリスクベースのポジションサイズ計算
  - セクター上限やレジーム乗数の適用

- リサーチ（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）などの特徴量解析

- AI（ai）
  - ニュース NLP スコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI API（gpt-4o-mini 想定）を利用（APIキー必須）

- ユーティリティ
  - 設定管理（.env 自動読み込み、Settings クラス）
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ログ設定ユーティリティ（logging_setup）
  - プロセス優先度・CPU アフィニティ設定（process_priority）
  - Paper Trading 向け検証レポート生成ツール（tools/paper_verification_report）

---

## セットアップ手順

前提
- Python 3.10+（typing 構文を想定）
- システムにより追加のバイナリライブラリや権限が必要（psutil 等）

1. リポジトリをクローン／展開
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - 代表的な依存（プロジェクトの requirements.txt がある場合はそちらを使用してください）:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証で YAML 検証を行う場合）
   例:
     - pip install duckdb psutil openai pyyaml
4. 初期設定（.env）の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参考にして、環境変数を設定してください。
   - 自動ロード: 実行時、プロジェクトルート（.git または pyproject.toml を探す）で .env / .env.local を自動的に読み込みます。
     - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 重大な欠落がある場合は exit code が 1 を返します。--strict を指定すると警告も FAIL 扱いになります。

6. 初回起動前に data ディレクトリ等が必要な場合は作成されるか確認してください。ログディレクトリは `logs/` がデフォルトです。

---

## 主要な環境変数

必須（少なくとも実行する機能に応じて設定）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

代表的なオプション・挙動制御
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading: run_execution は専用の paper_trading DB を使用
  - live: 本番動作。十分注意して設定してください（LINE 通知等の設定確認推奨）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒）。デフォルト 60
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

注意点:
- Monitoring は KABUSYS_ENV に関わらず sqlite_path（本番用監視 DB）を使用します。
- Execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用し、本番 DB と分離します。

---

## 使い方（主要スクリプト）

全てリポジトリルートで実行する想定です（.env 自動ロードが有効な場合）。

1. 環境設定ウィザード
   - python -m kabusys.config_setup
     - .env を対話式に作成・更新します。

2. 設定検証
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

3. 監視ループの起動（Monitoring）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定可能（デフォルト 60）
   - 起動:
     - python -m kabusys.run_monitoring
   - 停止:
     - data/stop_requested.flag ファイルを作成するとループは終了します（stop フラグ）
     - Kill Switch は別途 data/kill.flag を作成することで ExecutionEngine に停止指示を出します（KillSwitch の動作参照）

4. 実行エンジンの起動（Execution）
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用
   - 起動:
     - python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成すると起動中のエンジンは停止シグナルを受けて終了します
   - 実行開始時に PID ファイル（デフォルト data/execution.pid）を作成します

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数の上書き）
   - 出力は標準出力に検証サマリ（稼働率、注文成功率、レイテンシなど）

6. AI 関連
   - ニュース NLP スコアリング:
     - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
       - DuckDB 接続を渡し、OpenAI API キー（引数または OPENAI_API_KEY）で実行
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

7. ロギング
   - setup_logging(app_name="execution") 等により
     - stdout にログを出力
     - 日次ローテーションで logs/<app_name>.log に保存（デフォルト 30 日分保持）

---

## 運用上の注意 / 安全ガイド

- KABUSYS_ENV=live のときは設定を慎重に行ってください。validate_config によるチェックを必ず実施してください。
- Kill Switch（data/kill.flag）を誤って自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。デフォルトは 0 を推奨。
- OpenAI API を用いる機能は API 利用料が発生します。キーの管理に注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL を使ってポーリングします。短すぎると負荷を招くためデフォルト 60 秒を推奨します。
- プロセス優先度設定（process_priority）で権限不足により設定失敗することがありますが、ログに警告が出ます（フェールセーフ）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュールの抜粋です。実際のリポジトリではこれに加えて他のモジュールやテスト等があるかもしれません。

- src/kabusys/
  - __init__.py  — パッケージ宣言（__version__ 等）
  - config.py  — 環境変数 / Settings クラス、自動 .env ロード機能
  - config_setup.py  — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py — プロセス優先度・CPU affinity 設定

  - monitoring/
    - monitoring_db.py — SQLite スキーマ作成・永続化レイヤ
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — （トレード監視。ここでは省略されているが存在想定）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成・評価
    - monitoring_engine.py — 各 Monitor を束ねる

  - execution/
    - execution_engine.py — 実行エンジン本体（起動・セッション管理）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 実行周辺の構成要素（ファイル群）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — Momentum/Volatility/Value 等の計算（DuckDB 利用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ

  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — ETF MA と マクロセンチメント合成によるレジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

- その他：
  - data/ — 実行中に生成される SQLite、PID、フラグファイルなど（デフォルトパス）
  - logs/ — ログファイル（デフォルト）

---

## 開発者向けメモ / 補足

- DB マイグレーションは簡素：monitoring_db.init_monitoring_db は存在しないカラム追加等を行う簡易マイグレーションを行います。
- DuckDB は分析用の高速列指向 DB、prices_daily / raw_financials / raw_news 等のテーブルを想定しています。
- 各モジュールは可能なかぎり副作用を抑え、外部 API 呼び出しは明示的に渡す（api_key 等）ことでテストを容易にしています。
- テスト時は OpenAI 呼び出し関数（_call_openai_api）をモックすることが想定されています（score_news 等の注記参照）。

---

問題がある箇所や補足したい具体的な README セクション（たとえば systemd ユニットファイル例、docker-compose 例、CI 設定等）があれば、それに合わせて README を拡張します。必要であればサンプル .env テンプレートや起動例（systemd / supervisor / docker）も追記できます。