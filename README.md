# KabuSys

日本株自動売買システムの軽量コアライブラリ（開発用 README）。  
この README はリポジトリ内のソースコードに基づき作成しています。

主な機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコアコンポーネント群です。  
主な役割は以下の通りです。

- 発注エンジン（ExecutionEngine）を起動して注文管理・リスク管理を行う
- システム監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート管理
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- 研究用モジュール（ファクター計算、特徴量解析）
- AI 支援（ニュースの NLP スコアリング、レジーム判定）
- 開発者向けツール（.env ウィザード、設定検証、Paper Trading レポート作成）

設計思想としては、実行環境（本番 / ペーパー / 開発）を明確に分離し、DB や発注クライアントを環境に応じて切り替え可能にすることで、安全性を確保しています。

---

## 機能一覧（抜粋）

- Execution
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV によるペーパートレード切替）
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - リスク管理（RiskManager）、OrderManager、Reconciler など
- Monitoring
  - run_monitoring: SystemMonitor のポーリングループを起動
  - SystemMonitor / TradeMonitor / RiskMonitor（監視ログは SQLite に永続化）
  - KillSwitch（条件に応じて data/kill.flag を書き込む）
  - MonitoringEngine（監視モジュールの統合）
- Portfolio
  - 候補選定、等配分／スコア加重配分
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）
  - セクター上限制御・レジーム乗数
- Research
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - DuckDB を用いた高速集計
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM でセンチメント評価し ai_scores に保存
  - regime_detector: MA とマクロセンチメントを合成して市場レジーム判定
- ユーティリティ
  - .env 設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート（tools/paper_verification_report）
  - ロギング設定（utils/logging_setup）
  - プロセス優先度・CPU affinity ヘルパー（utils/process_priority）

---

## 必要な外部依存（代表）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を行う場合に推奨）

（実際の requirements.txt は本リポジトリに合わせて用意してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロダクション用途は適切なバージョン管理を行ってください）

3. 環境変数の初期化（.env 作成）
   - 対話型ウィザード:
     - python -m kabusys.config_setup
     - ウィザードは .env を生成します（デフォルトはプロジェクトルート/.env）
   - 自動ロードの動作:
     - config モジュールはプロジェクトルートを判定し `.env` と `.env.local` を自動で読み込みます
     - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

4. 設定の検証
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

5. データディレクトリ / ログディレクトリ（多くは自動作成されますが事前作成しても良い）
   - data/（SQLite や PID・フラグファイルを格納）
   - logs/（ログファイル、setup_logging が自動作成を試みます）

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（"1" で有効、開発用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

注意: Settings モジュール内で必須変数が未設定の場合は ValueError が発生します。validate_config で事前確認を推奨します。

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動を行いません。
    - 実行中は data/execution.pid に PID を書きます。停止は stop フラグや kill.flag の検出で行います。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60）
  - 補足:
    - Monitoring は常に本番用の sqlite_path を使用して監視ログを記録します（KABUSYS_ENV に依存しない）。
    - 停止フラグ: data/stop_requested.flag

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定して、kabusys.ai.score_news などの関数を呼び出します（スクリプト経由の利用を想定）。
  - 注意: OpenAI 呼び出しは失敗耐性処理（リトライ / フォールバック）を持ちますが、API キーは必須です。

---

## 運用上の注意

- データベース分離:
  - 本番監視 DB（SQLITE_PATH）とペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）は分離されています。ペーパートレード稼働時に本番 DB に影響を与えないよう設計されています。
- Kill Switch:
  - RiskMonitor 等が条件を満たすと data/kill.flag を作成することで ExecutionEngine に停止シグナルを送ります（KillSwitch）。本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- ロギング:
  - すべての起動スクリプトは utils.setup_logging を使用し、logs/<app_name>.log に日次ローテートで出力します。LOG_DIR で変更可能。
- 権限・優先度:
  - 実行スクリプトは起動時に set_process_priority("high") を呼びます。権限により設定できない場合は警告を出します（psutil が必要）。

---

## ディレクトリ構成（抜粋）

プロジェクトルートの src/kabusys 以下の主なファイル・パッケージ:

- run_execution.py
  - ExecutionEngine の起動スクリプト（スレッドで実行し stop フラグ検出で終了）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔設定）

- config.py
  - 設定読み込み・Settings クラス（.env 自動読み込みロジック・env getter）

- config_setup.py
  - 対話式 .env 生成ウィザード

- validate_config.py
  - 起動前設定検証 CLI

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

- ai/
  - news_nlp.py — ニュースを LLM でスコアリングし ai_scores テーブルへ書き込み
  - regime_detector.py — 市場レジーム判定

- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — CPU / メモリ / データ鮮度 / プロセス監視
  - trade_monitor.py — 発注ログ整合性・滞留注文等の監視（ソース参照）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイル書き込みによる停止シグナル
  - monitoring_engine.py — 各モニタの束ね

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・集計上限・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — ファクター計算
  - feature_exploration.py — 将来リターン・IC・統計解析

- utils/
  - logging_setup.py — ログの共通設定（コンソール + 日次ファイルローテート）
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

- __init__.py
  - パッケージ定義・バージョン

その他、data/（実行時生成されることが多い）と logs/ が期待されるディレクトリです。

---

## よくある運用操作

- 停止フラグを利用して安全に停止する
  - 実行中のプロセスは data/stop_requested.flag を監視します。停止させたい場合はこのファイルを作成してください（運用ルールに応じて管理）。
- Kill Switch をクリアする
  - data/kill.flag があると ExecutionEngine は発注を停止します。開発環境で自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を .env に設定します（本番では非推奨）。
- ログレベル変更
  - LOG_LEVEL 環境変数で変更できます（例: export LOG_LEVEL=DEBUG）。

---

## 開発者向けメモ

- DuckDB を用いるモジュール（research, ai の一部）は、DuckDB の接続オブジェクトを引数として受け取ります。テスト時はインメモリ DB を作成して注入すると良いです。
- OpenAI 呼び出しは _call_openai_api をラップしているため、ユニットテストでは該当関数をモックしてください（例: unittest.mock.patch）。
- monitoring_db.init_monitoring_db は冪等でマイグレーション（カラム追加）処理を行います。既存 DB の互換性保持に注意しています。

---

この README はコードの主要部分から自動的に要点を抜粋して作成しています。運用やデプロイ時は環境固有の設定（DB バックアップ、アクセス権限、API キー管理）に十分ご注意ください。必要であれば実行例や docker-compose、CI/CD の設定例も追加で作成できます。