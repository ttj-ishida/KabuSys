# KabuSys — README (日本語)

概要
----
KabuSys は日本株の自動売買／リサーチ基盤です。価格データ集計、ファクター計算、ポートフォリオ構築、注文実行、監視・アラート、Paper Trading の検証ツール、LLM を用いたニュースセンチメント／レジーム判定などのコンポーネントを含みます。モジュールは可能な限り副作用を避けた純粋関数群と、SQLite / DuckDB を使った永続化層で構成されています。

主な特徴
--------
- 環境切替（development / paper_trading / live）による挙動分離
- 実行エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）の独立稼働
- Paper Trading 用に本番 DB と分離された専用 SQLite（data/paper_trading.db）
- DuckDB を用いた分析用データストア（data/kabusys.duckdb）
- LLM（OpenAI）を使ったニュースセンチメント（news_nlp）／レジーム判定（regime_detector）
- 監視ログ永続化（SQLite）とリスク監視（ドローダウン、ポジション上限など）
- ペーパートレード検証レポート生成ツール
- .env ウィザードおよび起動前設定検証ツール

動作要件（推奨）
----------------
- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の検証を行う場合に推奨）
- （実行環境に応じて）kabuステーション API や J-Quants の認証情報

セットアップ手順
----------------
1. リポジトリをクローン／展開します（Project root を想定）。
2. 仮想環境を作成・有効化：
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール（requirements.txt がある場合はそれを使用）:
   - pip install duckdb psutil openai PyYAML
   - または: pip install -r requirements.txt
4. 初期設定:
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成（例は次節参照）。
5. 設定検証（任意）:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

環境変数（.env の例）
---------------------
config_setup により生成される .env の主要項目（デフォルト値の例を含む）:
- KABUSYS_ENV=development  # development | paper_trading | live
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

注意:
- 環境変数は OS 環境変数 > .env.local > .env の優先順位でロードされます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- Paper Trading（KABUSYS_ENV=paper_trading）の場合、発注はモック実装を用い、data/paper_trading.db に記録され本番 DB と分離されます。

主要ファイルと実行方法
--------------------
- 起動スクリプト
  - 監視ループ（Monitoring）
    - python -m kabusys.run_monitoring
    - ポーリング間隔: 環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    - 監視は常に本番用 sqlite_path（SQLITE_PATH）を使用します（環境に依存せず本番 DB を書き換える設計のため注意）。
    - 停止はプロジェクトルート/data/stop_requested.flag の存在で検知します。
  - 実行エンジン（Execution）
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録します。
    - 停止フラグ: project_root/data/stop_requested.flag を検知すると終了します。
    - 実行中の PID は data/execution.pid に書き込まれます（デフォルト）。
- 設定ツール
  - python -m kabusys.config_setup  # 対話式 .env ウィザード
  - python -m kabusys.validate_config [--strict]  # 起動前の設定検証
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- ライブラリ API（プログラムから利用）
  - kabusys.portfolio.*（候補選定、重み付け、個別サイズ計算）
  - kabusys.research.*（ファクター計算、IC 等）
  - kabusys.ai.score_news（ニュースセンチメントのスコアリング）
  - kabusys.ai.regime_detector.score_regime（市場レジーム判定）
  - kabusys.monitoring.MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor 等

ログ・データ・フラグ
--------------------
- ログ:
  - デフォルトでは logs/<app_name>.log に日次ローテーションで保存（30日保持）
  - コンソール出力は stdout
  - ログレベルは LOG_LEVEL 環境変数で制御（例: INFO, DEBUG）
- データ:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite (監視用): data/monitoring.db（Settings.sqlite_path）
  - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- 停止 / キルフラグ:
  - stop_requested.flag: run_monitoring / run_execution が監視している「停止要求」用ファイル（存在でループを抜ける）
    - パス: プロジェクトルート/data/stop_requested.flag
  - kill.flag: Kill Switch により作成され、ExecutionEngine 停止を通知するために使用（パスは Settings.kill_flag_path、デフォルト data/kill.flag）
  - PID ファイル: data/execution.pid（ExecutionEngine が PID を書込む）

監視・リスク機構の概要
---------------------
- SystemMonitor: CPU/メモリ/ディスク/プロセス存在の監視、データ鮮度チェック（prices_daily の最終日付）
- TradeMonitor: trade_logs を基に滞留注文や約定異常を検出（実装ファイル参照）
- RiskMonitor: ダッシュボード（dashboard テーブル）からドローダウン計算、ポジション数監視、必要時に risk_logs に永続化
- KillSwitch: RiskMonitor 等の結果に応じて kill.flag を作成（重篤な条件時に ExecutionEngine 停止を誘発）
- MonitoringEngine: 上記モジュールを束ねて定期的にチェックし、必要に応じてアラート通知（AlertManager）や Kill Switch 評価を行う

よく使うコマンド例
-----------------
- .env を生成:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
- 監視をデーモン的に起動（開発用）:
  - python -m kabusys.run_monitoring
- 実行エンジン起動（本番/ペーパー切替は KABUSYS_ENV に依存）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ディレクトリ構成（抜粋）
----------------------
プロジェクトの主要ファイル・ディレクトリ（src/kabusys 以下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          # 対話式 .env ウィザード
  - validate_config.py       # 起動前設定検証 CLI
  - run_monitoring.py        # Monitoring ポーリングループ起動スクリプト
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       # ログ初期化ユーティリティ
    - process_priority.py    # プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py      # SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

開発上の注意
-----------
- 本プロジェクトではデフォルトで本番用の sqlite_path（monitoring.db）を監視側が使用するため、環境切替や DB パスの設定には注意してください。Paper Trading は専用の PAPER_TRADING_SQLITE_PATH を使うようにしています。
- OpenAI 関連機能を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライやフェイルセーフ（失敗時は 0 相当のフォールバック）を備えていますが、レート制限やコストに注意してください。
- .env は機密情報を含むため、絶対にリポジトリにコミットしないでください。
- logs ディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソールのみになります（警告が出力されます）。

サポート／拡張ポイント
---------------------
- BrokerClient の実装差替えにより任意の証券 API に対応可能（broker_factory で抽象化）
- ポートフォリオ構築ロジック（weights, allocation_method）や lot_size の銘柄別対応は拡張余地あり
- DuckDB スキーマ（prices_daily / raw_financials / raw_news 等）に合わせてリサーチ機能を拡張可能

ライセンスや連絡先
------------------
（ここにプロジェクトのライセンス・メンテナ連絡先等を追記してください）

以上。必要であれば README にサンプル .env やコマンドのより詳しい使い方、CI 設定、デプロイ手順などを追記します。どの情報を優先して加えるか教えてください。