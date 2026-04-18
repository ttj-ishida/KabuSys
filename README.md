README
======

概要
----
KabuSys は日本株向けの自動売買・研究基盤ライブラリです。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）起動スクリプト（本番 / ペーパートレード対応）
- 監視サブシステム（System / Trade / Risk のモニタ）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用モジュール（ファクター計算、特徴量探索、IC 計算）
- ニュース NLP（OpenAI を使ったセンチメント評価）および市場レジーム判定
- Paper Trading 検証レポート生成ツール
- 環境設定ウィザードと設定検証 CLI

主な設計方針
- 本番環境とペーパートレードを明確に分離（DB も分離可能）
- DuckDB を解析用 DB、SQLite を監視 / 取引ログ用に利用
- LLM（OpenAI）呼び出しはリトライやバリデーションを組み込みフェイルセーフに設計
- 自動起動時の .env 読み込み機能（必要に応じて無効化可能）

機能一覧
--------
- 実行 / 監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（停止フラグで終了）
- 環境設定・検証
  - config_setup.py: 対話式 .env ウィザード（キー/パス/トークンの初期化）
  - validate_config.py: .env と config/*.yaml の事前検証（--strict オプションあり）
- 監視・リスク管理
  - system_monitor / trade_monitor / risk_monitor / kill_switch / monitoring_engine
  - MonitoringDB: SQLite に監視ログを永続化
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、セクター制限、position sizing（lot 単位丸め・aggregate cap）
- リサーチ
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - feature_exploration.py: 将来リターン・IC・統計サマリ
- AI 関連
  - news_nlp.py: ニュース記事を OpenAI でスコア化 -> ai_scores テーブルへ書込
  - regime_detector.py: ETF (1321) の MA とマクロニュースで市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB を集計し PASS/FAIL 判定の検証レポートを出力

要件（推奨）
-------------
- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML — config/*.yaml の内容検証に使用
- SQLite は標準ライブラリで利用

インストール例
--------------
1. Python 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows (PowerShell 等)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 解析を使う場合）pip install PyYAML

（必要に応じて requirements.txt を作成して pip install -r で管理してください）

セットアップ手順
----------------
1. プロジェクトルートへ移動（.env/.git があるディレクトリ）
2. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabu API パスワード、DB パスなどを入力して .env を生成します
3. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗として扱います（exit code 1）
4. データディレクトリ作成（手動または起動時に自動作成されます）
   - mkdir -p data logs
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

環境変数（主要）
----------------
これらは .env で管理します。主要なキー:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は paper DB (PAPER_TRADING_SQLITE_PATH) + MockBroker を使用
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — 監視 DB
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs）
- OPENAI_API_KEY（AI モジュール使用時）
- KILL_FLAG_CLEAR_ON_START（0/1、本番で 0 推奨）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると起動時の .env 自動読込を無効化できます

使い方（主要コマンド）
--------------------

- 対話式 .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は .env の KABUSYS_ENV に関係なく本番 sqlite_path（SQLITE_PATH）を監視 DB として使います
  - 停止: data/stop_requested.flag を作成すると安全にループが終了します

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
  - 起動中に data/stop_requested.flag を作成するとエンジンを停止します
  - PID ファイル: data/execution.pid（デフォルト）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコアリング / レジーム判定（プログラムから呼び出す例）
  - 例: news のスコア化
    - from datetime import date
    - import duckdb
    - from kabusys.ai import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")

ログ設定
--------
- setup_logging() により stdout とファイル（logs/<app_name>.log、日次ローテーション）に出力します
- ログレベルは LOG_LEVEL 環境変数または引数で制御可能
- ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみで継続します

停止フラグ / Kill Switch
------------------------
- data/stop_requested.flag: run_execution / run_monitoring の外部停止シグナル
- KillSwitch は監視モジュールから条件（ドローダウン・ポジション上限など）を満たすと data/kill.flag を書き込みます
  - ExecutionEngine は kill.flag の存在を検出すると停止する設計です
- .env の KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を自動消去します（本番では 0 推奨）

データベース（既定）
-------------------
- DuckDB: data/kabusys.duckdb — リサーチ用テーブル（prices_daily, raw_financials, raw_news などを想定）
- SQLite (監視): data/monitoring.db — monitoring_db が作成するテーブル（system_status, trade_logs, positions, risk_logs, dashboard）
- SQLite (paper): data/paper_trading.db — ペーパートレード用の分離 DB（KABUSYS_ENV=paper_trading で使用）

ディレクトリ構成
----------------
以下は src/kabusys 内のおおよその構成（主要ファイルのみ抜粋）:

- kabusys/
  - __init__.py
  - config.py                 # 環境変数読み込み・Settings
  - config_setup.py           # .env 対話ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                     # 実行時に使われる（例: monitoring.db, kabusys.duckdb, kill.flag 等）
  - logs/                     # ログ出力先（デフォルト）

開発上の注意点 / トラブルシューティング
----------------------------------------
- Python バージョンは 3.10 以上を推奨（型注釈に | 演算子を使用）
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- validate_config.py は PyYAML がない場合、config/*.yaml の内容検証をスキップして警告を出します。詳細な YAML 検証を行いたい場合は PyYAML をインストールしてください
- OpenAI を利用するモジュールは API キーが必須です。API 呼び出しにはリトライとフェイルセーフが含まれますが、キーを設定しておくこと
- DuckDB / SQLite のファイルパスは .env で変更可能。運用時はバックアップやファイル権限に注意してください

ライセンス・貢献
----------------
本 README にはライセンス情報は含まれていません。リポジトリに LICENSE があればそちらを参照してください。バグ報告や機能要望は issue を作成してください。

以上が本コードベースの概要および使用手順です。必要であれば各モジュール（ExecutionEngine、Monitoring 内部実装など）の詳細ドキュメントも作成します。どの部分の追記を優先するか教えてください。