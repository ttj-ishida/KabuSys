KabuSys
=======
日本株向けの自動売買 / 研究フレームワーク（軽量なプロダクション寄り設計）。  
このリポジトリはトレード実行エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント）連携などを含むモジュール群で構成されています。

概要
----
KabuSys は以下の目的を持ったモジュール群を提供します。
- 自動売買実行（ExecutionEngine） — 本番 / ペーパートレード対応
- 監視（Monitoring） — システム稼働・注文状況・リスク監視と Kill Switch
- ポートフォリオ構築（portfolio） — 候補選定・重み計算・ポジションサイズ計算
- リサーチ（research） — ファクター計算・特徴量探索
- AI（ai） — ニュースの自然言語処理によるセンチメント評価、レジーム判定
- ユーティリティ（utils） — ロギング、プロセス優先度設定等
- ツール（tools） — ペーパートレード検証レポート等

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に隔離して記録
- 監視ループ（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、Kill Switchやアラートを出す
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 環境設定ウィザード（config_setup.py）
  - .env の対話的作成・更新を支援
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の妥当性チェック（--strict で警告も失敗扱い）
- ポートフォリオ構築（select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes）
- 研究用ファクター計算（momentum / volatility / value 等）
- ニュース NLP（ai.news_nlp.score_news）とレジーム判定（ai.regime_detector.score_regime）
- ペーパートレード検証レポート生成（tools/paper_verification_report.py）

前提条件・依存関係
------------------
- Python 3.10+
- 主な依存（プロジェクトに requirements.txt があればそちらを使用してください）:
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
  - PyYAML（config 検証で YAML 検査を行う場合に必要）
- SQLite / DuckDB を使用（ファイルベースの DB）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - あるいはプロジェクトの requirements.txt があればそれを利用: pip install -r requirements.txt

4. .env を準備
   - 対話式ウィザード: python -m kabusys.config_setup
   - または .env を手動作成（.env.example を参照）
   - 自動ロード: kabusys.config はプロジェクトルートの .env を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

5. データディレクトリとログディレクトリの作成（必要に応じて）
   - mkdir -p data logs

主な環境変数（代表例）
---------------------
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の約定モード: instant|partial|never|reject（デフォルト instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒。run_monitoring.py で使用）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — プロセス管理 / Kill Switch

起動方法（CLI）
---------------
- 環境ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / ペーパー共通エントリ）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を設定可能（デフォルト 60 秒）

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH を使うことも可能）

プログラムからの利用例（簡易）
----------------------------
- DuckDB 接続を作成して研究関数を呼ぶ例:
  - import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from kabusys.research import calc_momentum
    records = calc_momentum(conn, target_date=date(2026,4,1))

- AI ニューススコアリング（OpenAI API キーが必要）:
  - from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

安全上の注意
-------------
- KABUSYS_ENV=live の場合は実際に発注が行われます。設定（APIキー・資金・リスクパラメータ等）を十分に確認してください。
- Kill Switch 機構があり、リスク閾値を超えると data/kill.flag が書き込まれて ExecutionEngine に停止シグナルを送ります。
- .env は絶対にソース管理にコミットしないでください。

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging により統一的に設定されます。
- デフォルトのログディレクトリ: logs/
- 各アプリケーション（execution, monitoring 等）は logs/<app_name>.log に日次ローテーションで出力します。

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み・Settings
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

modules/
- execution/               — 実行エンジン関連（broker_factory, execution_engine, order_manager, ...）
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
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

（上記は src/kabusys 配下の概略。実際のファイルはリポジトリ内を参照してください）

開発・拡張のヒント
------------------
- .env の自動ロード: config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を読み込みます。テスト中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- DuckDB は分析・リサーチ用途、SQLite は監視や注文ログの軽量永続化に使われます（設計で役割を分離）。
- AI 呼び出しは OpenAI の SDK を利用しています。API レート制限や 5xx に対してリトライ戦略が実装されていますが、運用環境ではキー管理とコスト管理に注意してください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報や貢献ルールがある場合はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

お問い合わせ
------------
- 実装詳細や運用設定については該当モジュール（execution/, monitoring/, ai/）のドキュメントやソースの docstring を参照してください。README にない詳細な使い方はソース内コメントが有益です。

以上。必要であれば README にサンプル .env.example のテンプレートや、各 CLI の具体的な出力例・トラブルシュート項目を追記できます。どの情報を追加しますか？