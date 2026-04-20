README
=====

概要
----
KabuSys は日本株向けの自動売買・研究・監視を統合した Python パッケージです。  
ポートフォリオ構築、ポジションサイズ決定、リスク制御、発注エンジン（ExecutionEngine）、監視（Monitoring）や AI を用いたニュースセンチメント評価などのコンポーネントを備えています。  
本リポジトリはライブラリ本体と起動スクリプト、CLI ユーティリティを含み、ローカル開発からペーパートレード、実運用まで想定しています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBroker によるペーパートレードを data/paper_trading.db に記録（本番 DB と分離）
  - ブローカー抽象化、注文管理、リスク管理、reconciler を含む
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム資源、プロセス健全性、注文ログ、リスク指標の定期チェック
  - Kill Switch（条件トリガーで data/kill.flag を書き込み ExecutionEngine を停止）
  - アラート送信（LINE 等を想定する仕組みと組み合わせ可能）
- Portfolio 構築（portfolio パッケージ）
  - 候補選抜、等分配・スコア加重配分、セクター上限適用、ポジションサイズ計算（単元株丸め、集約キャップ）
- Research（research パッケージ）
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
- AI（ai パッケージ）
  - ニュース NLP（OpenAI）でセンチメントスコアを取得し ai_scores に保存
  - マクロセンチメント + ETF MA200 乖離の合成で市場レジーム判定
- ツール / CLI
  - 環境設定ウィザード: config_setup.py（.env 対話生成）
  - 設定検証: validate_config.py（.env や config/*.yaml の存在チェック）
  - ペーパートレード検証レポート: tools/paper_verification_report.py

動作環境（依存）
----------------
最低限必要な外部パッケージ（代表例）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config YAML 検証を使う場合・任意）

（環境に合わせて仮想環境を用意し、pip でインストールしてください。requirements.txt は同梱されていないため必要パッケージを個別にインストールしてください。）

インストール / セットアップ
--------------------------
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証が必要なら）pip install pyyaml
4. .env を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成（.env.example を参照）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたい場合は --strict を付ける

主要な環境変数（抜粋）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（Settings により必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用 / オプション:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必要）
- PAPER_FILL_MODE — ペーパートレードでの約定モード: instant|partial|never|reject（デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0|1)（本番は 0 推奨）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）

起動・使用方法
-------------

共通:
- すべての起動スクリプトはパッケージモジュールとして実行できます:
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution

Monitoring（監視プロセス）:
- 起動:
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能。
- 停止:
  - プロセスを手動で終了（Ctrl+C）するか、プロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了します。
- ログ:
  - logs/monitoring.log に日次ローテーションで出力（setup_logging により設定）

Execution（発注エンジン）:
- 起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 DB に記録され、MockBrokerClient が使用されます。
- 停止:
  - data/stop_requested.flag を作成すると起動済み実行スレッドに停止を指示します。
  - Kill Switch により data/kill.flag が書き込まれると ExecutionEngine 側で停止がトリガーされます（KillSwitch の挙動は監視ルールによる）。
- PID ファイル:
  - data/execution.pid（デフォルト）に PID が書かれます。

設定ウィザード / 検証:
- .env 生成:
  - python -m kabusys.config_setup
- 検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

Paper Trading 検証レポート:
- 実行:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI / レジーム判定 / ニューススコア:
- OpenAI API を使用するコマンドや関数は OPENAI_API_KEY が必要です（なければ例外）。
- ai モジュールの関数は duckdb 接続と target_date を受け取り、DB に書き込み / 更新します。

停止フラグ / Kill Switch
--------------------
- data/stop_requested.flag:
  - run_monitoring.py / run_execution.py はこのファイルの存在を監視し、検出時に安全にシャットダウンします（手動で停止指示する用途）。
- data/kill.flag:
  - Monitoring の評価により KillSwitch が発動すると ExecutionEngine 停止目的でこのファイルが書き込まれます。
  - KillSwitch.clear() で削除できます。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされます（本番では推奨されません）。

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されています。
- デフォルトは stdout 出力 + 日次ローテーションされたログファイル（logs/<app_name>.log、30日保持）。

データベース / マイグレーション
----------------------------
- monitoring のテーブルは run_* スクリプト内で init_monitoring_db() を呼ぶことで自動作成されます（冪等）。
- monitoring_db.init_monitoring_db() は既存スキーマに対する簡単なマイグレーション（カラム追加など）も行います。
- DuckDB（分析用）ファイルは DUCKDB_PATH に保存されます。prices_daily / raw_news / raw_financials 等のテーブルを想定しています（実データの準備が必要）。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（AI + MA200 合成）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        # （コードベースに含まれている想定のモジュール）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        # （アラート統合用の想定モジュール）
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - data/                    — 実行時生成: DB / flag / pid など（プロジェクトルート）

開発メモ
--------
- 単体テストや CI で自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと config の .env 自動読み込みを無効化できます。
- OpenAI 関連は API レート制限やネットワークエラーに対してリトライロジックを実装していますが、テスト時は _call_openai_api を patch して API 呼び出しをモックしてください。
- process_priority.set_process_priority はプラットフォーム依存の挙動があるため権限不足で警告が出ることがあります（無害）。CI 等では無効化しておくとよいです。

以上。運用・開発で追加の使い方や例が必要であれば、どの部分（Execution の起動例、AI スコアの手動実行、DuckDB のサンプルクエリ等）を詳しく記載するか教えてください。