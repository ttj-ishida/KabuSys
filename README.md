# KabuSys

KabuSys は日本株の自動売買／リサーチ基盤のための軽量フレームワークです。取引エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、LLM を使ったニュース評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

- 取引実行（ExecutionEngine）やそれを監視する監視プロセス（Monitoring）を含む自動売買基盤。
- Paper trading（ペーパートレード）モードをサポートし、本番 DB と分離して動作可能。
- DuckDB を用いたリサーチ／ファクター計算モジュール。
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント評価と市場レジーム判定。
- システム監視（CPU / メモリ / ディスク / データ鮮度）・リスク監視・Kill Switch 機構による安全停止機能。
- ログ設定、プロセス優先度設定、設定ウィザード／検証ツール等のユーティリティを提供。

---

## 主な機能一覧

- Execution
  - 本番／ペーパートレード切替（`KABUSYS_ENV`）
  - BrokerClientFactory 経由のブローカークライアント
  - OrderManager / RiskManager / Reconciler / ExecutionEngine
- Monitoring
  - SystemMonitor: プロセス稼働・データ鮮度・リソース監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン監視
  - KillSwitch: 条件に基づく停止フラグ（`data/kill.flag`）
  - MonitoringEngine: 各モニタの束ねとアラート発行
  - SQLite に監視ログ永続化（`monitoring_db.py`）
- ポートフォリオ構築（純粋関数）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ
  - DuckDB を使ったファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン・IC 計算等の統計解析ユーティリティ
- AI
  - ニュースの LLM センチメント評価（`ai.news_nlp.score_news`）
  - 市場レジーム判定（`ai.regime_detector.score_regime`）
  - OpenAI のリトライ・レスポンス検証・バッチ処理ロジックを実装
- ツール
  - 環境設定ウィザード（`.env` 生成）: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
  - ペーパートレード検証レポート生成: `kabusys.tools.paper_verification_report`
- ユーティリティ
  - ログ設定（コンソール + 日次ローテーションファイル）
  - プロセス優先度／CPU affinity 設定

---

## 必要環境 / 依存ライブラリ

- Python 3.9+（型アノテーションに Path | None を使用）
- ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイルチェック時に任意で使用）
- SQLite は標準ライブラリで利用

インストール例:
- 仮想環境作成例:
  - python -m venv .venv
  - source .venv/bin/activate
- 必要パッケージ:
  - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして移動
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境作成・有効化（任意）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（下にサンプルを記載）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 問題がある場合は出力を参照して修正。`--strict` を付けると警告もエラー扱い。

6. DB／ログディレクトリの確認
   - デフォルト: `data/`（SQLite, PID, kill.flag など）、`logs/`（ログ）
   - 必要に応じて環境変数でパスを上書き

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード
  - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- DB パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 SQLite, default: data/paper_trading.db)
- OpenAI
  - OPENAI_API_KEY
- ログ / PID / Kill flag
  - LOG_LEVEL (default: INFO)
  - LOG_DIR
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1) — 本番では 0 推奨
- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- Paper trading 動作
  - PAPER_FILL_MODE: instant / partial / never / reject

サンプル .env（最低限の例）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

注意: `.env` は絶対にリポジトリにコミットしないでください。

---

## 実行方法

- 監視ループを起動（常駐プロセス）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）

- ExecutionEngine を起動（取引エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient と paper DB を使用（`PAPER_TRADING_SQLITE_PATH`）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

ログ:
- デフォルトは `logs/<app_name>.log` に日次ローテーションで出力。
- `setup_logging(app_name="execution")` のように起動スクリプトから設定されます。

停止（Kill Switch / Stop flag）:
- 監視や実行プロセスは `data/stop_requested.flag` や `data/kill.flag` 等のフラグファイルを参照します。
- KillSwitch は重大なリスクを検知した際に `data/kill.flag` を書き込んで ExecutionEngine を停止させます。
- ExecutionEngine 起動時には `KILL_FLAG_CLEAR_ON_START` の値に注意（本番で 1 にすると危険）。

---

## ライブラリとしての利用（簡単な例）

- ポートフォリオ関数の呼び出し:
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

- リサーチ関数:
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  from kabusys.research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026,4,1))

- AI スコアリング（ニュース）:
  from kabusys.ai import score_news
  # conn は duckdb connection、target_date は date 型
  score_news(conn, target_date=date(2026,4,01), api_key="YOUR_OPENAI_KEY")

- Market regime:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,4,01), api_key="YOUR_OPENAI_KEY")

注: AI 関連関数は OpenAI API キーの設定（引数または環境変数 OPENAI_API_KEY）が必要です。

---

## 主要ディレクトリ構成

（プロジェクトルートの `src/kabusys` 相対）

- __init__.py
- config.py — 環境変数管理・自動 .env 読み込みロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度設定
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
- execution/ (取引実行関連)
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
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
- monitoring/（上記）
- tools/
  - paper_verification_report.py

（実際のファイル一覧はリポジトリによる）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env の内容を慎重に扱う。`KILL_FLAG_CLEAR_ON_START=1` は本番では避ける。
- .env は絶対にリポジトリへコミットしない（機密情報含む）。
- OpenAI API を呼び出す処理は外部 API 依存のため、レート制限やコストに注意する。APIキー管理を徹底する。
- 監視プロセス（run_monitoring）は本番 sqlite_path を参照します（環境に依らず本番 DB を使用する設計になっている点に留意）。
- paper_trading は本番 DB と分離するために `PAPER_TRADING_SQLITE_PATH` を指定して運用することを推奨。

---

## 追加情報 / トラブルシュート

- ログディレクトリの作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。権限やパスを確認してください。
- psutil のプロセス優先度設定は OS に依存します。権限不足で設定できない場合は警告が出ますが処理は継続します。
- DuckDB / SQLite のパス設定は `.env` で上書き可能。`validate_config` でパスの親ディレクトリ存在等のチェックを行えます。
- テスト用途で自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

README はこのプロジェクトのエントリポイントや開発者向けの簡易ガイドとして作成しました。詳細なモジュール設計・アルゴリズム仕様（PortfolioConstruction.md、StrategyModel.md 等）はリポジトリ内の設計ドキュメントを参照してください。