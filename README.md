README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python コードベースです。  
主な目的は以下のとおりです。

- 日次/リアルタイムのシグナル生成・ポートフォリオ構築（portfolio）
- 発注実行（ExecutionEngine）およびペーパートレードの分離
- システム監視・リスク監視・Kill Switch（監視 → 必要時に停止フラグ作成）
- DuckDB を使ったファクター計算やリサーチ機能
- OpenAI を使ったニュース NLP／レジーム判定の補助機能
- 各種ツール（ペーパー検証レポート生成など）

特徴
----
- 環境変数・.env による設定管理（config.py）と対話式ウィザード（config_setup.py）
- 本番/ペーパートレードの DB 分離（paper_trading 用 SQLite）
- Monitoring: system / trade / risk を個別にチェックし、kill.flag を出す仕組み
- DuckDB を利用したファクター計算・研究用処理（research パッケージ）
- OpenAI（gpt-4o-mini 等）を利用するニュースセンチメント & レジーム判定（ai パッケージ）
- ログはコンソール + 日次ローテーションファイル（logs/*.log）で出力

必須依存（概略）
----------------
最低限必要なライブラリ（install 時に適宜追加してください）:
- Python >= 3.10
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証を行う場合に必要）
- その他プロジェクトによる追加依存（実装次第）

セットアップ（ローカル開発向け）
-----------------------------
1. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

3. .env の作成
   - 対話的ウィザードで生成:
     - python -m kabusys.config_setup
   - 手動作成: プロジェクトルートに .env を置く（.env.example を参考に）

   重要な環境変数（抜粋）
   - JQUANTS_REFRESH_TOKEN ... J-Quants API 用（必須）
   - KABU_API_PASSWORD       ... kabuステーション API パスワード（必須）
   - KABUSYS_ENV             ... execution モード: development / paper_trading / live（デフォルト: development）
   - DUCKDB_PATH             ... DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH             ... 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH ... ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
   - LOG_LEVEL               ... ログレベル（DEBUG/INFO/...）
   - OPENAI_API_KEY          ... OpenAI API キー（ai.news_nlp / regime_detector に必要）
   - PAPER_FILL_MODE         ... ペーパートレードの約定モード（instant/partial/never/reject）
   - KILL_FLAG_CLEAR_ON_START ... 起動時に kill.flag を自動クリアするか（0/1）

   注意: config.py は自動で .env を読み込みます（プロジェクトルートの検出に失敗した場合はスキップ）。
   自動ロードを無効化したい場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定検証
--------
.env や config/*.yaml の基本整合性チェック:
- python -m kabusys.validate_config
  - --strict を付けると警告があると失敗（exit 1）になります

起動・使い方
------------

1) ExecutionEngine（発注エンジン）起動
- 本番/開発/ペーパーは KABUSYS_ENV によって挙動が変わります。
- ペーパートレード時（KABUSYS_ENV=paper_trading）は MockBrokerClient を使い、data/paper_trading.db に記録されます（本番 DB と分離）。
- 実行:
  - python -m kabusys.run_execution

- 停止方法:
  - run_execution はプロセス間で stop flag (data/stop_requested.flag) を監視します。停止したい場合はこのファイルを作成してください。
  - 監視コンポーネントが Kill Switch 条件を満たした場合は data/kill.flag が書き込まれ、Engine 側でそれを検出して停止できます（設定次第）。

- PID ファイル:
  - data/execution.pid に PID を書きます（設定で変更可能）

2) Monitoring（監視プロセス）起動
- 監視は MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor を用いてシステム状態や注文状態を定期的にチェックします。
- 実行:
  - python -m kabusys.run_monitoring

- ポーリング間隔:
  - デフォルト 60 秒
  - 環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: export MONITOR_POLL_INTERVAL=30）

- 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使ってログを永続化します（monitoring は KABUSYS_ENV に依存せず production sqlite_path を使用する実装になっています）。

3) ペーパートレード検証レポート生成
- usage:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db）

4) AI / リサーチ機能
- ニュース NLP（ai.news_nlp.score_news）や市場レジーム判定（ai.regime_detector.score_regime）は OpenAI API キーが必要です（環境変数 OPENAI_API_KEY）。
- DuckDB 接続を渡して呼び出す設計になっています。直接 CLI エントリは用意されていませんが、モジュール経由で利用できます。

ファイルベースの停止・リセット
-----------------------------
- stop_requested.flag: run_monitoring / run_execution が監視している「即時停止」フラグ（停止要求）
- kill.flag: Kill Switch が書き込むファイル。ExecutionEngine に停止を促す用途
- 実行前に kill.flag を削除したい場合は KILL_FLAG_CLEAR_ON_START=1 設定により自動クリアできます（本番では推奨しません）

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging で統一的に設定されます。
  - 出力先: stdout と logs/<app_name>.log（日次ローテーション、30日保持）
  - LOG_DIR 環境変数でログディレクトリを変更可能

ディレクトリ構成（主要部分）
---------------------------
以下は主要なソース配置の概要（src/kabusys 以下）。実際のリポジトリでは pyproject.toml 等がプロジェクトルートに存在します。

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数/.env 読み込み・Settings
    - config_setup.py              # .env 対話ウィザード
    - validate_config.py           # 設定検証 CLI
    - run_execution.py             # ExecutionEngine 起動スクリプト
    - run_monitoring.py            # Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py                # ニュースセンチメント（OpenAI）
      - regime_detector.py         # 市場レジーム判定
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py           # (存在: 実装参照)
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py          # (存在: 実装参照)
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - execution/                   # Execution 関連コンポーネント（Engine, BrokerFactory 等）
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/                  # 監視関連（上記）
    - portfolio/                   # ポートフォリオ構築（上記）
    - research/                    # リサーチ（上記）
    - data/ ...                    # データ格納 (data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb)

開発上の注意点 / 実装上の留意事項
--------------------------------
- config.py はプロジェクトルート（.git または pyproject.toml の存在）を基準に .env 自動ロードを行います。テスト環境等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Logging のファイル出力はログディレクトリ作成に失敗した場合に自動で無効化され、コンソール出力のみ継続します。
- run_execution のペーパートレードは本番 DB と分離されます（paper_trading 用 sqlite ファイルを使用）。
- AI 呼び出し（OpenAI）はネットワークエラー・429 等に対して指数バックオフでリトライする実装です。API キーは必須です。
- DuckDB を用いる処理は接続オブジェクトを受け取り SQL を実行するスタイルです（外部副作用を避ける設計）。
- Python の型注釈（例: Path | None）を利用しているため Python >= 3.10 を推奨します。

よくある操作例
--------------
- .env を作る（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視デーモンを起動（開発用）
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- Execution 起動（ペーパー/本番は KABUSYS_ENV で決定）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

貢献 / 拡張案
-------------
- Broker クライアント（kabu ステーション連携）の実装強化・認証周りの整理
- stocks マスタで lot_size 等を管理して position_sizing を拡張
- ai モジュールのテスト用モック抽象化（現在も一部は差し替え可能）
- CI 用の設定検証パイプライン（validate_config を CI に組み込む）

ライセンス
----------
プロジェクトに付与されたライセンスに従ってください（リポジトリに LICENSE ファイルがある場合はそちらを参照）。

お問い合わせ
------------
実装内容・使い方に関する質問はリポジトリの Issue へお願いします。