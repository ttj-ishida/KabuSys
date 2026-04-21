KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
主要コンポーネントは以下のとおりです。

- ExecutionEngine: 注文の送信・リスク管理・約定処理を行う実行エンジン
- Monitoring: システム稼働、注文ログ、リスク状況を定期監視してアラート/Kill Switch を発動
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算などのポートフォリオ構築ロジック
- Research: DuckDB 上で動作するファクター計算・特徴量解析モジュール
- AI: ニュース NLP によるセンチメントスコアリング、レジーム判定（OpenAI を利用）
- Tools: 設定ウィザード、設定検証、ペーパートレード検証レポート等の CLI ツール

主な設計方針:
- 本番 DB とペーパー取引 DB を分離（KABUSYS_ENV=paper_trading 時は paper DB を使用）
- 外部 API 呼び出し（OpenAI 等）は環境変数でキーを指定
- フェイルセーフ（API エラーや DB 異常が起きても部分的に継続）を意識した実装

機能一覧
--------
- Execution
  - 実注文（kabuステーション）とモックブローカー（ペーパートレード）の切り替え
  - リスク管理（最大ポジション比率・利用率・ドローダウン等）
  - 注文ログ・約定ログの永続化（SQLite）
- Monitoring
  - CPU / メモリ / ディスク使用率監視
  - Execution プロセス死活監視、データ鮮度チェック
  - リスク監視（ドローダウン検出、ポジション上限監視）
  - Kill Switch（条件成立時に data/kill.flag を書き込んで Execution を停止）
- Portfolio
  - 候補選定（スコア・ランク順）、等重・スコア重みの計算
  - ポジションサイズ計算（リスクベース、等配分）
  - セクターキャップ、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン / IC（スピアマン）計算、統計サマリー
- AI
  - ニュース記事の銘柄別センチメントスコアリング（OpenAI）
  - 市場レジーム判定（ETF MA + マクロセンチメントの合成）
- Tools
  - 対話式 .env 生成（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化してください（venv / pyenv / conda 等）。

2. 依存パッケージ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証を有効にしたい場合）
   - 例:
     pip install duckdb psutil openai pyyaml

3. リポジトリルートに移動し、必要なディレクトリを作成
   - data/ （SQLite や PID / flag を置く）
   - logs/ （ログファイル）
   例:
     mkdir -p data logs

4. 環境変数の初期設定（.env）
   - 対話式ウィザードで .env を作成:
     python -m kabusys.config_setup
   - もしくは .env を手動作成。必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（デフォルト / 説明）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（KABUSYS_ENV=paper_trading 用）
     - LOG_LEVEL: INFO（デフォルト）
     - LOG_DIR: logs/
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - KILL_FLAG_CLEAR_ON_START: 0 | 1（本番では 0 推奨）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH: PID ファイル・kill.flag のパス（デフォルト data/…）

5. 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------
起動スクリプト（モジュール実行）
- ExecutionEngine を起動（本番またはペーパーの設定に依存）
  python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録されます。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動を中止します。
  - エンジンは data/execution.pid（デフォルト）に PID を書きます。

- Monitoring を起動（常駐監視）
  python -m kabusys.run_monitoring

  環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  監視は Settings.sqlite_path（本番 DB）を常に使用します（環境に依らず）。

停止 / Kill Switch
- 手動で ExecutionEngine を停止させたい場合は kill.flag（デフォルト data/kill.flag）を作成します。
  このファイルは KillSwitch によって書き込まれることがあり、ExecutionEngine は起動時にオプションでクリアする設定があります。
- run_monitoring/run_execution ループを即座に停止させたいテスト用途のフラグ:
  data/stop_requested.flag を作成するとループを抜けて終了します。

ツール
- 環境設定ウィザード:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI / Research の利用例
- OpenAI を使う機能（ニュース NLP / レジーム判定）を実行するには OPENAI_API_KEY を設定してください。
- モジュール関数をプログラムから呼ぶことができます（DuckDB 接続を渡す等）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）と target_date（日付）を受け取ります。

ログ
- ログはデフォルトで stdout と logs/<app_name>.log に出力されます（TimedRotatingFileHandler 日次ローテーション、30 日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging から行われ、LOG_DIR / LOG_LEVEL で調整できます。

注意点 / 運用メモ
- 設定ファイル (.env) は絶対にバージョン管理にコミットしないでください。
- KABUSYS_ENV=live の場合は特に注意して設定を確認してください（validate_config で警告が出ます）。
- Monitoring は monitoring DB（Settings.sqlite_path）を使用します。ペーパートレード時も monitoring 用 DB は本番 DB（デフォルト）を参照する点に注意してください。
- run_execution は paper_trading 時に paper_sqlite_path を使用するため、本番 DB とデータが混ざりません。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数 / 設定読み込みと Settings クラス
- config_setup.py            — 対話式 .env ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring 起動スクリプト
- data/                      — データパイプライン / DB 周り（DuckDB 関連） ※別ディレクトリに配置されることを想定
- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- monitoring/
  - monitoring_db.py         — SQLite 永続化層
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（注）上記は主要モジュールの抜粋です。詳細はソースコードを参照してください。

依存関係（例）
--------------
必要に応じてプロジェクトに合わせて調整してください。最低限想定されるパッケージ:
- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証を有効にする場合）

ライセンス / バージョン
-----------------------
パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース参照）。

お問い合わせ / 開発メモ
------------------------
- 開発中は KILL_FLAG_CLEAR_ON_START=1 を使うと起動時に kill.flag を自動クリアできます（本番では 0 を推奨）。
- モジュール単位でのユニットテスト、mock による外部 API の差し替えを想定しています（例: OpenAI 呼び出しはテスト時にパッチ可能）。

以上。プロジェクトの詳細や個別モジュールの使い方が必要であれば、そのモジュール名を指定してドキュメントを追加します。