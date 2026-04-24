README
======

概要
----
KabuSys は日本株向けの自動売買・研究基盤ライブラリです。  
主な目的は以下です。

- 市場データからファクターや特徴量を計算してリサーチを行う（DuckDB ベース）
- ポートフォリオ構築・ポジションサイジングの純粋関数群を提供
- 実際の発注を行う ExecutionEngine（本番 / ペーパートレード切替対応）
- システム・注文・リスクの監視（監視プロセスと Kill Switch）
- ニュース NLP（OpenAI）を使ったセンチメント集約および市場レジーム判定
- ペーパートレード検証レポート生成ツール

主要機能
--------
- 環境設定ウィザード（.env 生成 / 更新）
- 設定検証 CLI（.env と config/*.yaml のチェック）
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替。paper は専用 DB に分離）
- Monitoring（System / Trade / Risk）ポーリングループ
- Kill Switch（監視条件により data/kill.flag を書き込み、Engine を停止）
- ポートフォリオ構築：候補選定・重み付け・リスク適用・ポジション算出
- 研究用ユーティリティ：ファクター計算、forward returns、IC 計算、統計サマリー
- ニュース NLP（OpenAI を利用）で銘柄別センチメントスコアを ai_scores に格納
- Paper Trading 用検証レポート生成

セットアップ手順
----------------
1. Python 環境準備（推奨: virtualenv / venv）
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合は少なくとも以下を入れてください:
     pip install duckdb psutil openai PyYAML
   - 実行環境に応じて他の依存モジュール（requests 等）が必要になる場合があります。

3. 環境変数設定 (.env)
   - 対話式ウィザードで .env を生成:
     python -m kabusys.config_setup
   - あるいは手動で .env を作成してください（.env.example を参照する想定）。
   - 自動読み込み:
     パッケージはプロジェクトルート（.git または pyproject.toml）を探索して .env を自動ロードします。
     自動ロードを無効化する場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（起動前確認）
   - 設定検証を実行して問題がないか確認します:
     python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ（初回）
   - デフォルト DB / ログ等は以下を使用します（必要に応じて .env で変更してください）。
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite: 監視ログ)
     - data/paper_trading.db (ペーパートレード用 SQLite)
     - logs/ (ログ出力ディレクトリ)
   - logging_setup はログディレクトリを自動作成しますが、権限等で失敗する可能性があります。

主な環境変数（抜粋）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

重要（デフォルト値あり）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（news/regime 機能で必要）
- PID_FILE_PATH — ExecutionEngine 用 pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1。デフォルト 0。不用意な自動クリアは本番で危険)

モニタリング固有:
- MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒。デフォルト: 60）

使い方（起動 / ツール）
-------------------
- 環境設定ウィザード（.env 作成）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - 本番/開発/ペーパーは KABUSYS_ENV で切り替え
  - 実行:
    python -m kabusys.run_execution
  - ペーパートレード時 (例):
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ※ paper_trading は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。

- Monitoring（監視プロセス）起動:
  python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒、デフォルト 60）。
  - 監視は常に本番 sqlite_path を参照します（環境に依らず）。

- 停止制御:
  - data/stop_requested.flag（停止リクエスト）を作成すると run_monitoring/run_execution が検知して終了します（パスは各スクリプト内で設定）。
  - Kill Switch が発動すると data/kill.flag に理由を書き込み、ExecutionEngine を停止させる仕組みがあります（Settings.kill_flag_path）。

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  環境変数 PAPER_TRADING_SQLITE_PATH を使うこともできます。

- プログラム的利用（ライブラリとして）:
  - ポートフォリオ機能:
      from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - 研究機能:
      from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - ニュース NLP:
      from kabusys.ai import score_news
      # OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数引数で渡す

ログ
---
- ログは stdout とファイル (logs/<app_name>.log) に出力されます。
- 日次ローテーション（30 日保持）されます。
- setup_logging(app_name=...) を各起動スクリプトが使用して統一的に設定します。

データベースとマイグレーション
----------------------------
- monitoring_db.init_monitoring_db(conn) が必要なテーブルを冪等的に作成します。起動時に呼び出されるので手動操作は不要です。
- 既存 DB に対する簡易マイグレーション（カラム追加等）も含まれています（例: trade_logs に latency_ms を追加）。

注意事項 / ベストプラクティス
-----------------------------
- 本番運用時は KABUSYS_ENV=live の設定内容を慎重に確認してください（LINE 通知等の設定）。
- .env は絶対にリポジトリにコミットしないでください（シークレット情報を含むため）。
- Kill Switch（KILL_FLAG）や PID ファイルの取り扱いには注意してください。KILL_FLAG_CLEAR_ON_START=1 は本番では推奨しません。
- OpenAI 利用機能は API キーと利用料が必要です。API 呼び出し失敗時はフェイルセーフ（スコア 0 など）で進む設計が多いですが、設定とコスト管理は各自で行ってください。
- 外部依存（kabuステーション 等）は環境に合わせてセットアップしてください（API パスワード / ベース URL 等）。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                -- 環境変数と Settings
- config_setup.py          -- .env 対話式ウィザード
- validate_config.py       -- 設定検証 CLI
- run_execution.py         -- ExecutionEngine 起動スクリプト
- run_monitoring.py        -- Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py  -- ペーパートレード検証レポート CLI
- ai/
  - news_nlp.py             -- ニュース NLP スコアリング
  - regime_detector.py      -- 市場レジーム判定
- monitoring/
  - monitoring_db.py        -- SQLite 永続層（監視ログ）
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py        -- (実装参照: 監視の各種ロジック)
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
- execution/
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
- data/
  - pipeline.py             -- prices 日次取得等（DuckDB 参照）
  - stats.py                -- zscore 正規化等（research から使用）
- utils/
  - logging_setup.py
  - process_priority.py
  - その他ユーティリティ

付録: よく使うコマンド例
-----------------------
- .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config

- 実行エンジン起動:
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution

- 監視起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- ライブラリ的にニューススコアを実行（例）:
  from kabusys.ai import score_news
  import duckdb, datetime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, datetime.date(2026, 4, 20), api_key="sk-...")

最終更新
--------
この README はコードベースの説明を要約したものです。詳細な挙動や追加オプションは各モジュールの docstring を参照してください。