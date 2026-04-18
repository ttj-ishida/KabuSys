# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 起動スクリプト群）。

このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築・リスク計算、リサーチ（ファクター計算）および AI を用いたニュースセンチメントやレジーム判定などを含む、モジュール化された設計になっています。ライブラリとして利用することも、付属の起動スクリプトでプロセスを動かすこともできます。

バージョン: 0.1.0

---

## 概要（Project overview）

- 実行エンジン（ExecutionEngine）: ブローカークライアントを用いて発注を管理・実行します。`KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使い、ペーパートレード用 DB に記録します（本番 DB と分離）。
- 監視（Monitoring）: システム稼働状態、データ鮮度、注文状況、リスク（ドローダウン、ポジション上限等）を定期的にチェックし、必要に応じてアラートや Kill Switch（停止フラグ）を立てます。
- ポートフォリオ構築: シグナルの選定、重み付け（等金額・スコア加重）、ポジションサイズ計算（リスクベースなど）、セクター上限などを純粋関数群として提供。
- リサーチ: DuckDB 上の時系列データからファクター（モメンタム、ボラティリティ、バリュー等）や将来リターン、IC 計算、統計サマリーを算出。
- AI（OpenAI）連携: ニュース記事のセンチメントを LLM で評価して銘柄スコア化（ai_scores）、マクロニュースと ETF（1321）MA を合成して市場レジーム判定を行うモジュール。
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード・検証 CLI、紙トレード検証レポートなど。

---

## 主な機能一覧（Features）

- Execution:
  - 実際のブローカー接続または MockBroker によるペーパートレード対応
  - 注文リポジトリ、注文管理、リスクマネージャ、再調整（reconciler）等のコンポーネント分離
- Monitoring:
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化（SQLite）
  - Process 停止検出、データ鮮度チェック、ドローダウン検出、ポジション数監視
  - Kill Switch による安全停止
- Research:
  - DuckDB を使用した高速ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Spearman）、ファクター統計
- Portfolio:
  - 候補選定、重み計算（等金額/スコア）、ポジションサイズ計算（単元丸め・aggregate cap）
  - セクターキャップ、レジーム乗数による資金配分制御
- AI:
  - ニュースの銘柄別センチメント算出（OpenAI 使用）
  - マクロニュース + ETF MA によるレジーム判定（OpenAI 使用）
  - バックオフと堅牢なバリデーションを実装
- ツール:
  - .env を対話的に作成する `python -m kabusys.config_setup`
  - 設定検証 `python -m kabusys.validate_config`
  - ペーパートレード検証レポート `python -m kabusys.tools.paper_verification_report`

---

## セットアップ手順（Setup）

前提
- Python 3.9+ を推奨（ソースは typing の構文を多用しています）
- システムレベルで必要なパッケージ（例: libssl 等）は環境に依存します

1. リポジトリをクローン／展開してワークディレクトリへ移動します。

2. 仮想環境を作成して有効化します（任意だが推奨）。
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストールします（例）。
   - pip install duckdb psutil openai PyYAML
   - 他に使用する実装（ブローカークライアント等）に応じて追加してください。

   （プロジェクトに requirements.txt がある場合はそれを使用してください:
    pip install -r requirements.txt）

4. 初期設定（.env）を用意します。
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成してください。
   - 自動ロードは既定で有効です（OS 環境変数 > .env.local > .env の順）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 設定検証:
   - python -m kabusys.validate_config
   - 必須の環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 本番環境での注意点（KABUSYS_ENV=live の場合の警告など）を確認してください。

6. データディレクトリ等は実行時に自動作成されますが、書き込み権限が必要です（デフォルト: data/, logs/）。

---

## 主要な環境変数（主なもの）

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使うモジュール用（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のパス（Settings で上書き可能）

設定ファイル作成は `python -m kabusys.config_setup` を利用してください。

---

## 使い方（Usage）

起動スクリプト（CLI）例:

- 設定ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として扱います

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作中は data/execution.pid（デフォルト）に PID を書きます
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します

- 監視ループ起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で上書き可能

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

停止・制御:
- run_execution / run_monitoring はプロセス内で data/stop_requested.flag を監視します。停止したい場合はプロジェクトルートの data/stop_requested.flag を作成してください（自動的に検出して安全に停止します）。
- Kill Switch: 監視コンポーネントが危険状態を検知すると `data/kill.flag` を書き込みます。ExecutionEngine は起動時にこの Kill Flag を検出すると起動を行いません（または実行中に検出すると停止シグナルを受け取ります）。本番では `KILL_FLAG_CLEAR_ON_START` を 0 にすることを推奨します。

ライブラリとして利用する例（Python API）:
- ファクター計算:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb"); calc_momentum(conn, date(2026,4,1))
- ニュース NLP:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

ログ:
- setup_logging が提供され、起動スクリプトはこれを使用して `logs/<app_name>.log` に日次ローテーションで出力します（ディレクトリ: logs/）。

注意点:
- OpenAI を使うモジュールは API キーが必須です（環境変数 OPENAI_API_KEY または関数引数で指定）。
- .env の自動ロードは、プロジェクトルート（.git または pyproject.toml 検出）を基準に行われます。自動ロードを無効化する場合 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## ディレクトリ構成（Directory structure）

下記は主要ファイル / パッケージの概略（src/kabusys 内）です。実際のツリーはリポジトリルートによります。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート出力
  - execution/                — 実行エンジン関連（broker_factory, execution_engine, order_manager, order_repository, risk_manager, reconciler 等）
  - monitoring/
    - monitoring_db.py        — monitoring 用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（ETF + マクロセンチメント）
    - __init__.py
  - data/                     — 実行時データディレクトリ（デフォルト: data/）
    - monitoring.db (default SQLITE_PATH)
    - paper_trading.db (paper trading用)
    - kabusys.duckdb (default DUCKDB_PATH)
    - kill.flag, stop_requested.flag, execution.pid 等のランタイムフラグ/ファイル
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度・CPU affinity 設定
    - __init__.py

※ この README はリポジトリ内のソース構造に基づいています。ファイル名や配置は将来の変更により差分が発生する可能性があります。

---

## 運用上の注意（Notes / Best practices）

- 本番（KABUSYS_ENV=live）環境では Kill Switch / LINE 通知（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）などの設定を必ず確認してください。validate_config が本番時に警告を出します。
- .env は機密情報を含むため Git にコミットしないでください（config_setup にも注意書きあり）。
- OpenAI API へのリクエストはコストが発生します。news_nlp や regime_detector の運用頻度・バッチサイズ設定を考慮してください。
- run_execution/run_monitoring はプロセス優先度を高く設定する仕組みを持ちますが、環境（OS 権限）により設定できない場合があります（ログに警告が出ます）。
- DuckDB / SQLite のファイルバックアップやディスク容量には注意してください（ログ・DB が大きくなる可能性があります）。

---

必要であれば、この README を元に「デプロイ手順」「systemd ユニット例」「Dockerfile」「CI 用テスト手順」などの追加ドキュメントも作成します。どの情報が欲しいか教えてください。