README — KabuSys（日本株自動売買システム）
====================================

概要
----
KabuSys は日本株の自動売買・リサーチ・検証を支援するモジュール群です。本リポジトリは以下の主要機能を含む Python パッケージ構成になっています。

- 実行エンジン（ExecutionEngine）および監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算
- ファクター計算・特徴量探索（Research）
- ニュース NLP によるセンチメントスコアリング / レジーム判定（AI）
- Paper Trading 用検証レポート生成ツール
- .env 対話ウィザード・設定検証ツール
- ロギング・プロセス優先度ユーティリティ等の共通ユーティリティ

特徴一覧
---------
- 起動スクリプト:
  - run_execution: ExecutionEngine の起動（paper_trading 環境では MockBroker を使用し、本番 DB と分離）
  - run_monitoring: SystemMonitor のポーリングループ実行（MONITOR_POLL_INTERVAL で間隔調整可能）
- 監視:
  - SystemMonitor: CPU/メモリ/ディスク、プロセス死活、データ鮮度を監視
  - RiskMonitor / KillSwitch: ドローダウン・ポジション上限を検出し kill.flag を書き込む
  - MonitoringDB: SQLite に監視ログ／トレードログ／ダッシュボードを永続化
  - MonitoringEngine: 各 Monitor を束ねてポーリング、アラート送出
- Execution 側（モジュール群）:
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine（起動スクリプトあり）
- ポートフォリオ:
  - 候補選定、等重・スコア加重・リスクベース配分、セクター制限、レジーム乗数
- Research:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた SQL ベース）
  - 将来リターン計算、IC（情報係数）・統計サマリ
- AI:
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメントスコア化（ai_scores への格納）
  - regime_detector: ETF（1321）ma200 乖離とマクロニュースを合成して市場レジーム判定
- ツール:
  - config_setup: .env の対話式ウィザード（雛形作成）
  - validate_config: .env / config/*.yaml の事前検証
  - paper_verification_report: Paper Trading の検証レポート出力

必須・推奨依存パッケージ
------------------------
（実行環境に応じてインストールしてください）
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（config YAML の内容検証を行う場合に任意で必要）

例:
pip install duckdb psutil openai PyYAML

セットアップ手順
----------------

1. リポジトリをクローン / 配置
   - この README の想定ルートはパッケージが src/kabusys にある構成です。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要ライブラリをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は上記依存を個別にインストール

4. .env 作成（対話式）
   - python -m kabusys.config_setup
   - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD は必須
   - KABUSYS_ENV の値: development / paper_trading / live
   - .env は絶対に Git にコミットしないでください

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

主要環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（"DEBUG"/"INFO"/"WARNING"/"ERROR"）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の約定モード: instant/partial/never/reject）

使い方（実行例）
----------------

- 環境変数の自動ロードについて
  - パッケージ起動時はプロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local を自動ロードします。
  - 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - paper_trading 環境では MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録されます
  - 停止方法: data/stop_requested.flag を作成すると実行スレッドが停止します

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path（SQLITE_PATH）を使用してログを書きます
  - 停止フラグ: data/stop_requested.flag

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI / レジーム判定（プログラム API）
  - news_nlp.score_news(duckdb_conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
  - Api キーは OPENAI_API_KEY 環境変数か引数で指定

ログ
----
- デフォルトのログディレクトリ: logs/
- 起動スクリプトは app_name に応じて logs/<app_name>.log を日次ローテート（30日分保存）
- ログ出力レベルは LOG_LEVEL で制御

ファイルフラグ / 制御ファイル
----------------------------
- data/stop_requested.flag — run_execution / run_monitoring の停止トリガー（存在を確認して安全終了）
- data/kill.flag — KillSwitch が書き込む ExecutionEngine 停止フラグ（存在する場合は起動時に明示的に扱う）
- data/execution.pid — ExecutionEngine の PID ファイル（起動時に扱われる）

ライブラリ API（主要）
---------------------
- kabusys.config.Settings — 環境設定ラッパー（プロパティで各設定を参照）
- kabusys.portfolio.* — 候補選定 / 重み計算 / ポジションサイズ計算 / セクター制限 等の純粋関数
- kabusys.research.* — DuckDB を受け取りファクター・将来リターン・IC 等を計算
- kabusys.ai.news_nlp.score_news — news を LLM でスコアリングして ai_scores に保存
- kabusys.ai.regime_detector.score_regime — レジーム判定と market_regime テーブルへの書込み
- kabusys.monitoring.MonitoringDB — SQLite への読み書きユーティリティ（system_status / trade_logs / risk_logs / dashboard / positions）

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env 自動ロード / Settings
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリングスクリプト

subpackages:
- /utils/
  - logging_setup.py        — 共通ロギング設定
  - process_priority.py     — プロセス優先度 / CPU affinity
- /monitoring/
  - monitoring_db.py        — SQLite 永続化層
  - system_monitor.py       — システム状態監視
  - risk_monitor.py         — ドローダウン / ポジション数監視
  - kill_switch.py          — kill.flag 管理
  - monitoring_engine.py    — 各 Monitor のオーケストレーション
  - alert_manager.py*       — （アラート管理、参照あり）
  - trade_monitor.py*       — （トレード監視、参照あり）
- /execution/
  - execution_engine.py*    — ExecutionEngine（参照されるが本 README では省略）
  - order_manager.py*       — 注文管理等
  - broker_factory.py*      — ブローカークライアント生成
  - ...                     — その他 Execution 関連
- /portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- /research/
  - factor_research.py
  - feature_exploration.py
- /ai/
  - news_nlp.py
  - regime_detector.py
- /tools/
  - paper_verification_report.py

（* のファイルは本 README のコード抜粋に一部参照があるが、詳細はソースを参照してください）

運用上の注意
-------------
- .env に API トークン等のシークレットを保存する際は Git 管理から除外してください。
- KABUSYS_ENV=live の場合は特に注意して設定をチェックしてください（validate_config の警告機能を活用）。
- Kill Switch（KILL_FLAG）や stop_requested.flag の扱いは慎重に行ってください。KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

トラブルシュート
-----------------
- ログが出力されない / ファイルハンドラが作れない場合は権限やディレクトリ作成エラーを確認（logs/ のパーミッション）。
- DuckDB / SQLite のパスは .env で調整。validate_config で親ディレクトリの存在確認を行えます。
- OpenAI 呼び出しで 429 / ネットワーク断 / 5xx が発生した場合は内部でリトライ実装がありますが、API キーとレート制限を確認してください。

以上。開発者向けのモジュール設計やさらに詳しい API 使用法は各モジュールの docstring を参照してください。README に不足している点や、特定機能の使用例（サンプルコード）を希望する場合はお知らせください。