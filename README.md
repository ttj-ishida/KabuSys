KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための Python コードベースです。  
主要な機能群は次の通りです:

- 発注エンジン（ExecutionEngine）起動スクリプトと実行管理
- 監視モジュール（System/Trade/Risk）による稼働監視と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI（OpenAI）を使ったニュースセンチメント評価と市場レジーム判定
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザードと設定検証 CLI

主要な設計方針:
- 実運用（live）とペーパートレード（paper_trading）を明確に分離
- DuckDB / SQLite による分析・監視データ保存
- OpenAI や外部 API 呼び出しは明示的にキーを必要とし、失敗時はフェイルセーフ
- スクリプトは CLI モジュールとして直接起動可能（python -m kabusys.xxx）

機能一覧
--------
- 環境管理
  - .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - 自動 .env 読み込み（プロジェクトルート検出）
- 実行 / 監視
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV により paper_trading モード切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - kill.flag / stop_requested.flag によるプロセス制御
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）でコンソール & 日次ローテートファイル出力
  - process_priority 設定ユーティリティ（高優先度でプロセス起動）
- 監視（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB: SQLite に対する永続化 API（system_status / trade_logs / positions / risk_logs / dashboard）
  - KillSwitch: ドローダウンやポジション上限で停止フラグを作成
- ポートフォリオ（portfolio）
  - 候補選定 (select_candidates)
  - 重み計算 (calc_equal_weights, calc_score_weights)
  - セクター制限 (apply_sector_cap) / レジーム乗数 (calc_regime_multiplier)
  - ポジションサイズ決定 (calc_position_sizes)
- リサーチ（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算, IC（Information Coefficient）, 統計サマリ
  - DuckDB を用いた高速集計
- AI（ai）
  - news_nlp.score_news: OpenAI を用いてニュースを銘柄ごとにスコアリングし ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースで市場レジーム判定（market_regime テーブルへ書込）
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------

前提
- Python 3.9+（pyproject.toml に合わせてください）
- 推奨: 仮想環境（venv, pipenv, poetry 等）

1. リポジトリをチェックアウト / コピー
   - プロジェクトルート配下に src/ と data/, config/ 等が配置されます

2. 仮想環境作成・依存インストール
   - 例（pip）:
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
   - 必要な主な依存（参考）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で optional）
     - など（実際の requirements.txt を参照）

3. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 生成された .env は絶対に Git にコミットしないでください。
   - 自動ロードを無効化する場合（テスト用）:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証
   - .env と config/*.yaml の整合性チェック:
     python -m kabusys.validate_config
   - 警告を厳密に FAIL と扱う場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ（data/）作成
   - デフォルトの SQLite/DuckDB ファイルは data/ に作られます。事前に mkdir -p data logs を推奨。

環境変数（主要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant|partial|never|reject。ペーパートレードの約定モード）
- LOG_DIR / LOG_LEVEL
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数、デフォルト 60）

使い方（代表例）
-----------------

起動スクリプト
- 監視ループ起動（SystemMonitor をポーリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは data/paper_trading.db に記録され本番 DB と分離
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 実行中に stop flag を作成するとエンジンに停止を要求します
  - PID ファイル: data/execution.pid が利用されます（Settings.pid_file_path で変更可）

ツール
- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db /path/to/paper_trading.db

AI 機能をプログラムから呼び出す例
- ニューススコア（DuckDB 接続と target_date を渡す）
  from kabusys.ai.news_nlp import score_news
  import duckdb, datetime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, datetime.date(2026, 4, 20), api_key="sk-...")

- レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, datetime.date(2026, 4, 20), api_key="sk-...")

リサーチ関数の使用例
- ファクター計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  rows = calc_momentum(conn, target_date)

ログ
- ログ出力は kabusys.utils.logging_setup.setup_logging を通して統一
- デフォルト: stdout + logs/<app_name>.log（日次ローテート、30日保持）
- LOG_DIR, LOG_LEVEL で設定変更可

停止・Kill Switch
- 実行停止（外部から）:
  - run scripts は data/stop_requested.flag の存在を監視し、検出時に安全停止する
- KillSwitch（自動停止）:
  - RiskMonitor 等の結果により data/kill.flag を書き込み、ExecutionEngine に停止を促す
  - KillSwitch.clear() で削除可能（Settings.kill_flag_clear_on_start = 1 の場合は起動時に自動クリアされるが、本番では 0 推奨）

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                 # 環境変数 / 設定読み込みロジック
    config_setup.py           # .env 対話式ウィザード
    validate_config.py        # 設定検証 CLI
    run_execution.py          # ExecutionEngine 起動スクリプト
    run_monitoring.py         # SystemMonitor 起動スクリプト
    tools/
      paper_verification_report.py
    utils/
      logging_setup.py
      process_priority.py
    monitoring/
      monitoring_db.py
      monitoring_engine.py
      system_monitor.py
      risk_monitor.py
      trade_monitor.py         # （トレード監視ロジック）
      kill_switch.py
      alert_manager.py         # （アラート送信ロジック）
    execution/                 # 発注関連（Engine, Broker, OrderManager 等）
      execution_engine.py
      broker_factory.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py
      regime_detector.py
    data/                      # （データ格納ファイル: data/*.db 等）
    config/                    # YAML 設定テンプレート等

注意点・運用メモ
----------------
- run_monitoring は monitoring 用の SQLite（Settings.sqlite_path）を環境にかかわらず使用します（監視データは本番 DB に依存）。
- run_execution は KABUSYS_ENV により paper_trading 用 DB を使用する（完全分離）。
- OpenAI 呼び出しは API エラー時にリトライやフォールバックが仕組まれているが、APIキーは必須。課金・レートに注意。
- .env ファイルは Secrets を含むため絶対にリポジトリにコミットしないでください。
- psutil 周りは OS 権限（nice / affinity）が必要な場合があり、権限不足では警告のみ出て処理は継続します。
- DuckDB/SQLite のパスやログディレクトリは .env で調整してください。logs ディレクトリの権限に注意。

ライセンス / バージョン
-----------------------
- パッケージバージョン:
  kabusys.__version__ = "0.1.0"
- ライセンス情報が別途ある場合はプロジェクトルートの LICENSE 等を参照してください。

サポート・開発
---------------
バグ修正・拡張・追加機能は README を更新の上、該当モジュールにユニットテストを追加してください。  
特にトレード周り・リスク管理・Kill Switch は慎重なレビューとステージングでの検証を推奨します。

以上。必要であれば、README に含めるコマンドの具体的な例や .env の雛形（安全にマスクしたもの）を追加で作成します。