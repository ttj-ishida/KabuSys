KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤の軽量実装です。  
主な目的は以下:

- 日次のファクター計算・ポートフォリオ構築（research, portfolio）
- 発注・執行・リスク管理（execution）
- ランタイム監視・アラート・Kill Switch（monitoring）
- Paper Trading 検証ツール・レポート（tools）
- ニュースの NLP によるスコアリングや市場レジーム判定（ai）

このリポジトリは純粋関数／DB 隔離の原則に沿って設計されており、本番 DB とペーパー取引 DB を分離できます。

主な機能
--------
- 実行モジュール
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用いて data/paper_trading.db に記録（本番 DB と分離）。
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔を変更可）。

- 設定・検証
  - config_setup.py: .env を対話的に作成・更新するウィザード。
  - validate_config.py: .env や config/*.yaml の簡易検証 CLI（--strict オプションあり）。

- モニタリング
  - system_monitor / trade_monitor / risk_monitor を束ねた MonitoringEngine。
  - KillSwitch によるフラグファイル（data/kill.flag）でのエンジン停止シグナル生成。
  - SQLite に監視ログを永続化する monitoring_db。

- ポートフォリオ構築（純粋関数）
  - 銘柄選定、重み計算（等金額・スコア）、ポジションサイズ計算、セクターキャップ、レジーム乗数適用。

- リサーチ
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）。
  - 将来リターン計算、IC（Information Coefficient）などの統計ユーティリティ。

- AI 関連
  - news_nlp: OpenAI を用いたニュースのセンチメントスコア付与（ai_scores テーブルへ書込）。
  - regime_detector: ETF の MA とマクロニュースを合成して市場レジーム判定（market_regime テーブルへ書込）。

- ツール
  - paper_verification_report.py: Paper Trading DB（data/paper_trading.db）から稼働率・注文成功率・レイテンシ等を集計し検証レポートを出力。

セットアップ手順
----------------
前提
- Python 3.10 以上（型注釈や新しい集合型表記を想定）
- 必要パッケージ（最小例）:
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - （オプション）PyYAML（validate_config で config/*.yaml をパースする場合）

例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML

環境変数 (.env)
- .env をプロジェクトルートに置くことで自動読み込みされます（既存 OS 環境変数を上書きしない）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要なキー（.env.example を参考に作成してください）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可; デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB; デフォルト: data/paper_trading.db)
  - KABUSYS_ENV (development | paper_trading | live) — 実行モード
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - OPENAI_API_KEY (AI 機能利用時に必要)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート通知に利用する場合)
  - KILL_FLAG_CLEAR_ON_START (0/1; 本番では 0 推奨)

.env を対話的に作る:
  python -m kabusys.config_setup

設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

DB 初期化
- 実行スクリプト起動時に必要なテーブルは自動で作成されます。monitoring 用 SQLite は init_monitoring_db() により冪等に初期化されます。

使い方
------
起動スクリプト（モジュール実行）
- ExecutionEngine を起動（production/paper_trading は KABUSYS_ENV に依存）:
  python -m kabusys.run_execution

  動作概要:
  - プロセス優先度を "high" に設定（set_process_priority）
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に書き込み
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
  - 実行中に stop flag を検知すると安全に停止

- Monitoring を起動:
  python -m kabusys.run_monitoring

  オプション（環境変数）:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。不正値はデフォルトにフォールバック。
  動作概要:
  - SystemMonitor.check_once() を poll interval 毎に呼び出す
  - ループ中に data/stop_requested.flag が存在する場合は終了
  - 監視は常に本番 sqlite_path を使用（環境にかかわらず）

停止 / Kill
- 実行中のループを外部から停止する方法:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のポーリングループが検出して終了します（手動で作成或いは管理スクリプトから）。
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動時のクリア動作や起動中の検出ロジックを持ちます）。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアしますが、本番では危険なので 0 を推奨。

Paper Trading 検証レポート
- data/paper_trading.db を指定して検証レポートを出力:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI 機能
- news_nlp / regime_detector は OpenAI API を使用します。環境変数 OPENAI_API_KEY を設定してください。
- API 呼び出しはレート制限や transient エラーに対してバックオフ付きでリトライします。失敗時はフェイルセーフとしてイグノア／デフォルト値にフォールバックします。

ログ
- ログは kabusys.utils.logging_setup.setup_logging を通じて統一的に出力されます:
  - コンソール（stdout）
  - ローテート付きファイル: logs/<app_name>.log（デフォルト）
- ログディレクトリは環境変数 LOG_DIR またはデフォルト logs/。作成できない場合はファイル出力をスキップしてコンソールのみ出力します。

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- DUCKDB_PATH: DuckDB ファイルパス（分析用）
- SQLITE_PATH: 監視 DB（monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB
- OPENAI_API_KEY: OpenAI 呼び出し用
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の MockBrokerClient の約定モード（instant|partial|never|reject）

ディレクトリ構成
----------------
（主要なファイル/モジュールのみ抜粋）

- src/kabusys/
  - __init__.py (パッケージ定義)
  - __version__ = "0.1.0"

  - run_execution.py
  - run_monitoring.py

  - config.py
    - Settings クラス: 環境変数のラッパー・自動 .env ロード
  - config_setup.py
    - .env を対話的に作成するウィザード
  - validate_config.py
    - 起動前の設定チェック CLI

  - utils/
    - logging_setup.py: 共通ログ設定
    - process_priority.py: プロセス優先度 / CPU affinity 設定

  - monitoring/
    - monitoring_db.py: SQLite テーブル作成・CRUD ユーティリティ（MonitoringDB）
    - system_monitor.py: CPU/メモリ/Disk/データ鮮度/プロセス監視
    - trade_monitor.py: （注文ログ監視: 滞留注文・価格異常など）※実装参照
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag の作成/判定
    - monitoring_engine.py: 各モニタを束ねるエンジン
    - alert_manager.py: （アラート送信・LINE 等）※実装参照

  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
    - ExecutionEngine / Order 管理 / Broker 抽象化等

  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 発注株数計算（単元丸め・aggregate cap 等）
    - risk_adjustment.py: セクター上限・レジーム乗数

  - research/
    - factor_research.py: モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC・統計サマリ

  - ai/
    - news_nlp.py: ニュースセンチメントの LLM スコアリング
    - regime_detector.py: 市場レジーム判定（MA + マクロニュース + LLM）

  - tools/
    - paper_verification_report.py: Paper Trading の検証レポート生成

運用上の注意
-------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live の設定は本番運用になります。LINE 等の通知設定や Kill Switch の動作（KILL_FLAG_CLEAR_ON_START）が安全設定になっているか確認してください。
- run_execution/run_monitoring は PID ファイル / flag ファイル（data/*.pid, data/kill.flag, data/stop_requested.flag）を用いて起動・停止制御します。これらのファイルパスは Settings からカスタマイズ可能です。
- OpenAI を利用する機能は API 料金・レート制限に注意してください。API エラーはフェイルセーフで扱われますが、外部 API 呼び出しは運用コストとして考慮してください。

貢献・拡張案
--------------
- StrategyModel / Execution ロジックの差し替え（独自ブローカー実装の追加）
- ログ集約・メトリクス出力（Prometheus / Grafana 連携）
- テスト用モックの充実（news_nlp の API 呼び出し抽象化など）
- DuckDB テーブル設計のスキーマ管理スクリプト追加

ライセンス
----------
各プロジェクトポリシーに従ってください（リポジトリに LICENSE を配置することを推奨します）。

補足（よく使うコマンド）
-----------------------
- .env 作成ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  python -m kabusys.run_execution

- Monitoring 起動:
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。必要であれば README に含めるサンプル .env テンプレートや起動スクリプトの systemd / Supervisor 用サンプルユニットも作成します。必要な内容を教えてください。