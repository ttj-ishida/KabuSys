KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買フレームワーク「KabuSys」の一部実装です。
監視（Monitoring）、実行（Execution）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのコンポーネントを備え、ローカル実行およびペーパートレード/本番運用を想定した設計になっています。

主な特徴
--------
- 実行エンジン（ExecutionEngine）と独立した監視サブシステム（Monitoring）
- ペーパートレード用に本番 DB と分離された専用 SQLite（data/paper_trading.db）対応
- News NLP / Regime Detector による LLM を用いたセンチメント評価（OpenAI）
- DuckDB を利用したリサーチ／ファクター計算モジュール（prices_daily / raw_financials 参照）
- リスク制御モジュール（ドローダウン監視・ポジション上限監視）と Kill Switch（flag ファイルで Execution を停止）
- ロギングの統一設定（コンソール + 日次ローテーションファイル）
- 各種ユーティリティ（プロセス優先度設定 / 環境変数ウィザード / 設定検証 / 検証レポート）

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを収集
- 環境設定・検証
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の整合性チェック CLI
- 監視
  - monitoring/:
    - SystemMonitor: CPU/メモリ/ディスク・プロセス稼働・データ鮮度を監視
    - TradeMonitor: 発注・約定ログの検査（滞留注文・価格異常など）
    - RiskMonitor: ドローダウン / ポジション上限検知、dashboard 更新、risk_logs 登録
    - KillSwitch: 条件により data/kill.flag を作成して Execution を停止
    - MonitoringDB: SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - MonitoringEngine: 上記を束ねるポーリングエンジン
- ポートフォリオ構築
  - portfolio/:
    - 銘柄選定、等比/スコア加重の重み計算、セクターキャップ、レジーム乗数、ポジションサイズ算出（lot 単位丸め、aggregate cap）
- リサーチ
  - research/:
    - ファクター計算（momentum, volatility, value）
    - 将来リターン、IC（スピアマン）計算、統計サマリー
- AI
  - ai/news_nlp.py: raw_news を集約して OpenAI へバッチ送信し ai_scores テーブルへ書込
  - ai/regime_detector.py: ETF（1321）MA200 とマクロニュースの LLM 評価を組合せて market_regime を算出
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB の検証レポート生成（稼働率、成功率、レイテンシ等）

セットアップ手順
----------------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（例: requirements.txt がある場合はそれを使用）。
   - 必要な主要パッケージ（抜粋）:
     - duckdb
     - psutil
     - openai
     - （開発時）PyYAML（config の検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabuAPI パスワード等の必須値を入力します。
   - 生成後、設定検証:
     - python -m kabusys.validate_config
     - 必須項目が不足しているとエラーになります。--strict を付けると警告も失敗扱いになります。

4. 必要なディレクトリを作成します（通常はスクリプトで自動生成されますが、手動で用意する場合）。
   - data/ (SQLite や PID / flag を置く)
   - logs/ (ログファイル保存)

環境変数（主要）
----------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用/挙動制御
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（ai モジュール利用時）
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視用 monitoring DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading DB（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
  - LOG_LEVEL, LOG_DIR
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト "0"）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。1 未満や不正値はデフォルトにフォールバック。

使い方（実行例）
----------------
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 備考:
    - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能。
    - run_monitoring はモニタリング用 DB（Settings.sqlite_path）を環境にかかわらず使用します（監視は本番 DB の状態を監視するため想定）。
    - 停止: プロセスに KeyboardInterrupt を送るか、プロジェクトルート/data/stop_requested.flag を作成すると安全に終了します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と完全分離）。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
    - 実行中に停止させるにはプロジェクトルート/data/stop_requested.flag を作成するか、kill.flag を用いて外部から停止シグナルを与えます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラムからの利用例）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)  # api_key 省略時は環境変数 OPENAI_API_KEY を参照

停止 / Kill Switch
------------------
- KillSwitch（kabusys.monitoring.kill_switch）は条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine はこの flag を検出して安全停止を行います。
- 手動で ExecutionEngine を停止したい場合:
  - プロジェクトルート/data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアしますが、本番では 0 を推奨します。

ディレクトリ構成（主要）
----------------------
（src 以下をパッケージ化している想定。ここでは主要ファイルを抜粋して示します）

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数 / Settings クラス、自動 .env ロード
    - config_setup.py            # .env 対話ウィザード
    - validate_config.py         # 設定検証 CLI
    - run_execution.py           # ExecutionEngine 起動スクリプト
    - run_monitoring.py          # SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
    - execution/                  # ExecutionEngine 関連（broker, order_manager 等）
      - execution_engine.py
      - broker_factory.py
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
    - data/                       # 実行時に使用するファイル（SQLite / PID / flags 等）
    - logs/                       # ログ出力先（設定により変更可能）

注意点 / 運用上のヒント
-----------------------
- run_monitoring は監視 DB（SQLITE_PATH）を本番 DB として扱うため、監視専用 DB を別に用意したい場合は sqlite のパスを適切に設定してください。ただし既存の実装では monitoring は本番 sqlite_path を使用する設計です（run_execution は環境に応じて paper_trading_db を使用）。
- OpenAI 関連機能を利用する場合は OPENAI_API_KEY を必ず設定してください。API 呼び出しは失敗時にフェイルセーフ（スコア 0 にフォールバック、またはそのチャンクをスキップ）する実装がありますが、運用では安定したキー管理が必要です。
- ログは logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- config/*.yaml（system_config.yaml など）は config_setup/生成スクリプトで作成する想定です。PyYAML がない場合、validate_config は YAML 検証をスキップします。

貢献 / テスト
--------------
- ユニットテストを追加して各純粋関数（portfolio/*.py、research/*.py、monitoring/*.py の一部）を検証できます。AI / DB 依存の部分はモックで代替してください（例: OpenAI クライアントや DuckDB/SQLite 接続の差し替え）。
- 設定検証（validate_config）や .env ウィザード（config_setup）は CLI で容易に試せます。

ライセンス・その他
------------------
- この README ではコード全体の解説を主目的としています。ライセンス情報や詳細なアーキテクチャ設計文書（PortfolioConstruction.md, StrategyModel.md 等）が別途あれば併せて参照してください。

以上。必要であれば README にサンプル .env のテンプレートやより詳しい起動フロー図、各モジュールの公開 API の一覧（関数/クラスと引数）を追加します。どの情報を優先して追加しますか？