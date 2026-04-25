KabuSys — 日本株自動売買ライブラリ / 実行コンポーネント
=====================================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリと簡易実行・監視スクリプト群です。
主な目的は以下です。

- 自動発注エンジン（ExecutionEngine）と監視コンポーネント（Monitoring）を分離して運用可能
- DuckDB / SQLite を用いたデータ分析・ログ永続化
- ペーパートレード用の分離 DB（data/paper_trading.db）をサポート
- ニュース NLP（OpenAI）によるセンチメント集約、レジーム判定モジュール
- ポートフォリオ構築、ポジションサイジング、リスク制御の純関数群
- 開発時に便利な設定ウィザード / 設定検証 / 検証レポート生成ツール

主要な特徴
----------
- 環境変数 / .env による設定（Settings クラス）
- 開発・ペーパー・本番切替（KABUSYS_ENV = development|paper_trading|live）
- ペーパートレード時は Mock ブローカー + 専用 SQLite に記録して本番 DB と分離
- ロギング統一化（コンソール + 日次ローテーションファイル）
- 監視（System/Trade/Risk）と Kill Switch による安全停止
- OpenAI（gpt-4o-mini）を利用したニュースセンチメントおよびレジーム判定（オプション）
- DuckDB を用いた研究/ファクター計算モジュール

前提・依存関係
---------------
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai（OpenAI API を使う場合）
- 任意（YAML 検証に必要）
  - PyYAML

インストール例（仮）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate
- 必要パッケージインストール（例）
  - pip install duckdb psutil openai pyyaml

環境変数（主なもの）
--------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- データベース / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 SQLite、デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
- ログ
  - LOG_LEVEL (DEBUG/INFO/…、デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)
- ペーパートレード
  - PAPER_FILL_MODE (instant | partial | never | reject) — デフォルト: instant
- 監視ループ
  - MONITOR_POLL_INTERVAL (秒, デフォルト: 60)
- OpenAI
  - OPENAI_API_KEY

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo> && cd <repo>
2. 依存関係をインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は前述のパッケージを個別にインストール）
3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗とみなす: python -m kabusys.validate_config --strict
4. データディレクトリ（data/）やログディレクトリは自動作成されるが、必要に応じて権限を確認してください。

基本的な使い方
-------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作モードが paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動しません（停止フラグチェック）。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（秒、デフォルト 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（環境に依らず）

- 設定ウィザード（.env の対話式作成/更新）
  - python -m kabusys.config_setup

- 設定の事前検証
  - python -m kabusys.validate_config
  - --strict をつけると警告があると exit(1) になります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- OpenAI を使うモジュール（プログラム的に）
  - ニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を None にすると env の OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一されます。
- 出力:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30世代保持）
- LOG_DIR 環境変数でログディレクトリを変更可能

停止・Kill Switch
-----------------
- 実行エンジンの停止要求:
  - data/stop_requested.flag（run scripts が監視しているフラグ）や、monitoring による kill.flag があり得ます
- KillSwitch（監視コンポーネント）が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine が停止する仕組みです。
- 実行開始前に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動消去できます（本番では推奨されません）。

開発者向け（モジュール利用）
----------------------------
多くの処理は純粋関数 / 小さなクラスに分かれているため、Python から直接インポートして利用できます。例:

- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- 研究用ファクター計算（DuckDB 接続を渡す）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
- 研究機能（IC, forward returns）
  - from kabusys.research import calc_forward_returns, calc_ic, factor_summary

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py (バージョン etc.)
- config.py — 環境変数 / .env 自動ロードと Settings クラス
- config_setup.py — 対話式 .env ウィザード (CLI)
- validate_config.py — .env / config/*.yaml の検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV に依存）
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py — SQLite 永続化層（テーブル初期化 / CRUD 補助）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
- execution/  (ExecutionEngine 周りの実装)
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py, __init__.py
- research/
  - factor_research.py, feature_exploration.py, __init__.py
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）によるスコア付与
  - regime_detector.py — レジーム判定
- monitoring_db / data 出力先（実行時に data/ 以下を利用）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - __init__.py

運用上の注意
-------------
- 本番 (KABUSYS_ENV=live) では kill_flag / KILL_FLAG_CLEAR_ON_START の値に注意してください。KILL_FLAG_CLEAR_ON_START=1 は本番では危険です。
- OpenAI の利用には API キー（OPENAI_API_KEY）が必要です。利用時のコスト・レート制限に注意してください。
- run_monitoring は常に本番用の sqlite_path を参照します（設定がどの env でも同じ DB を参照する設計）。
- ペーパートレードは本番 DB と分離されます。KABUSYS_ENV=paper_trading の場合、専用 DB (PAPER_TRADING_SQLITE_PATH) を使います。

よくあるコマンドまとめ
---------------------
- .env を作る（対話式）:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス・貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

補足・参考
-----------
- .env.example（ルートにある場合）を参考に .env を作成してください。
- config/*.yaml（system_config.yaml 等）は validate_config.py でチェックしますが、PyYAML がない場合はパース検証をスキップします。
- DuckDB は分析用、SQLite は監視・トレードログ用に使い分けています。

以上。運用・導入で不明点があればプロジェクトの README やドキュメント（存在する場合）を参照してください。必要なら README の内容を実際の env 名や起動フラグに合わせてカスタマイズして提案します。