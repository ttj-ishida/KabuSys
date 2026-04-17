# KabuSys — README (日本語)

このドキュメントはこのリポジトリの概要、使い方、セットアップ手順、主要機能、ディレクトリ構成をまとめたものです。

注意: 本 README はソースコード（src/kabusys 以下）を基に作成しています。実行前に `.env` を正しく設定してください（config_setup で対話的に生成可能）。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究プラットフォームです。  
主な機能は以下の通りです。

- 戦略のためのファクター計算・研究モジュール（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 実行エンジン（ExecutionEngine）とブローカークライアント（実取引 / ペーパートレード対応）
- 監視（System / Trade / Risk Monitor）と Kill Switch（異常時に発注停止）
- ニュース NLP（OpenAI を利用したセンチメント評価）とレジーム判定
- 各種ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

設計上のポイント:
- DuckDB を分析用 DB、SQLite を監視・トレードログ用 DB として利用
- 環境による DB 分離（`paper_trading` モードでは paper_trading 用 SQLite を使用）
- OpenAI を使った NLP 処理は API キー必須（フェイルセーフ設計あり）
- 自動環境変数読み込み（プロジェクトルートの `.env` / `.env.local`）

---

## 主な機能一覧

- research/
  - ファクター計算 (momentum, volatility, value)
  - 将来リターン・IC・統計サマリー
- portfolio/
  - 候補選定（スコア順）、等配分 / スコア加重配分
  - ポジションサイズ計算（リスクベース等）
  - セクター制限・レジーム乗数適用
- execution/（実装参照）
  - BrokerClientFactory による本番 / モック切替（`paper_trading`）
  - ExecutionEngine, OrderManager, RiskManager 等
- monitoring/
  - SystemMonitor（CPU/メモリ/ディスク、プロセス監視、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件により `data/kill.flag` を書き込み発注停止）
  - AlertManager（LINE Push での通知、クールダウン制御）
- ai/
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント評価（ai_scores に書き込み）
  - regime_detector: マクロ + ETF MA200 による市場レジーム判定
- tools/
  - paper_verification_report: ペーパートレード DB から検証レポートを生成
- 設定系
  - config_setup.py: 対話式 `.env` 生成ウィザード
  - validate_config.py: 起動前の設定検証 CLI

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールします（最小限の例）。
   - 例:
     - pip install duckdb psutil openai requests pyyaml

   実際の requirements.txt がある場合はそれを使用してください。

3. 環境変数（.env）を作成します（対話ウィザード推奨）。
   - 実行:
     - python -m kabusys.config_setup
   - ウィザードで入力した内容はプロジェクトルートの `.env` に保存されます。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
   - 任意 / 既定値:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（DEBUG 等に変更可）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、未設定でも動作）

4. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ準備（必要に応じて）:
   - デフォルトの DB/フラグファイルは `data/` 以下を参照します。自動作成されますが、パーミッション等を確認してください。

---

## 使い方（起動コマンド例）

プロセス優先度や PID ファイル、停止フラグ制御などが組み込まれています。

- 監視ループ（System / Trade / Risk の定期チェック）を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視プロセスは常に「本番用の sqlite_path」を使用します（環境に関係なく monitoring は production DB を参照）。

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録（本番 DB と分離）します。
  - 起動時はプロセス優先度を "high" に設定し、`data/execution.pid` に PID を書きます（実行管理用）。
  - 停止: `data/stop_requested.flag` を作成するとループが検知して安全に停止します。

- 設定ウィザード（.env の初期作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - オプション `--db PATH` で SQLite パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）。

- AI 機能（プログラムから呼ぶ例）:
  - news NLP（指定日でニュースをスコア化）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # conn は duckdb 接続
  - レジームスコア:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

注意: AI 機能を使う場合は OPENAI_API_KEY を環境変数または引数で渡す必要があります。

---

## 重要なファイル / フラグ / デフォルトパス

- DB / ファイル:
  - DuckDB: data/kabusys.duckdb （環境変数 DUCKDB_PATH で変更可）
  - SQLite (monitoring): data/monitoring.db （環境変数 SQLITE_PATH）
  - SQLite (paper trading): data/paper_trading.db （PAPER_TRADING_SQLITE_PATH）
  - PID ファイル: data/execution.pid（ExecutionEngine が利用）
  - Kill flag: data/kill.flag（KillSwitch が書き込む）
  - Stop requested: data/stop_requested.flag（run_* スクリプトが監視している停止フラグ）

- 環境変数（代表的なもの）
  - 必須:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
  - 任意 / 推奨:
    - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
    - OPENAI_API_KEY — AI 機能に必要
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - LOG_LEVEL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート通知用

- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔（秒）を上書き（デフォルト 60）。不正値（<=0 等）はデフォルトにフォールバック。

---

## 停止・Fail-safe の仕組み

- run_monitoring / run_execution はプロジェクトルートの `data/stop_requested.flag` を監視しており、存在すると安全にループを終了します（グレースフルシャットダウン）。
- KillSwitch（監視コンポーネント）は条件を満たした場合 `data/kill.flag` を作成し、ExecutionEngine 側で検出して取引を停止します。
- AI API 呼び出しはリトライ・サニティチェックを備え、失敗時はスコアを 0 にフォールバックする等、フェイルセーフな挙動を意図しています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロ）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化操作
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
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py     — psutil を使った優先度 / CPU affinity ユーティリティ
  - その他:
    - execution/ (発注関連)
    - data/ (実行時に生成される DB / フラグファイル 等)
    - config/ (yaml テンプレート等)

---

## 開発・運用上の注意点

- 本番環境 (KABUSYS_ENV=live) 設定時は特に注意してください。validate_config による事前チェックを強く推奨します。
- `KILL_FLAG_CLEAR_ON_START=1` は本番で危険になり得ます（Kill Switch を自動クリアします）。
- psutil によるプロセス優先度設定は OS に依存します（Windows / POSIX の差を吸収するロジックあり）。権限不足等で設定に失敗した場合はログに警告が出てスキップされます。
- DuckDB / SQLite のパスは環境変数で上書き可能です。Paper Trading は専用 SQLite（分離）を使うため、本番 DB を汚染しません。
- OpenAI の API 呼び出しはコストがかかります。運用時は API 呼び出し頻度・バッチサイズ・リクエスト制御を検討してください。

---

## よく使うコマンドまとめ

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はリポジトリのコードに基づいて作成しています。さらに詳細な使用方法や設計仕様はソースコード内の docstring / コメントを参照してください。必要なら README にサンプル設定（.env.example）や運用手順、図解を追加できますので要望があれば教えてください。