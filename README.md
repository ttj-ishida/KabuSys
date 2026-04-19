# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買 / 研究 / 監視用ユーティリティ群をまとめたものです。  
以下はコードベース（src/kabusys 以下）に基づく README（日本語）です。

---

## プロジェクト概要

KabuSys は以下を目的とした小規模な自動売買プラットフォームのコンポーネント群です。

- 発注・約定の実行エンジン（ExecutionEngine）
- システム稼働・注文・リスクの監視（Monitoring）
- ポートフォリオ構築・ポジションサイジング等の純関数ライブラリ（portfolio）
- DuckDB を使ったリサーチ / ファクター計算（research）
- ニュース NLP を用いた AI スコアリング・レジーム判定（ai）
- 各種ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の要点：
- 本番（live）・ペーパートレード（paper_trading）を明確に分離
- DB（SQLite / DuckDB）を中心とした永続化
- 自動監視・Kill Switch による安全停止機構
- OpenAI を利用する NLP 部分は API キー必須かつフェイルセーフ実装

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアント切替（本番 / モック）
  - ペーパートレード用専用 SQLite DB 分離（data/paper_trading.db）
  - 停止フラグ / PID 管理

- Monitoring
  - SystemMonitor（CPU・メモリ・ディスク、データ鮮度、プロセス死活検知）
  - TradeMonitor（注文の滞留・約定異常検出）
  - RiskMonitor（ドローダウン、ポジション上限検知）
  - KillSwitch（危険時に data/kill.flag を書き込んで Execution を停止）
  - 監視ポーリングループ起動スクリプト（run_monitoring.py）
  - 監視ログ永続化（monitoring_db.py：system_status / trade_logs / positions / risk_logs / dashboard）

- Portfolio（純関数）
  - 候補選定 / 重み付け（等額・スコア重み）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ算出（ロット整形・利用可能現金でのスケーリング）

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・統計サマリー（外部 pandas 依存なし、DuckDB 経由）

- AI
  - ニュースベースの銘柄センチメントスコアリング（OpenAI）
  - マクロニュースと価格指標に基づく市場レジーム判定（OpenAI）
  - API エラーに対するリトライ / バックオフ / フェイルセーフを実装

- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発 / ローカル実行向け）

前提：
- Python 3.10+（typing の union 表記等に合わせてください）
- Git, SQLite, （任意で DuckDB CLI）

例: 仮想環境 + 必要パッケージのインストール

1. リポジトリを取得する
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検証を行う場合）
   - 例:
     - python -m pip install --upgrade pip
     - python -m pip install duckdb psutil openai pyyaml

   ※ 実際の requirements.txt がある場合はそれを使用してください。

4. data / logs ディレクトリを作成
   - mkdir -p data logs

5. .env の準備
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - これが .env を生成します（.env は決して Git にコミットしないでください）
   - もしくは .env を手動で作る（必要な環境変数は下記参照）

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

---

## 必須 / 主要な環境変数

最低限設定が必要なもの（README 内のコードに基づく）：

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- OPENAI_API_KEY — OpenAI を用いる機能（ai.score_news / score_regime）で必要
- PAPER_FILL_MODE — ペーパートレードの約定動作（instant|partial|never|reject、デフォルト: instant）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_DIR / LOG_LEVEL — ログ出力先 / レベル（logging_setup が参照）

注意:
- .env 自動ロードはプロジェクトルートに .git または pyproject.toml がある場合に行われます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

---

## 使い方（実行例）

- 監視ループの起動（監視プロセス）
  - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（秒、デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は .env の設定にかかわらず monitoring は本番 sqlite_path を使用する（監視ログは共通 DB）

- 実行エンジン（ExecutionEngine）起動
  - KABUSYS_ENV=paper_trading のときは MockBroker を利用し、Paper Trading 用 DB に記録
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動しない
  - 実行はデーモンスレッドで行われ、同フラグや外部からの kill.flag によって停止する

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付与すると警告も失敗扱いで exit 1

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング / レジーム判定（ライブラリ API）
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - どちらも DuckDB 接続を受け取り、api_key（OpenAI）を引数または環境変数 OPENAI_API_KEY で指定

ログ:
- ログは logs/<app_name>.log に日次ローテートで保存されます（デフォルト logs ディレクトリ）。
- setup_logging(app_name="execution" や "monitoring") が各起動スクリプトで利用されています。

停止 / Kill Switch:
- data/kill.flag — KillSwitch によって書き込まれる停止フラグ。ExecutionEngine はこれを検知して安全停止します。
- data/stop_requested.flag — run_execution / run_monitoring の外部停止フラグ（スクリプトでチェック）として使用されます。
- data/execution.pid — ExecutionEngine の PID 保存先（デフォルト）

MONITOR_POLL_INTERVAL:
- run_monitoring のポーリング周期を指定する環境変数（秒）。整数値 1 以上。無効値は 60 秒にフォールバック。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル / パッケージの一覧（この README の作成時点での抜粋）:

- src/kabusys/
  - __init__.py (バージョン等)
  - config.py (環境変数読み込み・Settings クラス)
  - config_setup.py (対話式 .env ウィザード)
  - validate_config.py (設定検証 CLI)

  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)

  - utils/
    - logging_setup.py (ログ設定ユーティリティ)
    - process_priority.py (プロセス優先度 / CPU affinity 設定)
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - monitoring_engine.py (各 Monitor を束ねるエンジン)
    - system_monitor.py (CPU/メモリ/データ鮮度監視)
    - risk_monitor.py (ドローダウン / ポジション上限監視)
    - kill_switch.py (kill flag 書き込みロジック)
    - trade_monitor.py (滞留注文・約定異常検出)  ※存在する想定（コードベースに依存）

  - execution/  (発注関連の実装ファイル群: broker_factory, execution_engine, order_manager, etc.)
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
    - news_nlp.py (ニュースセンチメントスコアリング)
    - regime_detector.py (市場レジーム判定)
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

data/ と logs/ はリポジトリルートで使用される（DB/フラグ/PID/ログ）。

---

## 注意事項・運用上のヒント

- .env は決してリポジトリにコミットしないでください（API トークン等を含む）。
- 本番実行（KABUSYS_ENV=live）時は特に kill flag / LOG_LEVEL 等を慎重に設定してください。
- OpenAI を使う機能は API 利用量・レイテンシ・料金の考慮が必要です。API 失敗時はフェイルセーフでスコアを 0 にする設計です。
- monitor / execution の停止は data/stop_requested.flag の作成または KillSwitch により行います。運用上、停止フラグファイルの管理ルールを決めてください。
- DuckDB / SQLite のパスは Settings によりデフォルトが設定されていますが、運用環境に合わせて .env で上書きしてください。

---

この README はコードベースの説明に基づいて作成しています。実運用前に必ず python -m kabusys.validate_config で設定チェックを行い、.env の必須項目を埋めてください。必要であれば README をプロジェクト固有の運用ルールに合わせて補足してください。