# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・研究・監視ツール群です。本リポジトリは以下の機能を含むモジュール群で構成されています: 注文実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・ポジションサイジング、リサーチ用ファクター計算、AI を使ったニュースセンチメント評価、ユーティリティ類。

この README は日本語での簡易ドキュメントです。開発者向けの CLI とライブラリ API の使い方、セットアップ手順、主要ファイル構成をまとめています。

## 主な概要

- 実行環境切替: KABUSYS_ENV により `development` / `paper_trading` / `live` を切替可能
- 実行スクリプト:
  - 実注文エンジン起動: run_execution.py
  - 監視ループ起動: run_monitoring.py
  - 設定ウィザード: config_setup.py
  - 設定検証: validate_config.py
  - ペーパートレード検証レポート: tools/paper_verification_report.py
- データ永続化:
  - SQLite: 監視・発注ログ等（デフォルト: data/monitoring.db、ペーパー用は data/paper_trading.db）
  - DuckDB: 時系列データ / リサーチ用（デフォルト: data/kabusys.duckdb）
- AI: OpenAI（gpt-4o-mini 想定）を用いたニュース NLP（news_nlp）、レジーム判定（regime_detector）
- ログ: logs/<app_name>.log（TimedRotatingFileHandler、デフォルト 30 日保持）

## 機能一覧

簡潔に主要機能を列挙します。

- Execution
  - ExecutionEngine による発注管理、リスク管理、OrderRepository による永続化
  - Paper Trading モードでは MockBrokerClient を使用し、本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- Monitoring
  - SystemMonitor: CPU/Mem/Disk、プロセス監視、データ鮮度チェック
  - TradeMonitor: 発注ログ/約定の監視（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン・ポジション数上限監視、Kill Switch 生成
  - MonitoringEngine: 上記を定期ポーリングしアラート発報
- Portfolio construction
  - 候補選定 / 等配分・スコア加重配分 / ポジションサイズ計算（ロット丸め、利用可能金額でスケール）
  - セクター上限適用、レジーム乗数（bull/neutral/bear）
- Research
  - DuckDB 上でのファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュースセンチメント集約と ai_scores への書き込み（OpenAI API）
  - 市場レジーム判定（ETF ma200 乖離 + マクロセンチメント）
- ツール
  - 設定ウィザード（対話式 .env 作成）
  - 設定検証 CLI（.env / config/*.yaml の簡易チェック）
  - Paper Trading の検証レポート出力

## セットアップ手順

前提: Python 3.10+ を推奨（typing の `X | None` などを使用）。

1. リポジトリをクローン / 展開
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール（最小例）
   - pip install duckdb psutil openai
   - PyYAML は config の YAML 検証（validate_config）で任意: pip install pyyaml
   - その他、プロジェクトで要求されるパッケージがあれば Pipfile / requirements.txt を参照してください
4. .env の作成
   - 対話式生成: python -m kabusys.config_setup
   - もしくは .env.example を参照して手動で .env を作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict
6. 必要なディレクトリの作成（自動で作られることもあるが事前準備推奨）
   - data/
   - logs/

注意:
- 自動 .env ロードはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Paper Trading は KABUSYS_ENV=paper_trading に設定すると mock ブローカーを使用し data/paper_trading.db を使用します（本番 DB と分離）。

## 使い方

主要な CLI／起動方法の例を示します。

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading に設定するとペーパートレード用 DB を使用（PAPER_TRADING_SQLITE_PATH で上書き可）
  - 実行はスレッドで行われ、data/stop_requested.flag を作成すると優雅に停止します

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定例:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH からも DB を参照します

- プログラム内 API の利用例（Python REPL 等）
  - 設定アクセス:
    - from kabusys.config import settings
    - settings.sqlite_path, settings.env など
  - AI スコアリング呼び出し（DuckDB コネクションを渡す）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

- ログ
  - logs/<app_name>.log に日次ローテーションで出力（デフォルト logs/）
  - ログレベルは LOG_LEVEL 環境変数で制御（例: DEBUG/INFO/...）

- Kill / Stop 操作
  - 実行エンジンを停止させたい場合:
    - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して停止します
  - Execution 停止トリガー（Kill Switch）:
    - monitoring が条件を満たした場合 data/kill.flag が書き込まれ、ExecutionEngine は起動時または稼働中にこれを参照して停止します
  - PID ファイル:
    - 実行時に data/execution.pid（デフォルト）が生成され、外部からプロセス管理を行う際に参照できます

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパー用）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LOG_LEVEL: ログレベル（例: INFO）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 実行時に kill.flag を自動クリアするか（0/1）

## ディレクトリ構成

以下は主要なソースパス（src/kabusys）を示します。実際のリポジトリルート下に data/ や logs/、config/ 等が存在します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（Settings, 自動 .env ロード）
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py      — レジーム判定（ETF MA + マクロセンチメント）
  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定、重み計算
    - position_sizing.py      — 発注株数計算（ロット丸め、集約キャップ）
    - risk_adjustment.py      — セクター上限、レジーム乗数
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラ / バリュー等の計算（DuckDB）
    - feature_exploration.py  — 将来リターン、IC、統計サマリ
  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層（system_status 等）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （コード内にあり）注文監視ロジック
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch（kill.flag）の管理
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信ロジック、LINE など）
  - execution/
    - broker_factory.py      — ブローカークライアント生成（本番 / モック）
    - execution_engine.py    — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/ (上記)
  - utils/
    - logging_setup.py       — 統一ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - data/ など（実行時に利用されるディレクトリ、DB、フラグファイル）

※ファイルによっては README の抜粋に掲載されていない補助モジュールがあります。実装詳細は各モジュールの docstring を参照してください。

## 開発・運用上の注意

- 本番モード（KABUSYS_ENV=live）では設定ミスが重大となるため validate_config の実行を推奨します。
- .env を絶対に Git にコミットしないでください（config_setup がヘッダに注意書きを入れます）。
- OpenAI API を使う処理は外部 API 呼び出しのため、レートリミットや失敗の取り扱いを考慮して運用してください（コード中にリトライやフォールバックが実装されています）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになることがあります。ログの永続化が必要な環境では書き込み権限を確認してください。
- プロセス優先度設定（set_process_priority）はプラットフォーム依存で権限不足により失敗する場合があります（警告ログのみ）。

## よく使うコマンドまとめ（例）

- 仮想環境作成 & 有効化
  - python -m venv .venv
  - source .venv/bin/activate
- インストール
  - pip install duckdb psutil openai pyyaml
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定チェック
  - python -m kabusys.validate_config
- 監視開始
  - python -m kabusys.run_monitoring
- 実行エンジン開始
  - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

詳細は各モジュールの docstring（ソース内に豊富に記載）を参照してください。追加のドキュメントや例が必要であれば、どの機能について詳しく説明するか教えてください。