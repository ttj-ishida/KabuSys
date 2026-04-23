# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム「KabuSys」のコードベースです。本 README はローカルでのセットアップ、主要機能、起動方法、ディレクトリ構成などを日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群で構成されています。

- 市場データ（DuckDB）を用いたリサーチ・ファクター計算
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター上限等）
- ExecutionEngine による発注実行（本番 / ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk モニタ）と Kill Switch
- OpenAI を使ったニュース NLP（センチメント）やレジーム判定
- 運用補助ツール（設定ウィザード、設定検証、ペーパー検証レポート など）

設計方針として「本番口座にアクセスしないリサーチ」「ペーパートレードとの分離」「ローカルで動作する単純なストレージ（SQLite / DuckDB）」を重視しています。

---

## 主な機能一覧

- 設定管理
  - .env ファイル自動読み込み（プロジェクトルート基準）
  - 対話式環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行系（Execution）
  - ExecutionEngine（本番 / ペーパー切替）
  - ブローカークライアント抽象化（paper_trading 時は MockBrokerClient を使用）
  - リスク管理（ポジション上限、最大利用率、ドローダウン等）

- 監視（Monitoring）
  - SystemMonitor（CPU/メモリ/Disk、データ鮮度、Executionプロセス健全性）
  - TradeMonitor（注文滞留・約定異常の検出）
  - RiskMonitor（ドローダウン・ポジション上限の監視）
  - KillSwitch（条件を満たしたとき data/kill.flag を書き込み Execution を停止）
  - 監視ログ永続化（SQLite: monitoring.db、MonitoringDB API）

- ポートフォリオ構築
  - 候補選定（スコア降順、上位N）
  - 重み付け（等金額、スコア加重）
  - ポジションサイズ計算（リスクベース、上限・単元丸め、スケールダウンロジック）
  - セクター上限適用、レジーム乗数

- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン・IC（情報係数）計算、統計サマリー

- AI（OpenAI）
  - ニュースのセンチメントスコアリング（ai_scores テーブルへ書き込み）
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）
  - OpenAI 呼び出しは健全なリトライ・バリデーションを実装

- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動。

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限必要な主要ライブラリ:
     - pip install duckdb psutil openai
   - （任意）YAML 検証を行う場合: pip install PyYAML

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します（.env は決して Git にコミットしないでください）

5. 設定検証
   - python -m kabusys.validate_config
   - 本番環境では --strict を使うと警告も失敗扱いになります。

6. データディレクトリの作成（必要に応じて）
   - data/ ディレクトリを作成（デフォルト DB 等の格納場所）
   - デフォルトの SQLite / DuckDB パス: data/monitoring.db, data/kabusys.duckdb

注意:
- OpenAI を利用する場合は OPENAI_API_KEY を .env に設定してください。
- J-Quants や kabuステーション連携は JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD が必須です。

---

## 環境変数（主要）

一部の主要な環境変数とデフォルト値:

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパー発注の約定挙動（instant / partial / never / reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR: ログ保存先（デフォルト: logs）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch の flag パス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト: 60）

---

## 使い方（起動コマンド例）

- 環境設定ウィザード（.env の初期作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に分離して記録します。
    - 起動前に data/stop_requested.flag があれば起動を行いません。
    - 実行中は data/execution.pid に PID を書き込みます。
    - 停止は data/stop_requested.flag の作成でトリガできます（停止フラグの位置はスクリプト内で data/stop_requested.flag を参照）。

- Monitoring 起動（常駐ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は本番用 sqlite_path を環境にかかわらず使用します（監視ログは monitoring.db に保存）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（conn）と target_date を渡す。api_key を省略すると OPENAI_API_KEY を参照します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- kill.flag / stop フラグについて
  - KillSwitch は条件検出時に Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。
  - ExecutionEngine/Monitoring の即時停止用には data/stop_requested.flag（run scripts が参照）を使う実装が一部にあります。環境によって使い分けられていますので、実運用ではドキュメントに従ってください。
  - kill.flag を手動で解除するにはファイル削除（rm data/kill.flag）または KillSwitch.clear() を呼ぶ。

---

## ディレクトリ構成（主要）

以下は src/kabusys 配下の主要ファイルとディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py       — 統一ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py       — （trade_monitor 実装ファイルあり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
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
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定
  - data/                    — 実行時に使用するファイル（DB・flag・PID 等、デフォルトパス）
  - logs/                    — ログディレクトリ（デフォルト）

（上記は抜粋です。実際のファイル構成はリポジトリを参照してください。）

---

## 運用上の注意点

- .env は機密情報（APIキーやパスワード）を含むため、絶対に Git に含めないでください。config_setup.py のヘッダにも注意書きがあります。
- KABUSYS_ENV=live の場合は本番発注が行われます。LINE 通知設定や Kill Switch の設定を十分に確認してください。
- OpenAI を利用する処理は API 呼び出しが発生します。API 利用料金やレートを考慮してください。失敗時はフェイルセーフ（スコア 0.0 など）で継続する実装になっていますが、設定ミスには注意。
- monitoring / execution の停止には stop flag / kill flag の取り扱いを運用フローに固めてください。
- DuckDB / SQLite のファイルはローカルに保存されます。バックアップやアクセス権に注意してください。

---

## 追加情報 / 参照

- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されます。ログファイルはデフォルト logs/<app_name>.log（日時ローテート）に吐かれます。
- プロセス優先度設定は kabusys.utils.process_priority.set_process_priority を使用します。起動スクリプトで最初に呼び出されています。
- テストや CI 用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます。

---

README に記載の内容で不足している箇所や、起動時の具体的なエラーメッセージ対応、運用手順書（SOP）などが必要であればその目的に合わせて追記します。