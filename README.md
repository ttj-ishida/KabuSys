# KabuSys

日本株自動売買システムのコアライブラリ／ツール群です。バックテストやポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）や AI を使ったニューススコアリングなどのコンポーネントを含みます。

---

## 概要

このリポジトリは、以下の主要機能を備えた自動売買プラットフォームの一部実装です。

- 銘柄選定・配分（Portfolio construction）
- 発注／注文管理・リスク制御（ExecutionEngine, RiskManager, OrderManager）
- 監視（System / Trade / Risk の定期チェック、Kill Switch）
- 研究用ファクター計算（Momentum / Value / Volatility 等）
- ニュースの NLP スコアリング（OpenAI を利用）
- ペーパートレード用の検証レポート生成ツール

設計方針として、可能な限り副作用を抑え、DB 接続を明示的に受け取る純粋関数群（研究／ポートフォリオ）と、永続化層（SQLite / DuckDB）を分離しています。

---

## 機能一覧（抜粋）

- 環境設定ウィザード: `kabusys.config_setup`（.env の対話的作成）
- 設定検証 CLI: `kabusys.validate_config`（.env、config/*.yaml の事前チェック）
- 発注エンジン起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker（paper DB に記録）
- 監視ループ起動スクリプト: `kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- 監視 DB ラッパー / モニター実装（system, trade, risk）
- Kill Switch（`data/kill.flag`）による安全停止
- ニュース NLP スコアリング（OpenAI API を使用）: `kabusys.ai.news_nlp.score_news`
- 市場レジーム判定（LLM + ETF MA 合成）: `kabusys.ai.regime_detector.score_regime`
- 研究用モジュール（DuckDB を用いたファクター計算、IC 計算 等）
- ペーパートレード検証レポート生成ツール: `kabusys.tools.paper_verification_report`

---

## セットアップ手順

1. Python 仮想環境を用意
   - python 3.10+ を推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 最低限:
     - duckdb
     - psutil
     - openai
   - optional:
     - PyYAML（`validate_config` が config/*.yaml のパース検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt が無い場合は上記を手動でインストールしてください）

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります: python -m kabusys.validate_config --strict

4. ディレクトリ（logs, data 等）の確認
   - ログはデフォルトで `logs/` に保存されます（`LOG_DIR` 環境変数で変更可能）。
   - データベースのデフォルト:
     - DuckDB: `data/kabusys.duckdb`（`DUCKDB_PATH`）
     - SQLite (monitoring): `data/monitoring.db`（`SQLITE_PATH`）
     - Paper trading SQLite: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH`）

---

## 使い方（主要コマンド例）

環境変数は .env に記載するか、実行前にエクスポートしてください。`.env` 自動ロードはデフォルトで有効です（必要なら `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化）。

- .env の生成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV が `paper_trading` のときは paper DB（`PAPER_TRADING_SQLITE_PATH`）を使用
    - ExecutionEngine の停止は `data/stop_requested.flag`（プロジェクトルート）を作成することでスレッドを終了させます
    - 実行時に PID ファイル（デフォルト `data/execution.pid`）を作成します

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=30（秒）
  - Monitoring は環境に関係なく本番の sqlite_path を利用して監視テーブルを初期化します
  - 停止: `data/stop_requested.flag` を作成するとループが終了します

- Kill Switch（Execution 停止用）
  - KillSwitch は `data/kill.flag` を書き込んで ExecutionEngine に停止を促します
  - 直接実行する例:
    - echo "reason..." > data/kill.flag
  - 削除してクリア:
    - rm data/kill.flag
  - .env の `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動でクリアします（本番では注意）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / 研究系関数の利用（ライブラリとして）
  - ニューススコアリング（プログラム内から呼び出し）
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

---

## 主要な環境変数（抜粋）

必須（起動前に設定が必要なもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper トレード専用 SQLite（paper_trading 用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

（すべては config_setup のウィザードおよび validate_config で確認可能）

---

## 停止・フラグ関連

- 停止要求（プロセス側の自発停止）
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します
- Kill Switch（自動的に ExecutionEngine を止める仕組み）
  - Monitoring の判定で `data/kill.flag` が書き込まれると Execution 側でチェックして停止します
  - `KILL_FLAG_CLEAR_ON_START=1` による自動クリアは本番環境では推奨されません（安全対策）

---

## ログ・DB・出力

- ログ:
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler で日次ローテーション、30日保持）
  - コンソールは stdout に出力
- DB:
  - Monitoring 用 SQLite: デフォルト data/monitoring.db
  - DuckDB: 分析用データベース data/kabusys.duckdb
  - Paper trading SQLite: data/paper_trading.db（paper_trading 向け）
- 既存 DB に対するマイグレーション処理（monitoring_db.init_monitoring_db）でカラム追加等を行います

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
- execution/
  - execution_engine.py
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
- data/
  - pipeline.py
  - stats.py
- monitoring/
  - monitoring_db.py
- utils/
  - logging_setup.py
  - process_priority.py

（上記はコードベースから抜粋した主要ファイルの一覧です。実際のレポジトリではさらにファイルが存在する場合があります。）

---

## 開発・拡張メモ

- DuckDB 接続を受け取る関数群は副作用を持たないよう設計されているため、テストが容易です。
- OpenAI 呼び出しはリトライや JSON バリデーション等の堅牢化処理を実装済みですが、API 仕様変更やレート制限への対応は運用で監視してください。
- 本番運用時は KABUSYS_ENV=live、適切な LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を忘れずに。

---

問題や実行上の不明点があれば、実行ログ（logs/）や validate_config の出力を確認してください。必要なら README を補足します。