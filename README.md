KabuSys
=======

日本株向けの自動売買・リサーチ基盤ライブラリ。  
ポートフォリオ構築、ポジションサイジング、監視（モニタリング）、ペーパートレード検証、LLM を使ったニュース解析／レジーム判定などの機能を含みます。

この README はリポジトリ内の主要スクリプト・モジュール群（src/kabusys 以下）を基に作成しています。

主な特徴
--------
- ポートフォリオ構築
  - 候補選定（スコア順/上位 N）
  - 等金額・スコア加重の重み計算
  - ポジションサイズ算出（リスクベース / 等分配 / スコアベース）
  - セクター上限適用・レジーム乗数対応
- 実行エンジン起動スクリプト（run_execution）
  - 本番 / ペーパートレード切替（paper_trading は MockBroker を使用し DB を分離）
  - リスク管理、注文管理、照合（reconciler）を統合してデーモン的に稼働
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
  - Kill Switch（条件により data/kill.flag を書き込んで Execution を停止）
- 研究・ファクター計算
  - モメンタム / バリュー / ボラティリティ等のファクターを DuckDB 上で計算
  - 将来リターン・IC（情報係数）計算、統計サマリ等
- AI（LLM）連携
  - ニュースのセンチメントを OpenAI（gpt-4o-mini を想定）でスコア化して ai_scores に保存
  - マクロニュース＋ETF MA を組み合わせた市場レジーム判定（regime_detector）
  - API 呼び出しはリトライ・バックオフ・レスポンス検証を実装
- 運用ユーティリティ
  - .env 対話式作成ウィザード（config_setup）
  - 起動前チェック（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）
  - 統一的なログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity ユーティリティ（utils.process_priority）

要件（推奨）
------------
- Python 3.10+
- pip install する外部パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML （config/*.yaml を検証する場合に必要）
- SQLite は標準ライブラリで利用

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repository-url>
2. Python 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 実際の環境に合わせて依存リストを用意している場合は requirements.txt を使ってください。
4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を配置（.env.example を参照）
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主要なデフォルト:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として exit(1) を返します

使い方（起動・ユーティリティ）
-----------------------------

- Execution エンジンを起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使い MockBrokerClient を利用します（本番 DB と分離）
    - data/execution.pid に PID を書き込む（pid_file_path）
    - data/stop_requested.flag があれば起動しない / 実行中に検出すると停止
    - 起動時にプロセス優先度を high に設定（utils.process_priority）
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔: 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能）
  - 監視は本番用 sqlite_path を常に参照（KABUSYS_ENV に依存しない）
  - 停止フラグ data/stop_requested.flag を検出するとループ終了
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（デフォルト: data/paper_trading.db）
- .env 対話式ウィザード
  - python -m kabusys.config_setup
  - 作成後は python -m kabusys.validate_config で検証を行ってください
- 設定検証 CLI
  - python -m kabusys.validate_config
  - --strict で警告を FAIL 扱い

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使い、発注はペーパー DB に記録
  - live: 本番。注意喚起が出ます
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL / LOG_DIR: ログ出力制御
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant / partial / never / reject）

運用メモ / ファイル
------------------
- 停止フラグ:
  - data/stop_requested.flag: run_execution / run_monitoring が監視する停止フラグ
  - data/kill.flag: KillSwitch が書き込むフラグ（ExecutionEngine 停止トリガー）
- PID ファイル:
  - data/execution.pid（デフォルト）に実行中 PID を書く
- ログ:
  - デフォルトは logs/<app_name>.log（utils.logging_setup）
  - 日次ローテーション・30日保持
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対する列追加（遡及的追加）を行う軽いマイグレーション処理を含む

ディレクトリ構成（要約）
-----------------------
以下は src/kabusys の主要ファイル・ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — 統一ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 + MonitoringDB クラス
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文系監視、スニペット内に存在）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch ロジック（flag ファイル）
    - monitoring_engine.py   — 上記 Monitor を束ねる実行エンジン
    - alert_manager.py       — （アラート送信管理、スニペットでは参照）
  - execution/                — Execution 系（broker_factory, execution_engine, order_manager 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み算出
    - position_sizing.py     — 株数決定・資金配分ロジック
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py            — ニュースセンチメントの LLM スコアリング
    - regime_detector.py     — マクロ + MA によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

サンプル .env（最小）
--------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

運用上の注意
-------------
- KABUSYS_ENV=live の設定は本番です。validate_config が警告を出します。LINE 通知設定などを必ず確認してください。
- Kill Switch / stop flag の取り扱いに注意してください（特に本番で自動クリアを許可する設定は危険）。
- OpenAI API キー周りは厳重に管理してください。API 失敗時のフォールバックはありますが、コストとレイテンシに注意。
- DuckDB / SQLite のファイルパスはバックアップ・アクセス権に注意して運用してください。

開発者向けメモ
--------------
- tests 用に環境変数読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（config.py）。
- OpenAI API 呼び出し部はテスト容易性のため _call_openai_api をモックできます（news_nlp, regime_detector）。
- monitoring_db は監視テーブルのスキーマ管理と軽量マイグレーションを提供します。

ライセンス・貢献
----------------
リポジトリのルートの LICENSE を参照してください。貢献する場合は issue / PR を送ってください。

---

補足や追加説明、README の例の具体化（ex. systemd ユニットファイル例、docker-compose 例、requirements.txt の生成など）をご希望でしたらお知らせください。