# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ + 起動スクリプト群）。

このリポジトリは主要な実行エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ／ファクター計算、ポートフォリオ構築、AI ニュース NLP などをモジュール化したコードベースです。各起動スクリプトはプロダクション運用を想定したログ・DB・プロセス管理・Kill Switch 機能を備えています。

主な目的
- 戦略に基づく銘柄選定・発注
- 実行状況 / システム状態の監視とアラート
- Paper Trading 用の切替と検証レポート
- DuckDB を使ったリサーチ・ファクター計算
- OpenAI を使ったニュースセンチメント評価（オプション）

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 設定 (.env) と環境変数
- 使い方（起動コマンド・ツール）
- ディレクトリ構成

---

プロジェクト概要
- 「KabuSys」は日本株用の自動売買・リサーチ基盤を意図したコード群です。
- 発注は kabuステーション API またはモック（paper_trading）で行える設計。
- 監視モジュールはシステム資源・データ鮮度・注文状態・リスク指標を継続チェックし、必要に応じて Kill Switch（停止フラグ）を書き込めます。
- DuckDB を分析用 DB に用い、prices_daily / raw_financials / raw_news 等のテーブルを参照してファクターやレポートを生成します。
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP / マクロセンチメントで市場レジーム判定・ニューススコアリングを行う機能を提供します（APIキー必要）。

---

機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（本番／ペーパートレード切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動
- 設定管理
  - config.py: 環境変数 / .env 自動読込 / Settings クラス
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env / config/*.yaml 等の事前検証 CLI
- 監視
  - monitoring_db.py: SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py: 各種監視ロジックと集約
  - kill_switch.py: データディレクトリの kill.flag 書き込みロジック
- 実行（Execution）
  - execution/*: ブローカーファクトリ、ExecutionEngine、OrderManager、RiskManager、Reconciler 等（起動スクリプトから組み立て）
- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder: 候補選定・重み計算
  - portfolio.position_sizing: 株数決定・資金配分・丸め
  - portfolio.risk_adjustment: セクター上限・レジーム乗数
- リサーチ
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン計算、IC、統計サマリ
- AI
  - ai.news_nlp: raw_news を集約し OpenAI API で銘柄別センチメントを算出して ai_scores へ保存
  - ai.regime_detector: MA200 とマクロニュース（LLM）を合成して market_regime を判定
- ユーティリティ
  - utils.logging_setup: 統一ログ設定（stdout + 日次ローテーション）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率・成功率・レイテンシ等）

---

必要条件（推奨）
- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config で YAML 検証を行いたい場合）
- SQLite（標準ライブラリの sqlite3 を使用）
- ネットワークアクセス（kabu API / OpenAI を利用する場合）

※ 実際の requirements.txt はリポジトリに含めてください。ここではコードから依存が推測されるものを列挙しています。

---

セットアップ手順（開発・ローカル）
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロダクション向けに requirements.txt を用意している場合はそれを pip install -r でインストール）

4. 設定ファイル作成
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（./.env）

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳密に扱いたい場合: python -m kabusys.validate_config --strict

6. データディレクトリ（data/）とログディレクトリ（logs/）を作成（config で指定している場合はパスを合わせる）
   - デフォルトでは data/ に DB・フラグファイル、logs/ にログファイルが作られます。起動時に自動作成されることが多いですが、権限等に注意してください。

---

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 運用環境切替
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading 時は MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用 flag（デフォルト: data/kill.flag）
- ログ
  - LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/...)
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- AI
  - OPENAI_API_KEY — OpenAI API キー（ai.* 関数を使う場合）
- run_monitoring 用
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- その他
  - PAPER_FILL_MODE — paper_trading 時の成行挙動 ("instant"|"partial"|"never"|"reject")

.env の自動ロード
- 実行時、プロジェクトルート（.git または pyproject.toml がある場所）を探索して
  - .env を読み込み（未設定の OS 環境変数のみ設定）
  - .env.local があればそれで上書き（OS 環境変数は上書きしない）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用等）。

---

使い方（起動・コマンド）

起動スクリプト（モジュール実行）
- ExecutionEngine（本番 or paper_trading）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 実行中の停止: data/stop_requested.flag を作成すると実行ループは検出して終了します。
  - Execution 停止トリガ: data/kill.flag を監視している ExecutionEngine はフラグが立つと停止します（Kill Switch 機能）。

- Monitoring（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整（秒）。デフォルト 60 秒。
  - 監視は Settings の sqlite_path を使って永続化（monitoring DB を利用）。監視は本番 DB を直接参照します（KABUSYS_ENV に依存しない点に注意）。

ユーティリティ CLI
- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可能

プログラムからの利用（ライブラリ）
- ポートフォリオ関数:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- リサーチ関数（DuckDB 接続を渡して使用）:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- AI:
  - from kabusys.ai import score_news
  - OpenAI API キーは OPENAI_API_KEY または関数引数で渡す

ログ
- ログは stdout にも出力され、デフォルトで logs/<app_name>.log に日次ローテーションで保存されます（デフォルト 30 日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

停止制御（Kill Switch / Stop Flag）
- data/kill.flag — Kill Switch が書き込むファイル。存在すると ExecutionEngine に停止シグナルを送ります。
- data/stop_requested.flag — run_*.py のループ終了を指示するローカル停止フラグ（起動スクリプトが定期的にチェック）。

DB 初期化
- monitoring_db.init_monitoring_db により必要なテーブルは起動時に冪等的に作成されます（マイグレーションも一部対応）。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py (※実装がある場合)
    - alert_manager.py (※実装がある場合)
  - execution/
    - broker_factory.py
    - execution_engine.py
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                     — 実行時に生成されることが想定（DB・flag・pid）
  - logs/                     — ログ出力先（デフォルト）

（実際のファイル一覧はリポジトリの src/kabusys 配下を参照してください。上は主要モジュールの抜粋です。）

---

運用上の注意
- KABUSYS_ENV=live は本番運用を意味します。validate_config で警告を確認し、LINE 通知等の設定を必ず確認してください。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup も同旨の注意を出力します）。
- OpenAI API の呼び出しには料金とレイテンシが発生します。API キー管理とレート制限に注意してください。
- run_execution/run_monitoring はプロセス優先度を高に設定します（utils.process_priority）。実行環境の権限やポリシーに注意してください。
- データベースファイル（DuckDB / SQLite）は適切にバックアップしてください。特に paper_trading と 本番 DB は分離して運用してください。

---

貢献 / 変更履歴
- この README はコードベースの説明を目的とした概要です。詳細実装や追加の設定項目は各モジュールの docstring / ソースコードコメントを確認してください。
- バグ修正や機能追加は issue / PR を通じて行ってください。

---

ライセンス
- リポジトリに記載されたライセンスに従ってください（ここでは省略）。

以上。README の改善点や追加で欲しい節（例: example .env、docker-compose 構成、詳細な ExecutionEngine API ドキュメント等）があれば教えてください。