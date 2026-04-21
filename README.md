# KabuSys

日本株向け自動売買システムの小規模モジュール群です。  
本リポジトリには、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、AI を使ったニュース評価などのユーティリティ群が含まれます。

---

## 概要

KabuSys は以下の目的で構築されたコンポーネント群を含みます。

- 自動発注（ExecutionEngine）と発注管理（OrderManager / RiskManager）
- システム稼働監視、トレード監視、リスク監視および Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- DuckDB を用いたリサーチ／ファクター計算
- OpenAI を利用したニュース NLP（センチメント評価）およびレジーム判定
- ペーパートレード用の検証レポート生成ツール
- 環境設定ウィザード・設定検証ツール

設計上のポイント：
- DB 層は SQLite（監視・ペーパートレード）と DuckDB（分析）を併用
- 環境変数 / .env による設定管理（config_setup.py で対話的に生成）
- 実行スクリプトは `python -m kabusys.<module>` で起動可能
- AI 部分は OpenAI API キーを必要とする（フォールバックや失敗時の安全処理あり）

---

## 主な機能一覧

- execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - paper_trading 環境では MockBrokerClient を使用し、本番 DB と分離された `data/paper_trading.db` を使用
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）による安全停止
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねるポーリングループ（run_monitoring.py）
  - システム資源（CPU/メモリ/ディスク）、プロセス生存、データ鮮度の監視
  - KillSwitch（条件に応じて `data/kill.flag` を書き込み、Execution を停止）
- portfolio
  - 候補選定、等配分／スコア配分の重み計算
  - セクター上限の適用、レジーム乗数算出
  - ポジションサイズ計算（lot 単位丸め、aggregate cap のスケール調整）
- research
  - DuckDB を使ったファクター計算（モメンタム・ボラティリティ・バリュー 等）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- ai
  - news_nlp: ニュースを LLM で評価し ai_scores テーブルへ書き込む
  - regime_detector: ETF（1321）の MA200 とマクロニュースを組み合わせて市場レジームを判定
- tools
  - paper_verification_report: ペーパートレード DB から検証レポート生成
- CLI/ユーティリティ
  - config_setup: .env を対話式で生成/更新
  - validate_config: 起動前の設定検証（必須環境変数・config/*.yaml・DB パス等）

---

## 必要条件（依存パッケージ）

最低限必要な外部ライブラリ（例）：
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- PyYAML（config/*.yaml の構文チェックを行う場合に任意で必要）

例（pip）:
pip install duckdb psutil openai PyYAML

※ requirements.txt は本リポジトリに含まれていないため、プロジェクト用途に合わせて requirements を作成してください。

---

## セットアップ手順

1. リポジトリをクローン／取得する
   - 任意のディレクトリに配置してください。

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 手動で作成する場合はプロジェクトルートに `.env` を配置

5. データディレクトリ
   - デフォルトでは `data/`、ログは `logs/` に出力されます。自動生成されますが、権限等が必要な環境では事前に作成してください。

---

## 主要な環境変数（概要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

AI 関連:
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）

その他（代表例・デフォルトを併記）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring の上書き用）
- PAPER_FILL_MODE — paper_trading の MockBroker 動作 ("instant" | "partial" | "never" | "reject")
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか ("0" / "1")

.env の例（抜粋）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 設定検証 / ウィザード

- .env 対話式ウィザード:
  - python -m kabusys.config_setup
  - 既存 .env を読み込み、対話的に編集・保存できます。

- 設定検証 CLI:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）扱いになります。

---

## 使い方（起動 / コマンド例）

- ExecutionEngine を起動（本番／ペーパートレードいずれも）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading では MockBrokerClient を使用し、データは `data/paper_trading.db` に記録されます。
  - 起動時に `data/stop_requested.flag` があれば起動せず終了します。
  - 実行中は `data/execution.pid`（デフォルト）に PID を書き込みます。
  - 停止フラグ（手動で停止）:
    - `data/stop_requested.flag` を作成すると監視ループ / エンジンが安全に停止します。
    - KillSwitch は `data/kill.flag` を作成して ExecutionEngine の停止を指示します（Monitoring が条件を満たしたときに書き込む）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）を使用します。監視は env にかかわらず本番 sqlite_path を使用します（設計上の注意点）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI モジュールをプログラムから呼び出す（例）
  - news_nlp.score_news(conn, target_date, api_key=...)  — DuckDB 接続を渡してニューススコアを ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=...) — market_regime テーブルへ書き込む
  - 直接 CLI は用意されていないため、スクリプト内から呼び出します。OpenAI API キーが必要です。

---

## ログと実行環境

- ログはデフォルトで `logs/<app_name>.log`（日次ローテーション・30 日保持）へ出力され、コンソールにも出力されます。
- ロギング設定は `kabusys.utils.logging_setup.setup_logging(app_name=...)` によって統一的に行われます。
- プロセス優先度は起動時に `kabusys.utils.process_priority.set_process_priority("high")` で高優先度に設定を試みます（権限がない場合は警告）。

---

## 停止・KillSwitch の仕組み

- data/stop_requested.flag
  - run_monitoring / run_execution のループがこのファイルの存在を監視し、存在すれば安全にループを抜けます（管理者が即時停止したい場合に使用）。
- data/kill.flag
  - Monitoring の KillSwitch がリスク条件を満たした場合に書き込むことで、ExecutionEngine 側の停止を誘発します。
  - KillSwitch は冪等（既存ファイルへの上書きは行わない）です。
- KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

---

## 主要ファイル・ディレクトリ構成

プロジェクト内の主な構成（抜粋）:

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理（.env 自動ロード含む）
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — Monitoring 起動スクリプト

kabusys/
- execution/                      — 発注関連（OrderManager, ExecutionEngine, BrokerFactory 等）
- monitoring/
  - monitoring_db.py              — SQLite 操作用ラッパー
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

プロジェクトルート:
- .env (ユーザー作成)
- data/ (DB、フラグファイル等: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid)
- logs/ (ログ出力先)

---

## 開発・デバッグ時のヒント

- .env の自動ロード:
  - `kabusys.config` はプロジェクトルート（.git または pyproject.toml を起点）から .env を自動ロードします。
  - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（主にテスト用途）。
- config/*.yaml の存在チェックは validate_config が行います。PyYAML が無い場合は YAML の中身チェックをスキップします（警告が出ます）。
- DuckDB / SQLite のパスの親ディレクトリが存在しない場合は警告が表示されます（起動時に自動作成されることが多いです）。
- AI API 呼び出し部分はリトライ・フォールバックの実装があり、失敗時は安全にゼロやスキップで継続する設計です。テスト時は API 呼び出しをモックすることを推奨します。

---

## ライセンス / バージョン

- パッケージバージョンは `kabusys.__version__ = "0.1.0"`（初期バージョン）。
- 本 README はコードベースから生成した概要です。具体的なライセンス表記や配布ポリシーはプロジェクトルートで管理してください。

---

何か特定のセクション（例: 実行例の詳細、.env の完全テンプレート、テスト方法や CI 設定）を追記したい場合は教えてください。必要に応じてサンプル .env、起動スクリプトの具体的なコマンド例、Docker/Docker Compose の雛形なども用意できます。