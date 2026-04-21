# KabuSys

日本株自動売買システムのライブラリ／ツール群。ポートフォリオ構築、リサーチ、監視、実行（ExecutionEngine）、Paper Trading 用ユーティリティ、AI ニュース解析などの機能を提供します。

注意: この README はリポジトリ内のソースコード（`src/kabusys/`）をもとに手動で作成しています。実行前に必ず `.env` を作成し、`python -m kabusys.validate_config` で設定を検証してください。

## 概要（Project overview）

- 戦略・ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定・重み計算（等分配 / スコア加重）
  - ポジションサイジング（リスクベース、等分配 等）
  - セクターキャップ、レジーム乗数などのリスク調整
- リサーチモジュール（DuckDB を使ったファクター計算、将来リターン、IC 計算等）
- AI モジュール（OpenAI を使ったニュースセンチメント、レジーム判定）
- Execution（発注エンジン）と Monitoring（監視）
  - ExecutionEngine は環境に応じて本番または Paper Trading（モックブローカー）で動作
  - Monitoring はシステム状態、注文ログ、リスクを定期チェックしてアラートや Kill Switch を発動可能
- 各種 CLI/スクリプト
  - 環境設定ウィザード（`.env` 作成補助）
  - 設定検証ツール
  - Paper Trading 検証レポート生成ツール

## 主な機能一覧（Features）

- 環境管理
  - .env 自動ロード（プロジェクトルートに基づく）
  - `config_setup.py` による対話式 .env 作成
  - `validate_config.py` による事前検証（必須環境変数のチェック、config/*.yaml の存在確認等）
- 実行エンジン（Execution）
  - Live / Paper Trading に対応（`KABUSYS_ENV`）
  - Paper Trading は本番 DB と完全分離（デフォルト: `data/paper_trading.db`）
  - RiskManager、OrderManager、Reconciler 等のコンポーネント
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる `MonitoringEngine`
  - SQLite に監視ログを永続化（`data/monitoring.db`）
  - Kill Switch により重大リスクで Execution を停止可能（`data/kill.flag`）
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を調整（デフォルト 60 秒）
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン・IC（Spearman）・ファクター統計サマリ
- ポートフォリオ構築
  - 候補選別、等重 / スコア重み、リスクベースの株数決定、セクター上限適用
- AI（OpenAI）
  - ニュースを LLM（gpt-4o-mini）でスコアリングして `ai_scores` に保存
  - マクロニュース + ETF MA に基づく市場レジーム判定
  - リトライ・JSON バリデーション等の堅牢な実装
- ツール
  - Paper Trading 検証レポート出力（稼働率、成功率、レイテンシ等）

## セットアップ手順（Setup）

1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートにする（`pyproject.toml` / `.git` が存在するディレクトリ）。

2. Python 仮想環境を作成して有効化（例）:
   - python >= 3.9 推奨
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 必要なパッケージをインストール（最低限の依存）:
   - duckdb
   - psutil
   - openai
   - PyYAML（`validate_config.py` で YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   実際のプロジェクトでは `requirements.txt` や `pyproject.toml` があればそちらを利用してください。

4. ディレクトリ作成:
   - デフォルトでは下記のデータ/ログパスを使用します。必要に応じて手動で作成してください（`logging_setup` は自動作成を試みますが権限等で失敗する場合があります）。
     - data/（SQLite DB、PID・フラグファイル用）
     - logs/（ログ出力）

5. .env (環境変数) を用意:
   - `python -m kabusys.config_setup` を実行して対話式ウィザードで `.env` を作成できます。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY（各 AI 関数は引数でキーを受け取ることも可能）
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（default: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: DEBUG/INFO/...
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の挙動）

6. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL にする

## 使い方（Usage / 実行例）

- 実行エンジン起動（ExecutionEngine）
  - 本番/ペーパーは `KABUSYS_ENV` に依存
  - python -m kabusys.run_execution

  挙動メモ:
  - 起動時にプロセス優先度を "high" に設定（`utils.process_priority.set_process_priority`）
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録（本番 DB と分離）
  - `data/stop_requested.flag` が存在すると起動せず終了

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き（デフォルト 60）
  - 監視は本番の `settings.sqlite_path`（`SQLITE_PATH`）を使用（KABUSYS_ENV に依存しない）
  - `data/stop_requested.flag` の検出でループを終了

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（`PAPER_TRADING_SQLITE_PATH` 環境変数の代替）

- AI 関連（スクリプト化されているエントリポイントはないが、モジュールとして利用可能）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

- ログ設定:
  - 各スクリプトは最初に `kabusys.utils.logging_setup.setup_logging(app_name="...")` を呼び出します。
  - デフォルトログディレクトリ: logs/
  - ローテーション: 日次、30 日保持

## 実行制御 / フラグ類

- stop_requested.flag
  - run_execution.py/run_monitoring.py はプロジェクトの data/stop_requested.flag を監視し、存在時に安全に停止します。
- execution.pid
  - ExecutionEngine が PID を書き込む（`data/execution.pid` デフォルト）。
- kill.flag
  - Kill Switch（`monitoring.kill_switch`）が検出条件を満たすと `data/kill.flag` を書き込み、Execution 側が停止を検討するための信号とします。
  - `KILL_FLAG_CLEAR_ON_START` 環境変数で起動時に自動クリアする挙動を制御（本番では 0 推奨）。

## ディレクトリ構成（Directory structure）

リポジトリ内の主要なモジュール構成（`src/kabusys/` を基準）:

- kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理（自動 .env ロード）
  - config_setup.py        — 対話式 .env 生成ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 用レポート生成
  - utils/
    - logging_setup.py     — 共通ログ設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py     — SQLite スキーマ / 永続化 API
    - monitoring_engine.py — 監視エンジン（各 Monitor を束ねる）
    - system_monitor.py    — システム状態 / データ鮮度監視
    - trade_monitor.py     — （注文関連監視: ソースに含まれる）
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — Kill Switch 実装（kill.flag 書き込み）
    - alert_manager.py     — アラート送信（LINE 等）
  - execution/
    - execution_engine.py  — ExecutionEngine 本体
    - broker_factory.py    — BrokerClient の生成（本番 / mock の切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py   — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py          — ニュースの LLM ベーススコアリング
    - regime_detector.py   — マクロ+ETF MA によるレジーム判定

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development | paper_trading | live（default: development）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用監視 DB（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、monitoring スクリプト用）

詳細や追加設定項目は `kabusys.config.Settings` のプロパティや `config_setup.py` の定義を参照してください。

## 注意事項 / 運用上のヒント

- 本番運用時は `KABUSYS_ENV=live` を設定し、`validate_config.py` の警告を必ず確認してください。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険（kill flag を自動で消してしまう）ため、本番では 0 を推奨します。
- Monitoring は KABUSYS_ENV にかかわらず本番の `SQLITE_PATH` を使う実装部分があるため、監視 DB に対するアクセス権・バックアップ計画を用意してください。
- OpenAI を使う機能は API コスト・レイテンシが発生します。API キーのレート制限や利用状況に注意してください（モジュールにはリトライ・バックオフロジックを含みます）。
- ログは `logs/` に日次ローテーションで保存されます。ディスク容量管理を行ってください。

---

上記はコードベースの主要な使い方・構成の概要です。実際に導入・運用する際は、プロジェクト内の `config/*.yaml`（存在する場合）や各モジュールのドキュメント、`config_setup.py` / `validate_config.py` の出力を参照して詳細設定を行ってください。必要があれば README を補足します—追加で載せたい内容（例: docker-compose、systemd unit サンプル、CI 設定等）があれば教えてください。