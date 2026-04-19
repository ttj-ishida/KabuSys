# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ群・起動スクリプト・運用ユーティリティ群）。

この README は src/kabusys 配下のコードベースに基づく利用ガイドです。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成された自動売買プラットフォームの骨組みです。

- 注文実行エンジン（ExecutionEngine） — ブローカークライアント経由で発注を行う（paper/live 切替）。
- 監視（Monitoring） — システム状態、注文ログ、リスク（ドローダウン等）を定期的にチェックしてアラートや Kill Switch を発動。
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、ポジションサイズ決定、セクター上限の適用などの純粋関数群。
- リサーチ（Research） — DuckDB を使ったファクター計算・特徴量探索。
- AI 支援（AI） — OpenAI を利用したニュースセンチメントや市場レジーム判定。
- 運用ツール（Tools） — ペーパートレード検証レポート生成など。

設計のポイント:
- 実行環境（KABUSYS_ENV）により挙動を切り替え（development / paper_trading / live）。
- DuckDB は分析・リサーチ用途、SQLite は監視・発注ログ等の永続化に使用。
- AI（OpenAI）呼び出しは外部 API を利用し、失敗時はフェイルセーフで安全側にフォールバック。

---

## 主な機能一覧

- 実行モード切替（paper_trading → MockBrokerClient、本番はブローカー実クライアント）
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor を統合）
- Kill Switch（閾値超過で data/kill.flag を書き込み ExecutionEngine を停止）
- ロギング（統一的な setup_logging、stdout + 日次ローテートファイル）
- ポートフォリオ構築ロジック（候補選定・重み付け・リスク調整・ポジションサイズ算出）
- DuckDB ベースのファクター計算（Momentum / Volatility / Value 等）
- OpenAI を使ったニュースセンチメント（ai.news_nlp）とレジーム判定（ai.regime_detector）
- 運用ユーティリティ（.env 対話式ウィザード、設定検証、Paper Trading 検証レポート）

---

## セットアップ手順

前提:
- Python 3.9+（コード内型注釈の互換性に依存）
- system に duckdb、psutil、openai 等のライブラリをインストール

一般的な手順（プロジェクトルートで実行）:

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows

2. 依存パッケージのインストール
   - requirements.txt があれば:
     - pip install -r requirements.txt
   - 主要パッケージ（例）
     - pip install duckdb psutil openai

   ※ YAML 検証を有効にするには PyYAML を追加でインストール:
   - pip install pyyaml

3. .env の初期作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくはプロジェクトルートに手動で .env を作成

4. 設定の検証
   - python -m kabusys.validate_config
   - 問題がある場合は出力に従って修正
   - --strict を付けると警告も失敗扱いになる:
     - python -m kabusys.validate_config --strict

5. OpenAI を利用する機能を使う場合:
   - 環境変数 OPENAI_API_KEY を設定するか、該当関数に api_key を渡す

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI 利用時に必要
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に data/kill.flag を自動クリアするか（"1" でクリア、デフォルト "0"）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト 60）

その他のパス:
- PID ファイル: data/execution.pid（設定は Settings.pid_file_path で上書き可能）
- 停止フラグ（監視用）: data/stop_requested.flag
- Kill Switch フラグ: data/kill.flag

.env の自動読み込み:
- デフォルトで .env と .env.local をプロジェクトルートから自動ロードします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方

主要なエントリポイント（モジュールをモード付きで実行）:

1. .env を作成・編集
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - (厳格) python -m kabusys.validate_config --strict

3. 実行エンジン起動（ExecutionEngine）
   - デフォルト（環境変数 KABUSYS_ENV に従う）:
     - python -m kabusys.run_execution
   - Paper Trading モードにするには:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
     - この場合は MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録します。
   - 停止:
     - data/stop_requested.flag を作成すると起動中の run_execution は検知して停止します。
     - 運用上の強制停止には data/kill.flag を使い Kill Switch を経由して停止判定を行います。

4. 監視ループ起動（SystemMonitor）
   - python -m kabusys.run_monitoring
   - ポーリング間隔を上書き:
     - export MONITOR_POLL_INTERVAL=30
     - python -m kabusys.run_monitoring

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を直接指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

6. AI 関連（例: ニューススコア算出）
   - 内部 API を使う関数は OpenAI API キーが必要:
     - kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)
     - OPENAI_API_KEY を環境変数に設定していれば api_key 引数は不要

ログ:
- デフォルトのログディレクトリ: logs/
- ログは stdout（コンソール）と logs/<app_name>.log（日次ローテーション）へ出力

停止フラグ / PID:
- run_execution は data/execution.pid に PID を書くことが期待されます（Engine により使用）。
- 停止フラグや kill.flag を使って外部から安全に停止できます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要なファイル・ディレクトリと説明です。

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / .env 自動ロード・Settings クラス
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前チェック CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 使用）
    - regime_detector.py — 市場レジーム判定（OpenAI 使用）
  - monitoring/
    - monitoring_db.py — SQLite を用いた監視 DB 層（テーブル作成・読み書き）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文 / 約定の整合性チェック（ファイル内に定義あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み / 管理
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py — （アラート送信ロジック）
  - execution/
    - execution_engine.py — ExecutionEngine（注文発行の中心）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py ...
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注数量算出
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（Momentum / Volatility / Value）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - utils/
    - logging_setup.py — 共通ロギング設定
    - process_priority.py — プロセス優先度・CPU affinity 設定
    - その他ユーティリティ

データ・ログ等（プロジェクトルート想定）
- data/
  - monitoring.db (SQLite) — 監視ログ・trade_logs 等
  - paper_trading.db (SQLite) — paper_trading 用注文ログ（KABUSYS_ENV=paper_trading）
  - kabusys.duckdb — DuckDB（デフォルト: data/kabusys.duckdb）
  - execution.pid, kill.flag, stop_requested.flag — 運用用フラグ / PID

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では .env の値を慎重に管理してください。validate_config は live 時に特別な警告を出します。
- Kill Switch（data/kill.flag）が存在すると ExecutionEngine の稼働を停止させる設計です。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（自動クリアされるため）。
- OpenAI API 呼び出しは外部コストが発生します。api_key の管理やレート制限に注意してください。
- DuckDB / SQLite のファイルパスは .env で指定可能です。バックアップ・ディスク容量・パーミッションに注意してください。
- ロギングディレクトリ作成に失敗した場合はファイル出力が無効化され stdout のみとなります。ログディレクトリ権限を確認してください。

---

## よく使うコマンドまとめ

- .env の設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- (開発) 単体関数の呼び出し:
  - Python REPL / スクリプトからモジュール関数をインポートして実行

---

必要があれば README をさらに詳細化（各環境変数の完全一覧、アーキテクチャ図、運用手順、データベーススキーマ説明、ユニットテスト手順など）します。どの情報を追加したいか教えてください。