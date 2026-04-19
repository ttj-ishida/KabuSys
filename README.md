# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システム（仮称 KabuSys）のコアモジュール群です。戦略・ポートフォリオ構築・実行エンジン・監視・調査（Research）・AI（ニュースセンチメント/レジーム判定）などを含みます。

以下はこのコードベースの概要・機能・セットアップ・使い方・ディレクトリ構成です。

---

## プロジェクト概要

- 自動売買のためのコンポーネント群（ExecutionEngine、監視、リスク管理、OrderRepository 等）を提供します。
- データ分析・研究用に DuckDB を使ったファクター計算モジュールを持ちます（prices_daily / raw_financials を参照）。
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と分離して検証できます。
- ニュース記事を LLM（OpenAI）でスコアリングする AI コンポーネント（news_nlp）や、市場レジーム判定（regime_detector）を備えます。
- 監視（Monitoring）コンポーネントによりシステム状態・データ鮮度・注文の異常などを検出し、Kill Switch により ExecutionEngine を停止できます。

---

## 主な機能一覧

- Execution
  - ExecutionEngine と Order 管理、RiskManager、Reconciler（ブローカーとの整合）を組み合わせた発注処理
  - KABUSYS_ENV により paper_trading / live / development を切替可能
  - paper_trading モード時は MockBrokerClient を使用し、専用 SQLite（デフォルト: data/paper_trading.db）に記録

- Monitoring
  - SystemMonitor: CPU/Mem/Disk、プロセス稼働、データ鮮度の監視
  - TradeMonitor: 注文の滞留や約定異常検出（trade_logs を参照）
  - RiskMonitor: ドローダウン、ポジション上限監視とアラート / Kill Switch 連携
  - MonitoringEngine: 上記モニタを束ねたポーリングループ（MONITOR_POLL_INTERVAL で間隔指定）

- Portfolio Construction（純粋関数）
  - 候補選定、等配分/スコア加重、セクター制限、ポジションサイズ計算（lot 単位丸め等）

- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC 計算、特徴量サマリ

- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に格納
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM スコアを合成して market_regime を決定

- ユーティリティ
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.10+（typing の | ユニオンが使われているため）

1. リポジトリをクローンし、仮想環境を用意します。
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要なパッケージをインストールします（最小限の例）。
   - 例:
     pip install duckdb psutil openai pyyaml

   - このコードベースで使用される主な外部依存:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config YAML の検証を行う場合。無くても動作しますが警告が出ます）

3. 初期環境変数（.env）を作成します。
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - 手動で作る場合はリポジトリルートに `.env` を置き、以下の主要キーを設定してください（例）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0

   - 自動ロード: .env と .env.local は自動で読み込まれます（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. データディレクトリを作る（ログ・DB 保存場所）:
   - mkdir -p data logs

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API を使う場合に必須（AI 機能）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を削除するか（1=削除する、0=削除しない）
- PID_FILE_PATH, KILL_FLAG_PATH — Settings 経由で上書き可能

---

## 使い方（主なコマンド）

- 設定ウィザード（.env を作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告もエラー扱いにする場合:
    python -m kabusys.validate_config --strict

- 監視（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視はデフォルトで Settings.sqlite_path（本番用 monitoring.db）を使います（KABUSYS_ENV に依らず本番 sqlite を参照）。

- 実行エンジン（Execution）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のとき、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録し MockBrokerClient を使用します。
  - 実行中の停止:
    - マニュアルで停止フラグを立てる: データディレクトリに `stop_requested.flag` を置く（run_execution/run_monitoring の両方で検知して終了する）。
    - KillSwitch（リスク条件検出時）は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（プログラム上で呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要（api_key 引数で渡すことも可能）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## ログ・DB・フラグファイル

- ログ:
  - デフォルトログディレクトリ: logs/
  - ログファイル名: <app_name>.log（例: logs/monitoring.log, logs/execution.log）
  - ログは日次ローテート（30日保持）
  - setup_logging() を各起動スクリプトで呼び出しています

