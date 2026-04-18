# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買／リサーチ基盤コンポーネント群です。  
主要な機能はシグナル生成・ポートフォリオ構築、発注実行（実口座／ペーパートレード）、監視、AI を用いたニュース評価などを含みます。

---

## プロジェクト概要

- 設計方針
  - 発注ロジックと監視ロジックを分離し、独立したプロセス（ExecutionEngine / Monitoring）として実行可能。
  - Paper trading（ペーパートレード）と Live（本番）を環境変数により切替可能。ペーパートレードは本番 DB と分離される。
  - DuckDB を用いた研究・ファクター計算、SQLite を用いた監視・発注ログ永続化。
  - OpenAI（gpt-4o-mini 等）を利用したニュース NLP・レジーム判定（API キー任意）。
  - ログはコンソール出力 + 日次ローテーションファイル（logs/）で管理。

---

## 機能一覧

- 実行系
  - ExecutionEngine（発注実行、risk manager、order manager、reconciler 等）
  - BrokerFactory により本番／モックブローカーを切替（KABUSYS_ENV に依存）

- 監視系
  - SystemMonitor：CPU/メモリ/ディスク/プロセス生存・データ鮮度監視
  - TradeMonitor：注文の滞留・約定の異常検出（trade_logs 参照）
  - RiskMonitor：ドローダウン・ポジション上限監視（dashboard, positions）
  - MonitoringEngine：上記を束ねてポーリング、Kill Switch 判定、Alert 発行

- ポートフォリオ構築（純粋関数）
  - 候補選定、等金額／スコア加重配分、ポジションサイズ計算（lot 切り捨て）、セクター上限、レジーム乗数

- リサーチ（DuckDB ベース）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC 計算、統計サマリー

- AI / NLP
  - news_nlp: raw_news を集約して LLM（OpenAI）でセンチメント評価 → ai_scores に書込み
  - regime_detector: ETF（1321）MA200 とマクロニュースを組合せて市場レジーム判定

- CLI ツール
  - 環境設定ウィザード: python -m kabusys.config_setup（.env を対話式で作成）
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（開発／ローカル向け）

1. リポジトリをクローンし、仮想環境を作成
   - python 3.10+ 推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - 主要依存 (例):
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（設定検証で YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt はリポジトリに含まれていないため、プロジェクト用途に合わせて依存を固定してください。

3. 初期設定（.env 作成）
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（プロジェクトルートに配置）。
   - 例（最小）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - .env は決してバージョン管理にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います。

5. データディレクトリの準備（任意）
   - ログディレクトリ: logs/
   - DB ディレクトリ: data/
   - 多くのスクリプトは起動時に必要なディレクトリを自動作成しますが、権限などに注意してください。

---

## 使い方（起動・操作）

- ExecutionEngine（発注実行）
  - 本番モード / ペーパートレードは KABUSYS_ENV で切替:
    - KABUSYS_ENV=paper_trading → MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書込む
    - KABUSYS_ENV=live → 実ブローカー
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると起動中の run_execution が検知して停止します。
    - または monitoring 側の KillSwitch（data/kill.flag）で停止指示を出せます。

- Monitoring（監視プロセス）
  - 起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き（デフォルト 60）
  - 監視 DB:
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視ログは共通の監視 DB に記録）。
  - 停止:
    - data/stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH を指定することも可能。

- その他
  - ログ設定は kabusys.utils.logging_setup.setup_logging により統一
    - LOG_DIR 環境変数で出力先変更、LOG_LEVEL でレベル調整
  - OpenAI API を利用する機能（news_nlp, regime_detector）は環境変数 OPENAI_API_KEY を設定するか、関数呼び出し側で api_key を渡してください。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。デフォルト 60）
- OPENAI_API_KEY — OpenAI 利用時の API キー
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1。production では 0 推奨）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）

---

## 停止・Kill Switch の運用

- data/stop_requested.flag — run_execution / run_monitoring の外部停止フラグ（プロセスが検知して安全に終了）
- data/kill.flag — Monitoring の KillSwitch が書き込むことで ExecutionEngine に停止命令を出す（重大なリスク検出時）
  - KillSwitch はドローダウンや保有上限をトリガーに書き込み、既存の flag がある場合は追記しません（冪等）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings クラス、自動 .env ロードロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリング起動スクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
- execution/ (実行関連コンポーネント)
  - order_manager.py, execution_engine.py, broker_factory.py, order_repository.py, reconciler.py, risk_manager.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py, process_priority.py

（注）実際の broker 実装や execution internals は execution/ 配下にあり、発注APIとの接続箇所は BrokerClientFactory 経由で抽象化されています。

---

## 開発メモ・注意事項

- self-contained な SQL マイグレーション機構を monitoring_db.init_monitoring_db が持ち、既存テーブルにカラムがない場合は ALTER で追加します。
- DuckDB 関連処理はリサーチ専用で、本番発注処理とは分離されています（読み取りのみ）。
- OpenAI を利用する処理は API のエラー（429・timeout・5xx）に対して指数バックオフのリトライを実装していますが、API キーの漏洩やコスト管理には注意してください。
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動ロードします（テスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- ログファイル作成に失敗しても（権限等）コンソール出力は継続するように設計されています。

---

## よく使うコマンド例

- 環境設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

必要であれば README に以下を追加できます:
- requirements.txt の推奨セット
- systemd / supervisor 用のサービスユニットサンプル
- 具体的な .env.example（完全版）
- 各モジュールの詳細な API ドキュメント（関数一覧・引数説明）