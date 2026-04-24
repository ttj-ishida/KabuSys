KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は Python 製の日本株自動売買/研究フレームワークです。  
主な役割は次の通りです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ機能
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- 実行エンジン（ExecutionEngine）による発注管理（本番 / ペーパートレード切替）
- 監視モジュール（Monitoring）によるプロセス・システム健全性監視、Kill Switch
- AI（OpenAI）を用いたニュースセンチメント・レジーム判定機能
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、レポート生成 等）

主要機能
--------
- 環境設定管理（.env 自動読み込み、Settings クラス）
- 実行エンジン（run_execution.py）
  - KABUSYS_ENV により paper_trading（MockBroker） と live を切替
  - paper_trading 用に専用 SQLite DB（data/paper_trading.db）を利用し本番 DB と分離
- 監視（run_monitoring.py / monitoring パッケージ）
  - CPU / メモリ / ディスクの監視、Execution プロセスの稼働確認、データ鮮度チェック
  - Kill Switch: 指定条件（ドローダウンやポジション上限等）で data/kill.flag を作成して Execution を停止
  - 監視情報は SQLite（デフォルト data/monitoring.db）に永続化
  - モニタリングのポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等金額/スコア加重、リスク調整（セクター上限・レジーム乗数）
  - ポジションサイズ計算（単元株丸め・aggregate cap）
- 研究（research パッケージ）
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を利用）
  - 将来リターン、IC（情報係数）、統計サマリー等
- AI ベース機能（ai パッケージ）
  - news_nlp: OpenAI を使ったニュースセンチメント計算（ai_scores テーブルへ書き込み）
  - regime_detector: ETF + マクロニュースで市場レジーム判定（market_regime へ書き込み）
  - OpenAI 呼び出しはリトライ・バリデーション・フェイルセーフ実装あり
- ユーティリティ
  - config_setup.py: 対話式 .env ウィザード
  - validate_config.py: 起動前チェック（.env, config/*.yaml の検証）
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

セットアップ
----------
前提
- Python 3.10+ を推奨
- SQLite（標準ライブラリ）
- 必要パッケージ（最低限）:
  - duckdb
  - psutil
  - openai （AI 機能を利用する場合）
  - PyYAML （config YAML の検証を行う場合、任意）

インストール例（venv を使う例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai pyyaml

3. プロジェクトの .env を作成
   - python -m kabusys.config_setup
     - ウィザードに従って必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力してください。
   - もしくは .env を手動で作成（.env.example を参照）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development|paper_trading|live）（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）（run_monitoring 用）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant|partial|never|reject）

使い方（起動・ユーティリティ）
--------------------------------

1. 監視ループの起動
   - python -m kabusys.run_monitoring
   - 挙動:
     - ログは logs/monitoring.log（デフォルト）へ日次ローテーションで出力
     - ポーリング間隔は MONITOR_POLL_INTERVAL で変更可能
     - data/stop_requested.flag を作成すると監視ループは終了（run_monitoring 側の停止フラグ）
     - 監視は常に本番用 sqlite_path を参照（監視 DB は環境に依らず本番パスを使用）

2. 実行エンジン（ExecutionEngine）の起動
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
     - プロセス優先度を high に設定（set_process_priority）
     - data/stop_requested.flag を検知したら安全に停止
     - PID ファイル: data/execution.pid（デフォルト）

3. .env ウィザード（対話式設定）
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

5. ペーパートレード検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスを指定する場合:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

6. AI 機能（プログラム的呼び出し）
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="xxxx")
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="xxxx")

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。
- デフォルトのログ出力先は logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）
- コンソール出力は stdout（cron などとの親和性を考慮）

監視・停止フラグについて
-----------------------
- stop_requested.flag: プロジェクト内 data/stop_requested.flag（run_monitoring と run_execution が参照）
  - 存在すると実行ループは終了（監視やエンジンが検知して安全に停止）
- kill.flag: Kill Switch（監視が判定して書き込む） — ExecutionEngine はこれを検出して停止
- kill_flag_clear_on_start 設定が 1 の場合、起動時に kill.flag を自動クリア（本番では 0 推奨）

ディレクトリ構成（概観）
-----------------------
以下は主要なモジュール・パッケージの位置（src/kabusys 以下）です。実際のリポジトリではさらにファイルが存在する場合があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/Settings 管理
    - config_setup.py          — .env ウィザード CLI
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (参照される)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (参照される)
    - execution/
      - execution_engine.py (参照される)
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/ (実行時に作成される想定)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - config/ (設定 YAML テンプレ等)
      - system_config.yaml
      - data_config.yaml
      - strategy_config.yaml
      - risk_config.yaml
      - execution_config.yaml
      - monitoring_config.yaml

設計上の注意点 / 動作ポリシー
---------------------------
- .env は決してリポジトリへコミットしないでください（config_setup のヘッダにも注意書きあり）。
- KABUSYS_ENV を正しく設定することで paper_trading（本番 DB と分離）や live の動作を切替可能です。
- AI 呼び出し（OpenAI）は API キーが必要で、失敗時は安全側のフォールバック（0.0 等）を使用する実装になっていますが、API キーの管理は責任を持って行ってください。
- run_monitoring はデフォルトで本番用の sqlite_path を使用します（監視 DB は環境にかかわらず同一の本番パスを想定）。

トラブルシューティング
-----------------------
- .env が自動読み込みされない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認
  - プロジェクトルートの判定は .git または pyproject.toml に依存します
- ログファイルが作れない場合:
  - LOG_DIR 環境変数で書き込み権限のあるディレクトリを指定するか、logs ディレクトリの権限を確認
- PyYAML がないと validate_config の YAML 検証はスキップされます（警告）

ライセンス・バージョン
----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリの LICENSE を参照してください（本 README では記載されていません）。

最後に
-----
この README はコードベースから抽出できる仕様・使い方をまとめたものです。運用前には必ず python -m kabusys.validate_config で設定検証を行い、.env を適切にセットアップしてください。必要であれば CI で validate_config を実行して設定漏れを検出することを推奨します。