- DB:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite 監視 DB: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db（paper_trading モードで使用）

- フラグ / PID ファイル:
  - stop_requested.flag: run_monitoring/run_execution が起動ループ内で検知し終了するための外部停止フラグ
  - data/kill.flag: KillSwitch が書き込む停止フラグ（Execution 停止トリガー）
  - execution.pid: ExecutionEngine の PID を書き込むファイル（デフォルトパスは data/execution.pid、Settings で上書き可）

---

## 実行時の挙動・注意点

- run_monitoring の挙動
  - MONITOR_POLL_INTERVAL で設定した秒間隔で SystemMonitor.check_once() を呼び続けます（デフォルト 60 秒）。
  - 監視は常に Settings.sqlite_path（本番 monitoring.db）を使います（KABUSYS_ENV に依存しない）。
  - Stop フラグ（data/stop_requested.flag）を検知すると安全にループを抜けます。

- run_execution の挙動
  - KABUSYS_ENV=paper_trading の場合、Paper 用 SQLite を使い Mock ブローカーで完全分離して記録します。
  - 起動時に stop フラグが既に存在する場合は起動せず終了します。
  - 実行は別スレッドで run_session() を実行し、外部から stop フラグ検出で engine.stop() を呼びます。

- AI 機能の安全対策
  - OpenAI API の呼び出しはリトライ（指数バックオフ）を実装しています（429 / ネットワーク断 / タイムアウト / 5xx）。
  - レスポンスは厳密に検証し、無効なレスポンスは部分的に無視して安全に継続します。
  - API キーが未設定の場合は呼び出し側が ValueError を受け取ります（明示的に処理してください）。

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — Settings クラス（環境変数の集約・読み込み・検証）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI

  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — ニュース記事を LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（MA200 + マクロ LLM）

  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/Mem/Disk、データ鮮度、実行プロセス監視
    - trade_monitor.py — （注文ログ検査用）※該当ファイルの詳細実装が存在
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の管理・判定
    - monitoring_engine.py — 各 Monitor を束ねたポーリング実行

  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py — ブローカークライアント生成（Mock含む）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・スケール調整
    - risk_adjustment.py — セクター制限、レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value など
    - feature_exploration.py — 将来リターン、IC、統計要約

  - monitoring_db.py (上記 monitoring/monitoring_db.py と重複説明)
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

  - utils/
    - logging_setup.py — 統一ロギング設定（コンソール + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## よくある運用／デプロイのヒント

- systemd / supervisor 等で実行する場合:
  - run_monitoring/run_execution をそれぞれサービス化して自動起動・再起動を管理すると良い。
  - ログ出力は logs/ に集約されるため、ログローテーションや収集ツールを設定すると運用しやすくなる。

- 本番運用の注意:
  - KABUSYS_ENV=live の場合は特に .env や config/*.yaml の内容を慎重に確認してください（validate_config で警告を出す）。
  - KILL_FLAG_CLEAR_ON_START は本番では 0 にすることを推奨（1 にすると起動時に kill.flag が消去されるため危険）。
  - OpenAI キーを含む機密情報は決して Git にコミットしないでください（config_setup のヘッダにも記載あり）。

---

## 追加情報・参考

- 監視 DB のマイグレーション処理やテーブル定義は monitoring_db.init_monitoring_db() を参照してください。
- AI モジュールは API レスポンスの不確実性に対処するため堅牢に設計していますが、利用には OpenAI の利用料等がかかります。
- 研究（research）モジュールは DuckDB のテーブル（prices_daily, raw_financials 等）を前提に動作します。データの投入方法は別途用意する ETL / pipeline を参照してください（get_last_price_date など）。

---

もし README に追加したい「運用手順」「systemd サンプル」「DB スキーマの詳細」「設定例ファイル（.env.example）」などがあれば、ご希望に応じて追記します。