README
=====

概要
----
KabuSys は日本株の自動売買・研究を支援するモジュール群です。  
主に以下の機能を持ち、実運用（live）・ペーパートレード（paper_trading）・開発（development）環境を想定しています。

- 発注エンジン（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- 研究用ファクター計算・特徴量解析（DuckDB ベース）
- ニュース NLP（OpenAI を使った銘柄センチメント評価）
- 設定ウィザード・設定検証・分析ツール（レポート出力）

主な特徴
--------
- 明確に分離された環境（live / paper_trading / development）
- DuckDB を使った高速な時系列・ファイナンス計算
- OpenAI を使ったニュースセンチメント・レジーム判定（プラグイン的に利用）
- SQLite による監視ログ・トレードログ永続化
- 実行プロセスの優先度設定・ログ管理の統一ユーティリティ
- .env ウィザードとバリデーション CLI による導入支援

要件
----
- Python 3.10 以上（型注釈に union 型記法等を使用）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証に使用）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワークアクセス（kabuステーション API / OpenAI を利用する場合）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証を使う場合）pip install pyyaml

   ※ 実プロジェクトでは requirements.txt を用意している想定です:
     pip install -r requirements.txt

4. 初期設定（.env ファイル作成）
   - 対話式ウィザードで .env を作成
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データ / ログ ディレクトリの準備
   - デフォルトでは data/ と logs/ にファイルを保存します。必要に応じてパスを .env で上書きしてください。

主要な環境変数（.env）
---------------------
主なキー（設定ウィザードを参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 環境用）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番環境では 0 推奨）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動: instant | partial | never | reject

（注）自動的に .env.local が .env より優先して読み込まれ、OS 環境変数は上書きされません。

起動と使い方
------------

- 設定ウィザード
  - python -m kabusys.config_setup
    対話形式で .env を作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
    起動前に必須環境変数やファイル配置をチェックします。

- Execution Engine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
    - 起動時に data/stop_requested.flag があれば起動せず終了します。
    - 実行中に data/stop_requested.flag が作られると安全停止します。
    - PID ファイルは data/execution.pid（デフォルト）に出力されます。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
    - 監視は常に本番用 sqlite_path（SQLITE_PATH）を参照します（環境に依存しない）
    - data/stop_requested.flag によりループを終了します

- 停止・Kill Switch
  - リスク判定（ドローダウンやポジション上限）で KillSwitch がトリガーされると data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番では推奨されません）。
  - 手動停止: data/stop_requested.flag を作成して run_execution/run_monitoring を安全に終了させます。

- ロギング
  - デフォルトログディレクトリ: logs/
  - setup_logging により stdout と日次ローテートログ（logs/<app_name>.log）を併用
  - ログレベルは .env の LOG_LEVEL で設定

ツール
-----
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - データソースは PAPER_TRADING_SQLITE_PATH（または --db で指定）

ライブラリ／モジュール概要
------------------------
- kabusys.config
  - 環境変数読み込み・Settings クラスを提供（.env 自動ロード機能あり）
- kabusys.config_setup
  - .env を対話的に作成するウィザード
- kabusys.validate_config
  - 起動前の設定検証 CLI
- kabusys.run_execution
  - ExecutionEngine 起動スクリプト
- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動スクリプト
- kabusys.monitoring
  - monitoring_db.py: SQLite テーブル初期化 / 永続化 API
  - system_monitor.py, trade_monitor.py, risk_monitor.py: 各種監視ロジック
  - monitoring_engine.py: 各 Monitor を束ねるループ
  - kill_switch.py: kill.flag ロジック
  - alert_manager.py: （アラート送信ロジック）
- kabusys.execution
  - ExecutionEngine、OrderManager、RiskManager、Reconciler、BrokerFactory など（発注周り）
- kabusys.portfolio
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み付け・株数算出・セクター制限など
- kabusys.research
  - factor_research.py, feature_exploration.py
  - DuckDB を用いたファクター算出・IC 計測・統計サマリー
- kabusys.ai
  - news_nlp.py: OpenAI を用いたニュースセンチメント集計
  - regime_detector.py: 市場レジーム判定（MA + マクロセンチメント合成）
- kabusys.utils
  - logging_setup.py: ログ初期化ユーティリティ
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
  __init__.py
  config.py
  config_setup.py
  validate_config.py
  run_execution.py
  run_monitoring.py
  tools/
    __init__.py
    paper_verification_report.py
  ai/
    __init__.py
    news_nlp.py
    regime_detector.py
  monitoring/
    monitoring_db.py
    system_monitor.py
    trade_monitor.py
    risk_monitor.py
    kill_switch.py
    monitoring_engine.py
    alert_manager.py
  execution/
    (ExecutionEngine, order_manager, broker_factory, ...)
  portfolio/
    portfolio_builder.py
    position_sizing.py
    risk_adjustment.py
    __init__.py
  research/
    factor_research.py
    feature_exploration.py
    __init__.py
  utils/
    logging_setup.py
    process_priority.py
    __init__.py
  data/                # 実行時に使用する（例: monitoring.db, paper_trading.db, kill.flag 等）
  logs/                # ログファイル出力先（デフォルト）

運用上の注意
------------
- 本番（KABUSYS_ENV=live）での起動前には必ず python -m kabusys.validate_config を実行し、LINE 通知などの設定が有効か確認してください。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。運用では 0 を推奨します。
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要です。API 呼び出し失敗時はフェイルセーフ（スコア 0.0 等）で継続する設計ですが、結果の解釈には注意してください。
- DuckDB・SQLite のパスは .env で変更可能です。データのバックアップや場所の管理に注意してください。

開発メモ
--------
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml により判定）から行われます。テストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テストや CI では OpenAI 呼び出しや外部 API をモック化して実行することを推奨します（各モジュール内の API 呼び出し関数はパッチしやすい構成を意図しています）。
- DuckDB のクエリは大量データ処理を想定しており、リターンやウィンドウの設計をコメントで明記しています。研究用関数は副作用を持たない純関数群を目標に設計されています。

サポート・フィードバック
----------------------
不具合や改善提案はリポジトリの Issues に登録してください。

---

この README はコードベースの主要機能と運用方法をまとめたものです。実際の運用前には config_setup と validate_config を利用して環境を正しく整えてください。