KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買/リサーチ/監視ツール群を含むパッケージです。  
主に以下の機能を提供します。

- 日次のファクター計算・特徴量解析（DuckDB ベース）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- ExecutionEngine（発注処理）と Monitoring（監視・アラート・Kill Switch）
- Paper Trading（ペーパートレード）サポート（本番 DB と完全分離）
- ニュース NLP（OpenAI を用いたセンチメントスコアリング）
- 各種ユーティリティ（設定ウィザード、設定検証、レポート生成）

主要な設計方針：
- 本番とペーパートレードは DB を分離（PAPER_TRADING_SQLITE_PATH）
- .env / .env.local から環境変数を自動ロード（必要に応じて無効化可能）
- ログは stdout と日次ローテートファイルに出力（logs/<app>.log）
- OpenAI を使う機能は API キー（OPENAI_API_KEY）を必要とする

主な機能一覧
--------------
- 環境設定
  - config_setup.py: 対話式に .env を作成/更新
  - validate_config.py: .env や config/*.yaml の事前検証

- 実行系
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用
  - run_monitoring.py: SystemMonitor（ポーリング監視）を起動

- 監視 / リスク管理
  - monitoring/)
    - monitoring_db.py: 監視ログ用 SQLite のスキーマ初期化・永続化 API
    - system_monitor.py, trade_monitor.py, risk_monitor.py: 監視ロジック
    - monitoring_engine.py: 各 Monitor を束ねたポーリングエンジン
    - kill_switch.py: 条件達成時に data/kill.flag を書き込む Kill Switch
    - alert_manager.py: （アラート送信を担う想定コンポーネント）

- 発注ロジック
  - execution/ 以下: BrokerFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler 等

- リサーチ / ファクター
  - research/
    - factor_research.py: Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py: 将来リターン計算、IC 計算、統計サマリ

- AI 関連
  - ai/news_nlp.py: raw_news を集約して OpenAI でセンチメント評価 → ai_scores 書込
  - ai/regime_detector.py: ma200 とマクロニュースの LLM 評価で市場レジーム判定

- ポートフォリオ構築
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py

- ツール
  - tools/paper_verification_report.py: Paper Trading DB から検証レポートを生成

セットアップ手順
----------------

前提
- Python 3.9+（ソースは型ヒントで Union Types 等を使用）
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML 検証を使う場合）
- SQLite（標準ライブラリで利用可）

インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（pip）
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt があれば pip install -r requirements.txt）

環境変数設定
- プロジェクトルートに .env を作成してください。.env の生成をウィザードで行うことができます:
  - python -m kabusys.config_setup
- 主要な環境変数（主なもの）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - LOG_LEVEL — デフォルト: INFO
  - OPENAI_API_KEY — news_nlp / regime_detector を使う場合
  - PAPER_FILL_MODE — paper_trading における約定挙動（instant/partial/never/reject）
- 自動ロード:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動でロードします
  - 無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も FAIL（exit code 1）として扱います

使い方（主要コマンド）
--------------------

1) 環境ウィザード（.env 作成）
- python -m kabusys.config_setup
  - 対話的に .env を生成できます
  - 生成後に python -m kabusys.validate_config で検証してください

2) ExecutionEngine（発注処理）起動
- 本番またはペーパートレードを起動:
  - python -m kabusys.run_execution
- 動作のポイント:
  - KABUSYS_ENV=paper_trading のとき、専用の PAPER_TRADING_SQLITE_PATH に記録され本番 DB と分離されます
  - 起動時に data/stop_requested.flag が存在すると起動を中止します
  - 実行中に停止させたい場合は monitoring の Kill Switch により data/kill.flag が書き込まれるか、
    手動で stop フラグを立てる等の運用が想定されます
  - 実行中は data/execution.pid に PID が書き込まれます

3) Monitoring 起動（ポーリングループ）
- python -m kabusys.run_monitoring
- 環境変数:
  - MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒）。デフォルト 60 秒。1 未満の値は無効でデフォルトにフォールバック。
- 停止方法:
  - プロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します
  - Kill Switch（監視側）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine の停止を誘発します
- ログ:
  - logs/monitoring.log に日次ローテートで出力（30 日分保持）

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --db PATH --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
  - 稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定を出します

5) AI / リサーチ機能
- news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キー（環境変数 OPENAI_API_KEY または引数 api_key）が必要です
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ma200 とマクロニュースの LLM 評価により regime を判定し DB に保存します
- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns などは DuckDB 接続を受け取り純粋関数として使用可能

主要ファイル・ディレクトリ構成
---------------------------
（src/kabusys 以下を抜粋）

- run_monitoring.py       — SystemMonitor（監視）起動スクリプト
- run_execution.py        — ExecutionEngine 起動スクリプト
- config.py               — Settings クラス（.env / 環境変数読み取り）
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 設定検証 CLI

- monitoring/
  - monitoring_db.py      — SQLite スキーマ初期化・永続化 API
  - system_monitor.py     — システム状態・データ鮮度監視
  - trade_monitor.py      — 注文テーブル監視（滞留・異常検出）
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - kill_switch.py        — kill.flag 管理
  - monitoring_engine.py  — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py      — アラート送信（実装依存）

- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- research/
  - factor_research.py
  - feature_exploration.py

- ai/
  - news_nlp.py          — OpenAI を用いたニュースセンチメント
  - regime_detector.py   — 市場レジーム判定（ma200 + LLM）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py     — 統一ログ設定（stdout + 日次ファイルローテーション）
  - process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意点 / Tips
---------------------
- デフォルト DB / データディレクトリ:
  - デフォルトの DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
- Kill / Stop フラグ:
  - data/kill.flag: Kill Switch が設定されると ExecutionEngine に停止命令（Execution 側で監視している想定）
  - data/stop_requested.flag: run_monitoring / run_execution の外部的停止制御にも使用
- 本番環境 (KABUSYS_ENV=live) に切り替える際は validate_config.py の警告を必ず確認してください
- OpenAI の呼び出しには課金やレート制限があるため、news_nlp / regime_detector は運用での考慮が必要
- ログレベルは LOG_LEVEL 環境変数で調整可能。debug 情報が欲しい場合は DEBUG に設定

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリのトップレベルに配置してください（ここには含まれていません）

最後に
------
まずは .env を作成（python -m kabusys.config_setup）、その後設定検証（python -m kabusys.validate_config）を行い、ローカルでは paper_trading モードで動作確認することを推奨します。質問や追加のドキュメント（API 詳細、データスキーマ、運用手順）が必要であれば教えてください。