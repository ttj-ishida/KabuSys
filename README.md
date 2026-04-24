KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ／実行スクリプト群です。  
主要機能はシグナル生成 → ポートフォリオ構築 → ポジションサイズ算出 → 発注実行（本番／ペーパートレード）に加え、監視・リスク判定・AIベースのニュースセンチメント解析やリサーチ用ファクター計算を備えます。

主な特徴
--------
- ExecutionEngine：注文管理・リスク管理・ブローカー抽象化（本番／ペーパートレード分離）
- Monitoring：プロセス・システムリソース・データ鮮度・取引ログの監視・アラート連携、Kill Switch
- Portfolio construction：候補選定、重み計算、ポジションサイズ算定、セクター上限適用などの純粋関数群
- Research：ファクター（モメンタム／ボラティリティ／バリュー）計算、前方リターン・IC 検証ユーティリティ
- AI モジュール：ニュースを LLM でスコアリング（OpenAI）、市場レジーム判定
- CLI ユーティリティ：
  - .env の対話式ウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - Paper Trading 検証レポート作成スクリプト

必須依存（代表）
----------------
最低限以下の Python パッケージが必要です（バージョンは適宜調整してください）。
- Python 3.10+
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- PyYAML（validate_config の YAML 検証を有効にする場合）

インストール例（venv を推奨）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)
- 必要パッケージをインストール
  - pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリルートへ移動（pyproject.toml や .git がルート判定に使われます）。
2. .env を作成（推奨：対話式ウィザードを利用）
   - python -m kabusys.config_setup
     - 対話形式で J-Quants トークンや kabuAPI パスワード、DB パス等を設定できます。
     - .env は絶対に Git にコミットしないでください。
3. 設定を検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。
4. データディレクトリの確認
   - デフォルトの DB / PID / フラグファイル は project_root/data 以下に作成されます。必要に応じて .env で上書きしてください。

重要な環境変数（主なもの）
--------------------------
（.env に設定可能）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE — ペーパートレードでの約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用）

使い方（主要スクリプト）
-----------------------

.env の作成／更新（対話式）
- python -m kabusys.config_setup

設定検証
- python -m kabusys.validate_config
- --strict を付けると警告で exit(1) になります

ExecutionEngine（発注エンジン）起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db 等）に記録します。実際の発注は行いません。
  - 起動時に project_root/data/execution.pid （PIDファイル）や停止フラグを利用します。
  - 停止は project_root/data/stop_requested.flag を作成すると検知して停止します。

Monitoring（監視ループ）起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL で間隔を上書き可能（秒）
  - 監視は Settings.sqlite_path（デフォルト monitoring.db）を使用します（環境にかかわらず本番パスを使う設計）
  - 停止は project_root/data/stop_requested.flag を作成して行います

Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを指定する場合: --db PATH、または環境変数 PAPER_TRADING_SQLITE_PATH を使用
  - 稼働率・成功率・レイテンシ等を集計して PASS/FAIL 判定を出力します

AI（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY または関数引数経由）
- ニュースセンチメント: kabusys.ai.score_news（内部で raw_news / news_symbols / ai_scores を使用）
- レジーム判定: kabusys.ai.regime_detector.score_regime
- 大きいデータや API リクエストの失敗に備えたバックオフ・フェイルセーフ設計あり

停止・Kill Switch の仕組み
-------------------------
- 停止要求（外部による Engine 停止）:
  - project_root/data/stop_requested.flag — run_execution / run_monitoring が監視しており存在時に停止します
- Kill Switch（監視から ExecutionEngine に停止指示）:
  - KillSwitch が条件を満たした場合に project_root/data/kill.flag を作成します。ExecutionEngine 側は kill.flag を検知して適切に停止する挙動（config によりクリア設定あり）を想定しています。

ログ
----
- ログは標準出力（StreamHandler）および日次ローテーションで logs/<app_name>.log に出力されます（デフォルト logs/、30 日分保持）。
- setup_logging() を全スクリプトから呼ぶ設計です。LOG_DIR 環境変数で変更可。

ディレクトリ構成（主要ファイル）
------------------------------
以下はパッケージルート src/kabusys 以下の主要ファイル／モジュールです（抜粋）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数読み込み・Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py           — ログセットアップ
    - process_priority.py        — プロセス優先度・CPU affinity
  - execution/                    — 発注関連（BrokerFactory, ExecutionEngine, OrderManager, RiskManager など）
  - monitoring/
    - monitoring_db.py           — SQLite テーブル初期化・永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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

補足・運用上の注意
-----------------
- デフォルトで使用する SQLite / DuckDB のファイルパスは .env で変更可能です。運用時はパスや権限を適切に管理してください。
- KABUSYS_ENV が live の場合は本番動作になります。validate_config は本番時の注意喚起を出します。LINE 通知設定等を忘れず確認してください。
- run_execution/run_monitoring はプロセス優先度を高く設定しようとします（プラットフォーム依存で失敗する場合は警告が出ます）。
- OpenAI API を使う処理はレート制限やエラーに対し再試行・フォールバックのロジックが組まれていますが、API キーやコストには注意してください。
- .env を直接編集する場合は既存の OS 環境変数との競合に注意してください。config.py は .env の自動読み込みを行います（無効化可：KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

開発者向け
----------
- テストや CI 環境では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動 .env 読み込みを無効化できます。
- モジュールはできる限り純粋関数／副作用の少ない設計を心がけています（特に portfolio/* や research/*）。
- DuckDB / SQLite を使ったクエリやテーブル操作はユニットテストでモック可能です。

ライセンス・バージョン
---------------------
- __version__ = "0.1.0"（パッケージ初期バージョン）
- ライセンス情報が別途ある場合はプロジェクトルートの LICENSE を参照してください。

最後に
------
まずは対話式ウィザードで .env を作成し、validate_config でチェック→ローカルで paper_trading モードで run_execution/run_monitoring を実行して挙動を確認する流れを推奨します。必要があれば README に追加したい項目（例: systemd ユニットファイル例、Docker 化手順、より詳細な設定項目一覧など）を指定してください。