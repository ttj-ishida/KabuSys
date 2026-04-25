KabuSys — 日本株自動売買システム（README）
=======================================

概要
----
KabuSys は日本株向けの自動売買／研究基盤の軽量実装です。本リポジトリは以下の機能群を含みます。

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）  
  - 本番 / ペーパートレード切替、注文管理・リスク管理・約定照合など（ブローカー抽象化）
- 監視コンポーネント（Monitoring）起動スクリプト（run_monitoring）  
  - システム状態監視、取引監視、リスク監視、Kill Switch、アラート
- 研究モジュール（research）  
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）、将来リターン・IC 評価、統計サマリ
- ポートフォリオ構築ユーティリティ（portfolio）  
  - 候補選定、重み付け、ポジションサイジング、セクターキャップ、レジーム乗数
- AI 支援（ai）  
  - ニュースのセンチメント評価（OpenAI）や市場レジーム判定
- ユーティリティ（utils）  
  - ログ設定、プロセス優先度／CPU affinity 設定、設定ロード等
- 運用支援ツール（tools）  
  - Paper Trading 検証レポート生成 等

主な特徴
--------
- 環境変数 / .env による設定（config_setup で対話的に .env 作成可能）
- KABUSYS_ENV による mode 切替（development / paper_trading / live）
- DuckDB（分析 DB）と SQLite（監視・発注履歴等）を併用
- OpenAI を用いたニュース NLP／リスク解析（API キーは環境変数で指定）
- 監視ループはフラグファイルにより安全に停止可能（data/stop_requested.flag / data/kill.flag）

セットアップ手順（開発環境向け）
-------------------------------
1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 基本依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合）
   - 例（pip）:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt はこのリポジトリに含まれていないため、環境に応じて必要パッケージをインストールしてください。

3. .env の作成
   - 対話型ウィザードで作成:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他主要な環境変数（省略可／デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード時の DB（data/paper_trading.db）
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能使用時に必要

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

基本的な使い方
--------------

1. 監視ループの起動（Monitoring）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
   - 起動:
     - python -m kabusys.run_monitoring
   - 補足:
     - 監視は sqlite_path（Settings.sqlite_path）を使用します。Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を参照します。
     - 停止: プロセスを終了するかプロジェクトルート/data/stop_requested.flag を作成するとループを終了します。

2. 実行エンジンの起動（Execution）
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用します。本番は実ブローカーを使用します。
   - 起動:
     - python -m kabusys.run_execution
   - 補足:
     - 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了します。
     - 停止は data/stop_requested.flag を作成するか、監視コンポーネントの Kill Switch（data/kill.flag）で指示できます。

3. Paper Trading 検証レポート
   - SQLite（ペーパートレード DB）を読み取り、稼働率・成功率・レイテンシ等のレポートを出力します。
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

4. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で渡す）
   - プログラムから直接呼ぶ例（Python）:
     - from kabusys.ai.news_nlp import score_news
     - from kabusys.ai.regime_detector import score_regime
     - 両関数は DuckDB 接続（DuckDBPyConnection）と target_date を受け取り DB に書き込みます。
   - 実行時の失敗はフェイルセーフ（API 失敗時はスコアを 0 にする等）で設計されています。

ログ・出力
---------
- logging は kabusys.utils.logging_setup.setup_logging で統一設定されます。
- デフォルトで stdout（コンソール）出力に加え logs/<app_name>.log に日次ローテーションで保存します（LOG_DIR 環境変数で変更可）。
- ログレベルは .env の LOG_LEVEL または setup_logging の引数で制御できます。

監視・停止フラグ
----------------
- data/stop_requested.flag — 起動スクリプト（run_monitoring / run_execution）がループを終了するために監視するフラグ（存在すれば停止処理）。
- data/kill.flag — KillSwitch が書き込む停止シグナル（ExecutionEngine に対する停止要求）。存在する場合 ExecutionEngine は停止されます。
- PID ファイル: data/execution.pid（ExecutionEngine 起動時に書き込まれる）

主要な設定ロード挙動
-------------------
- 自動でプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数を破壊しないよう保護）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env のパーサは export 句、クォート、コメント等に対応した堅牢な実装です。

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルとモジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring 起動スクリプト
  - run_execution.py         — Execution 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（schema init / CRUD）
    - system_monitor.py      — システム状態・データ鮮度チェック
    - trade_monitor.py       — （取引監視：滞留注文／約定異常等）※実装参照
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch（flag 書き込み）
    - monitoring_engine.py   — 各 Monitor をまとめるエンジン
    - alert_manager.py       — アラート送信（LINE 等）※実装参照
  - execution/
    - execution_engine.py    — ExecutionEngine（セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py      — ブローカークライアント生成（Mock を含む）
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py            — ニュースセンチメントスコア（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py

（注）上記は主要ファイルの一覧であり、実際の細かなサブモジュールはソースを参照してください。

開発メモ / 実装上の注意
-----------------------
- Monitoring（run_monitoring）は MONITOR_POLL_INTERVAL（秒）でポーリング。0以下の値は無効としてデフォルトにフォールバックします。
- Execution は KABUSYS_ENV=paper_trading の場合にデータ・発注を完全に分離（paper_trading DB を使用）する設計です。
- OpenAI を使う機能は API の rate/エラーに対してリトライ等の堅牢化が実装されていますが、API キーの管理と利用制限には注意してください。
- validate_config は PyYAML がない場合 config/*.yaml の内容チェックをスキップします（警告）。

よく使うコマンドまとめ
---------------------
- .env 作成（対話）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視プロセス起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 追加情報
-------------------
- config/*.yaml（system_config.yaml 等）は運用用設定ファイル群として想定されています。validate_config はそれらの存在・パースをチェックします（PyYAML 必要）。
- DB ファイル（data/ 以下）はデフォルトで作業ディレクトリの data/ に配置されます。必要に応じて .env でパスを変更してください。
- ログは logs/ に出力されます（LOG_DIR で変更可）。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はレポジトリのトップレベルファイルを参照してください（本 README には含めていません）。

最後に
------
この README はリポジトリ内のコードを参照して作成しています。詳細な利用方法や内部実装の追加説明はソースのドキュメント文字列（docstring）や各モジュールのコメントを参照してください。質問があればどの部分についてもっと詳しく知りたいか教えてください。