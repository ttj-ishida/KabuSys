README
======

概要
----
KabuSys は日本株向けの自動売買・研究基盤です。戦略の研究（ファクター計算・特徴量解析）、ポートフォリオ構築（候補選定・配分・ポジションサイズ計算）、実行エンジン（ExecutionEngine）および監視（Monitoring）機能、さらにニュースを用いた AI スコアリングなどのユーティリティ群を含みます。本リポジトリは主にライブラリ＋複数の起動スクリプト / CLI を提供します。

主な特徴
--------
- 戦略研究
  - ファクター計算: モメンタム / バリュー / ボラティリティ（DuckDB を用いた計算）
  - 将来リターン・IC 計算、統計サマリ等の研究ユーティリティ
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重配分
  - セクター集中制限、レジーム乗数
  - ポジションサイズ計算法（ロット丸め・リスクベースなど）
- 実行エンジン（Execution）
  - 本番 / ペーパートレード分離（ペーパー時は専用 SQLite）
  - ブローカークライアント抽象化、リスク管理、注文管理
- 監視（Monitoring）
  - システム状態・データ鮮度・取引ログの監視、Kill Switch、アラート連携
  - 監視用 DB（SQLite）への永続化
- AI（OpenAI）
  - ニュース NLP による銘柄別センチメントスコアリング（ai_scores）
  - 市場レジーム判定（MA200 とマクロニュースの LLM 評価の合成）
- 運用ツール
  - .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

前提・依存
----------
- Python 3.9+（ソース内の型ヒント等を想定）
- 推奨パッケージ（主に requirements.txt 等で管理を想定）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証用、必須ではない）
- 標準ライブラリ: sqlite3, logging, threading, datetime など
- 実行環境での外部 API を使う場合は対応する認証情報（J-Quants / kabuステーション / OpenAI 等）が必要

セットアップ手順
----------------
1. リポジトリをクローン / 配布パッケージを取得
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. .env の用意
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env を手動作成（例は下記参照）
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになる: python -m kabusys.validate_config --strict
6. データディレクトリの用意
   - デフォルトでは data/ 以下に SQLite / pid / flag ファイル等を作成します。必要に応じて .env でパスを変更してください。

主要な環境変数（抜粋）
---------------------
（詳しくは src/kabusys/config.py を参照）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能で必要)
- KABUSYS_ENV: execution モード（development / paper_trading / live） デフォルト: development
  - paper_trading 時は発注をモック化し専用 DB(data/paper_trading.db)を使用
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 SQLite, デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- MONITOR_POLL_INTERVAL (監視のポーリング間隔; run_monitoring では環境変数で上書き可能, デフォルト: 60 秒)
- その他: PID/kill flag のパスや監視閾値など（config.py を参照）

よく使うファイル / スクリプト
-----------------------------
- 環境セットアップ・検証
  - python -m kabusys.config_setup       # .env を対話式作成
  - python -m kabusys.validate_config    # 設定検証
- 実行関連
  - python -m kabusys.run_execution      # ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード DB に記録
  - python -m kabusys.run_monitoring     # SystemMonitor をポーリング起動
    - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能
- ツール
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - ペーパートレード用 SQLite の実行結果から検証レポートを生成
- ライブラリ利用例（アプリケーション／テスト内で呼び出して利用）
  - kabusys.research.calc_momentum(conn, date)
  - kabusys.portfolio.select_candidates(...)
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

運用上の注意
-------------
- 停止 / 強制停止フロー
  - monitoring/run_execution 等は data/stop_requested.flag や data/kill.flag の存在を確認して停止や Kill Switch を処理します。運用時はフラグファイルの扱いに注意してください。
  - KillSwitch はリスク条件（ドローダウンやポジション上限）を満たした場合に data/kill.flag を書き込み、ExecutionEngine の停止トリガーになります。
- ログ
  - ログは logs/<app_name>.log に日次ローテートで保存されます（デフォルト logs/）。環境変数 LOG_DIR で変更可能。
- Paper Trading
  - KABUSYS_ENV=paper_trading 時は本番 DB を使用せず paper_sqlite_path を用います（完全分離）。PAPER_FILL_MODE で約定動作を制御できます（instant/partial/never/reject）。
- AI 機能
  - OpenAI API を利用する機能は OPENAI_API_KEY が必要です。API 呼び出しはリトライやフェイルセーフを備えていますが、API 制限やコストに注意してください。
- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して .env/.env.local を自動読み込みします。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                   — 環境変数 / 設定管理
- config_setup.py             — .env 対話式ウィザード
- validate_config.py          — 設定検証 CLI
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — SystemMonitor ポーリング起動スクリプト

パッケージ群:
- ai/
  - news_nlp.py                — ニュース NLP スコアリング（OpenAI 連携）
  - regime_detector.py        — 市場レジーム判定（MA200 + マクロニュース）
- monitoring/
  - monitoring_db.py           — 監視用 SQLite のスキーマ / DB 操作
  - system_monitor.py          — システム状態・データ鮮度監視
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - kill_switch.py             — kill.flag の作成 / 管理
  - monitoring_engine.py       — 各 Monitor を束ねるエンジン
  - alert_manager.py*          — （アラート送信ロジック、未示の実装箇所）
  - trade_monitor.py*          — （約定/注文監視、未示の実装箇所）
- execution/
  - execution_engine.py*       — 実行エンジン（起動・セッション管理）
  - broker_factory.py*         — ブローカークライアント生成
  - order_manager.py*          — 注文管理
  - order_repository.py*       — 注文履歴永続化
  - reconciler.py*             — 注文整合性チェック
  - risk_manager.py*           — 実取引リスク管理
- portfolio/
  - portfolio_builder.py       — 候補選定・重み計算
  - position_sizing.py         — ポジションサイズ計算
  - risk_adjustment.py         — セクター制限・レジーム乗数
- research/
  - factor_research.py         — ファクター計算（momentum/value/volatility）
  - feature_exploration.py     — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py           — 一貫したログ設定ユーティリティ
  - process_priority.py        — プロセス優先度/CPU affinity 設定ユーティリティ
- monitoring/monitoring_db.py  — 監視 DB スキーマ（再掲、上位）

（* はこの README に含まれる一覧の一部で、完全な実装ファイルはリポジトリ内をご確認ください）

簡単な使用例
-------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視プロセスの起動（バックグラウンド実行等は運用に合わせて）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動（ペーパートレード）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サンプル .env（最小）
--------------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

ライセンス / バージョン
-----------------------
パッケージバージョン: src/kabusys/__version__ = 0.1.0
ライセンス情報はリポジトリのルート（LICENSE 等）を参照してください。

補足
----
- 各モジュールの詳細な使い方・パラメータや内部アルゴリズムはソース内の docstring に記載されています。運用時は特に監視・Kill Switch・リスク設定・AI API キーの管理に注意してください。
- DuckDB / SQLite のスキーマやマイグレーションは monitoring_db.init_monitoring_db などに実装されています。既存 DB を扱う際は互換性に注意してください。

ご不明点があれば、どの部分（セットアップ / 実行 / 各モジュールの使い方）について詳しく知りたいか教えてください。README をより運用向けにカスタマイズして追記します。