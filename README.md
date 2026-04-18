# KabuSys

日本株自動売買システムのコアライブラリ（README）。  
この README はリポジトリ内のスクリプト／モジュール群の使い方、セットアップ手順、ディレクトリ構成の概要を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステム群です。主な機能は以下の通りです。

- 発注を担当する ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働や注文挙動を監視する Monitoring（監視ループ・アラート・Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限等）
- リサーチ／ファクター計算（DuckDB を用いたファクター計算、特徴量探索）
- ニュース NLP を使ったセンチメント評価 / レジーム判定（OpenAI）
- 運用支援ツール（ペーパートレード検証レポート等）
- ロギング・プロセス優先度設定などのユーティリティ

設計上のポイント：
- 環境は env / .env で管理。`KABUSYS_ENV` によって `development` / `paper_trading` / `live` を切替。
- Paper Trading モードでは Mock ブローカーを使い、ペーパートレード専用の SQLite DB に記録して本番 DB を分離。
- DuckDB を分析用 DB として利用。SQLite は監視・発注ログの永続化に使用。

---

## 機能一覧

- Execution
  - 実際の発注ロジックを含む `ExecutionEngine`
  - ブローカークライアント抽象化（実ブローカー / MockBroker 切替）
  - リスク管理（rate limit、max position、drawdown 等）
- Monitoring
  - システム監視（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - 注文監視（滞留注文、約定異常等）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件を満たすと `data/kill.flag` を書き込み ExecutionEngine を停止）
  - `monitoring.db`（SQLite）へのログ永続化（テーブル＆マイグレーション対応）
- Portfolio
  - シグナルの候補選定、等配分・スコア配分、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）
  - ニュース記事のセンチメントスコアリング（`ai.news_nlp`）
  - マクロニュース + ETF MA200 乖離から市場レジーム判定（`ai.regime_detector`）
  - API 呼び出しは冪等・バックオフ等を考慮した実装
- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）
- ユーティリティ
  - 統一的なログ設定（stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env ウィザード、設定検証 CLI

---

## 必要条件（推奨）

- Python 3.9+（ソースは型注釈で modern Python を想定）
- 主要ライブラリ（最低限、環境に応じてインストールしてください）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML を検査する場合に任意）
- SQLite（Python に同梱の sqlite3 を使用）
- ネットワーク接続（OpenAI / ブローカー API を使う場合）

例（最低限のインストール）:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

   （実運用では requirements.txt を用意して pip install -r requirements.txt を使用することを推奨）

4. 初期設定（.env を作成）
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV などを設定
   - 設定検証: python -m kabusys.validate_config
     - --strict を付けると警告も失敗として扱う

5. 必要ディレクトリの作成
   - data/ （SQLite DB・PID・flag などを置く）
   - logs/ （ログ出力先、デフォルト）

6. DB 初期化はスクリプト実行時に自動で行われる（monitoring の init_monitoring_db が冪等で作成／マイグレーションを行います）。

---

## 主要な環境変数（要点）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API base（default: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI機能利用時に必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、default: INFO）
- LOG_DIR: ログディレクトリ（default: logs/）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モード）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: プロセス制御用 / Kill Switch 関連

（詳細は `kabusys.config.Settings` を参照してください。多くはデフォルト値が設定されています。）

---

## 使い方（主要スクリプト）

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で制御。`paper_trading` の場合は MockBroker を使い `PAPER_TRADING_SQLITE_PATH` に記録される。
  - 実行中は `data/execution.pid`（デフォルト）に PID を保存し、`data/stop_requested.flag` または kill.flag による停止制御を行う。

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - 監視は monitoring DB（デフォルト `data/monitoring.db`）に書き込み、Kill Switch を評価して必要に応じ `data/kill.flag` を書く

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能）
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ など

- AI 系（プログラム的利用）
  - ニューススコア付与:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - 引数に DuckDB 接続（duckdb.connect() の返り値）と target_date（datetime.date）を渡す
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

注意:
- run_monitoring は Monitoring の DB を常に本番 sqlite_path（Settings.sqlite_path）で使用します（環境に関係なく）。
- run_execution は KABUSYS_ENV=paper_trading のとき専用 DB に接続して本番 DB と分離します。

---

## 運用上の注意

- Kill Switch:
  - `kabusys.monitoring.KillSwitch` は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - `KILL_FLAG_CLEAR_ON_START=1` を本番で使うと危険（自動クリア）。live 環境では 0 推奨。
- ログ:
  - 共通の `setup_logging()` を用いて stdout と `logs/<app>.log`（日次ローテーション）へ出力します。ログディレクトリは `LOG_DIR` またはデフォルト `logs/`。
- DB マイグレーション:
  - `monitoring_db.init_monitoring_db()` はテーブル作成に加え、簡易的なマイグレーション（カラム追加）を行います。既存データとの互換に注意してください。
- AI:
  - OpenAI 呼び出しはリトライ・バックオフを備えていますが、API キーは必須。失敗時はフェイルセーフ（スコア 0 等）で継続する実装が一部にあります。
- 権限:
  - process priority の設定は権限が必要な場合があります。設定に失敗したときは警告を出してスキップします。

---

## ディレクトリ構成（主要ファイルの説明）

以下はソース配下の主要ファイル・モジュールの一覧（抜粋）と役割です。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス：環境変数・.env の読み込み・検証ロジック
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID / stop flag 制御）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で調整）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/
    - execution_engine.py, broker_factory.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    - 発注・リスク管理関連（Engine 本体、ブローカー抽象等）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / PID チェック
    - trade_monitor.py — 注文の滞留／約定異常監視（ファイル内実装参照）
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — kill.flag の作成・管理
    - monitoring_engine.py — 各 Monitor を束ねてポーリングするエンジン
    - alert_manager.py — (アラート送信の実装場所：LINE 等)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数計算（単元丸め・リスクベース）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等の計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計
  - ai/
    - news_nlp.py — raw_news を OpenAI で解析し ai_scores へ書き込む
    - regime_detector.py — ETF MA200 と LLM マクロセンチメントを組み合わせレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

- data/
  - デフォルトの DB（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等） / PID / flag を置く
- logs/
  - ログファイルはここに日次でローテートされます（例: logs/execution.log, logs/monitoring.log）

---

## 開発・拡張ポイント（参考）

- BrokerClientFactory に実ブローカー実装を追加して本番接続を可能にする
- 単体テスト・モックが充実していると安全に運用可能（特にリスク関連）
- DuckDB スキーマ（prices_daily, raw_financials, raw_news 等）の整備とデータ投入スクリプト
- アラート送信（LINE 等）の実装／設定強化
- ログ・メトリクスの外部集約（Prometheus / Loki 等）を追加することで運用性向上

---

## よく使うコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン開始: python -m kabusys.run_execution
- 監視ループ開始: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD [--db PATH]

---

この README はコードベース内の docstring と関数説明を元に作成しています。詳細な API や内部実装を確認したい場合は、該当モジュール（例: kabusys.execution.*, kabusys.monitoring.*, kabusys.ai.*）の docstring を参照してください。必要であれば英語版 README や運用手順書（Runbook）の作成も支援します。