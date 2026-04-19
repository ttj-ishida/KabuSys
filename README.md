KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python 製のパッケージです。本リポジトリには以下の主要機能を持つコンポーネントが含まれます。

- ExecutionEngine（発注エンジン）: 本番 / ペーパートレードを切替可能な発注フロー
- Monitoring（監視）: システム稼働状況・注文状態・リスク監視と Kill Switch
- Research / Portfolio: ファクター計算、特徴量解析、ポートフォリオ構築・ポジションサイジング
- AI 支援: ニュースの NLP スコアリング、レジーム判定（OpenAI 経由）
- ユーティリティ: 設定ウィザード、設定検証、検証レポート生成など

バージョン: 0.1.0（src/kabusys/__init__.py）

主な機能一覧
--------------
- 環境設定の自動読み込み（.env / .env.local）、Settings 抽象化
- 実行スクリプト:
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading で MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 監視:
  - system_monitor: CPU/メモリ/ディスク、プロセス死活、データ鮮度確認
  - trade_monitor: 注文の滞留／約定異常検出（実装参照）
  - risk_monitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - kill_switch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - monitoring_db: SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- 研究・ファクター:
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - research.feature_exploration: 将来リターン計算、IC 計算、統計サマリ
- ポートフォリオ構築:
  - portfolio.portfolio_builder / position_sizing / risk_adjustment: 候補選定、重み計算、株数算出、セクター制限、レジーム乗数
- AI:
  - ai.news_nlp: OpenAI を使ったニュースセンチメント評価と ai_scores 書き込み
  - ai.regime_detector: MA200 とマクロセンチメントの合成による市場レジーム判定
- ツール:
  - tools.paper_verification_report: ペーパートレード DB から検証レポート生成
- CLI:
  - config_setup.py: .env 対話ウィザード（初期作成/更新）
  - validate_config.py: .env / config/*.yaml の設定検証

前提・依存パッケージ
-------------------
最低限必要な環境（例）:
- Python 3.10+
- SQLite（標準ライブラリ）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml をパースして検証したい場合）

インストール例（仮）:
- 仮想環境作成
  python -m venv .venv
  source .venv/bin/activate
- 必要パッケージ（例）
  pip install duckdb psutil openai PyYAML

注: requirements.txt は本例に含まれていません。実運用では lock ファイルや requirements.txt を準備してください。

セットアップ手順
----------------
1. リポジトリをチェックアウト
2. 仮想環境を作成して依存ライブラリをインストール（上記参照）
3. .env を作成
   - 自動読み込み: src/kabusys/config.py はプロジェクトルート（.git または pyproject.toml）を検出すると .env/.env.local を自動で読み込みします。
   - 自動ロードを無効化する場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
4. 設定ウィザード（対話式）を使う:
   python -m kabusys.config_setup
   → 生成された .env を確認・保存してください
5. 設定検証:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります
6. data ディレクトリ等（データ・ログ格納先）が自動作成されますが、必要に応じて事前に作成してください（logs, data）

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先（デフォルト logs）
- OPENAI_API_KEY: OpenAI を使用する機能で必要
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、run_monitoring で使用。デフォルト 60）

サンプル .env（抜粋）
--------------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

使い方
------
起動・停止
- ExecutionEngine（発注エンジン）起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用しデータは PAPER_TRADING_SQLITE_PATH に書き込まれます（本番 DB と分離されます）。
  - 起動時に data/execution.pid を使用／作成します。停止は外部からフラグファイルを書き込むかプロセスを終了します。

- Monitoring（監視）起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
  - run_monitoring が見る停止フラグ: data/stop_requested.flag が存在するとループを終了します。

- Kill Switch（ExecutionEngine 停止）:
  - monitoring 側で条件に合致すると data/kill.flag が書き込まれ ExecutionEngine に停止シグナルを送ります。
  - KillSwitch.clear() により flag を削除できます（起動時に KILL_FLAG_CLEAR_ON_START=1 で自動クリアが可能ですが本番では推奨されません）。

管理・検証
- 設定ウィザード:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config [--strict]
- ペーパートレード検証レポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB ファイルを指定可能

AI 機能
- ai.news_nlp.score_news や ai.regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。API 呼び出しはリトライ/バックオフを備え、失敗時は安全側にフォールバックします（例: macro_sentiment=0.0）。

ログ
- すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を使って統一的にログを出力します。
- デフォルトで stdout と 日次ローテーションログ（logs/<app_name>.log）に出力します。

停止方法（安全停止フロー）
- 実験中:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring の外部ループが検知して終了します（run_execution は実行スレッドに対して engine.stop() を呼び出します）。
- 緊急停止（Kill Switch）:
  - monitoring が危険事象を検出すると data/kill.flag を書き込みます。ExecutionEngine は起動時に kill.flag をチェックし動作を制御します。

ディレクトリ構成（主要ファイル）
--------------------------------
以下はコードベースの主要モジュール（src/kabusys）を抜粋した構成例です。

- src/kabusys/
  - __init__.py (バージョン定義)
  - config.py (環境変数 / Settings 管理、自動 .env 読み込み)
  - config_setup.py (対話的 .env ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - __init__.py
    - paper_verification_report.py (ペーパートレード検証レポート)
  - utils/
    - __init__.py
    - logging_setup.py (ログ設定)
    - process_priority.py (プロセス優先度 / CPU affinity 設定)
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/          (発注エンジン周りの実装群: broker_factory, execution_engine, order_manager, ...)
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/ (実行時に使用する data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など)
  - logs/ (ログ出力先)

補足 / 注意点
-------------
- .env は絶対にレポジトリにコミットしないこと（config_setup.py のヘッダにも同様の注意が記載されています）。
- monitoring の DB 初期化（init_monitoring_db）は冪等であり、既存 DB に対してスキーママイグレーション（カラム追加）処理を含みます。
- データ鮮度・レジーム判定・AI 呼び出しはルックアヘッドバイアスを避ける設計（target_date 未満のみ参照する等）になっています。
- process_priority.set_process_priority はプラットフォームに合わせて Windows / POSIX に対応しますが、権限不足で失敗する場合は警告ログを出して継続します。

貢献・開発
----------
- テスト: 各モジュールは純粋関数的実装（副作用を限定）を心がけているためユニットテストが書きやすい設計です（DuckDB/SQLite コネクションを注入してテストできます）。
- ドキュメント: StrategyModel.md / PortfolioConstruction.md 等の設計ドキュメントに準拠した実装を含みます。追加の設計文書を README にリンクすることを推奨します。

ライセンス
---------
（ここにプロジェクトのライセンスを明記してください）

---

以上が本コードベースの概要・セットアップ・使い方のまとめです。追加で README に含めたいコマンド例や各コンポーネントの詳細（API 仕様、設定項目の完全一覧、実行例のスクリーンショット等）があれば指示ください。