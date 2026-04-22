KabuSys — 自動売買システム（README）
=================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。  
主要な機能群は以下を含みます: 注文実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター/リサーチ、ニュース NLP（OpenAI を利用）など。  
設計方針としては「テスト可能でフェイルセーフ」「本番／ペーパートレードの分離」「DuckDB を用いた分析」「SQLite を用いた監視ログ永続化」を重視しています。

主な機能
--------
- 実行エンジン（run_execution.py）
  - 本番 / ペーパートレードを切替可能（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録）
  - リスク管理、オーダー管理、再整合（reconciler）等を備える
- 監視（run_monitoring.py、monitoring/*）
  - システム健全性／データ鮮度／注文ログ／リスク（ドローダウン・保有数）等を定期チェック
  - kill.flag による安全停止（KillSwitch）
  - 監視結果は SQLite（デフォルト: data/monitoring.db）へ永続化
- ポートフォリオ構築（portfolio/*）
  - 候補選定、重み計算、セクター制限、ポジションサイズ計算（単元丸め対応）
- リサーチ（research/*）
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB ベース）
  - 将来リターン、IC 計算、特徴量サマリ等
- AI（ai/*）
  - ニュースを OpenAI でスコアリングして ai_scores テーブルへ格納
  - 市場レジーム判定（regime_detector）
- ツール（tools/*）
  - paper_trading の検証レポート生成スクリプト（paper_verification_report.py）
- 設定支援 / 検証 CLI
  - config_setup.py: .env を対話式で生成・更新
  - validate_config.py: .env と config/*.yaml の事前検証

前提（推奨）
------------
- Python 3.10+
  - いくつかの型注釈（|）とモダン構文を利用しているため
- 推奨 Python パッケージ（例）
  - duckdb, psutil, openai, PyYAML（YAML 検証を行う場合）
  - インストール例:
    - pip install duckdb psutil openai PyYAML

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv && source .venv/bin/activate
2. 必要パッケージをインストール
   - 例: pip install duckdb psutil openai PyYAML
   - （実際は requirements.txt を用意していれば pip install -r requirements.txt）
3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 重要な環境変数（最低限設定が必要なもの）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR など
   - 自動ロードの挙動:
     - 起動時にプロジェクトルートの .env と .env.local を自動読み込みします（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
4. 設定検証（任意／推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit(1)）

使い方（主要コマンド）
---------------------
- 実行エンジン（Execution）
  - 本番／ペーパーに応じて設定された DB を使用して起動します：
    - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH を使い、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - PID ファイル: data/execution.pid（設定により変更可）
- 監視プロセス（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は KABUSYS_ENV にかかわらず production sqlite_path（settings.sqlite_path）を使用します（設計上の仕様）
  - 停止方法:
    - data/stop_requested.flag を作成するとループが検知して終了します
- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または PAPER_TRADING_SQLITE_PATH 環境変数で指定
- AI / レジーム判定等（ライブラリ利用）
  - ai モジュールの関数はプログラムから呼び出します（例: kabusys.ai.score_news）
  - OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で渡す

ログ・データ・フラグ
-------------------
- ログ:
  - デフォルト出力先: logs/<app_name>.log（TimedRotatingFileHandler で日次ローテーション、30 日保持）
  - コンソール出力は stdout（stderr ではない）
- データ / 制御ファイル:
  - data/monitoring.db（SQLite、監視ログ、デフォルト）
  - data/paper_trading.db（ペーパートレード用 SQLite）
  - data/kabusys.duckdb（分析用 DuckDB）
  - data/execution.pid（ExecutionEngine PID）
  - data/kill.flag（KillSwitch による安全停止フラグ）
  - data/stop_requested.flag（run_* スクリプトの自己停止フラグ）

設定の注意点
-------------
- KABUSYS_ENV: development / paper_trading / live のいずれか。live は本番扱いのため注意深く設定してください（validate_config が警告を出します）。
- PAPER_FILL_MODE（ペーパートレード時の約定挙動）:
  - 有効値: instant | partial | never | reject
- KILL_FLAG_CLEAR_ON_START:
  - 1 にすると起動時に kill.flag を自動クリアします（本番では 0 を推奨）
- MONITOR_POLL_INTERVAL は正の整数。0 以下や不正値はデフォルトの 60 秒にフォールバックされます。

ディレクトリ構成（主なファイルと役割）
------------------------------------
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - execution/ — 注文実行関連（BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler, OrderRepository 等）
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログの永続化層
    - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py 等
  - portfolio/ — 候補選定、重み付け、ポジション計算、リスク調整
  - research/ — ファクター計算、特徴量探索（DuckDB ベース）
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリング
    - regime_detector.py — マクロ + MA200 でレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ（stream + file rotation）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

トラブルシューティング（よくある問題）
---------------------------------------
- ログファイルが作成されない:
  - permissions（logs ディレクトリ作成に失敗）や LOG_DIR 設定を確認。setup_logging は作成に失敗した場合にコンソールのみで継続します。
- OpenAI API 呼び出しが失敗する:
  - OPENAI_API_KEY を設定しているかを確認。API の一時エラーは内部でリトライしますが、キー未設定だと例外になる箇所があります。
- 設定検証でエラー:
  - .env.example を参考に必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。

貢献 / 追加事項
----------------
- DuckDB のテーブルスキーマ（prices_daily / raw_financials / raw_news 等）に依存する実装が多く含まれます。データパイプラインで期待されるスキーマを満たすことが前提です。
- 本 README はコードベースの主要設計と運用手順を示したもので、詳細仕様（Engine の内部動作・戦略 PDF 等）は別ドキュメント（PortfolioConstruction.md 等）を参照してください。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"

以上。必要であればインストール手順の具体的な requirements.txt の例や、よく使う環境変数の雛形（.env.example）を作成して README に追記しますか？