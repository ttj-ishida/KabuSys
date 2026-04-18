README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチフレームワークです。本リポジトリは次の役割を持つコンポーネント群を含みます。

- ExecutionEngine: 発注・オーダー管理・リスク管理を行う実行エンジン（本番 / ペーパートレード切替対応）
- Monitoring: システム稼働状況・注文状況・リスク監視と Kill Switch（停止フラグ）連携
- Research: DuckDB を用いたファクター計算・特徴量解析ツール
- AI 支援: ニュースセンチメントや市場レジーム判定のための OpenAI（gpt-4o-mini）呼び出しラッパ
- Utilities: ロギングやプロセス優先度設定、設定読み書きウィザード等の補助機能
- Tools: ペーパートレード結果検証レポート生成スクリプト 等

主な機能
--------
- 環境別動作: KABUSYS_ENV により development / paper_trading / live を切替
  - paper_trading: MockBroker を使い、本番 DB と分離した data/paper_trading.db を使用
- ExecutionEngine の起動・停止制御（pid / stop フラグ / kill.flag）
- 監視ループ (SystemMonitor / TradeMonitor / RiskMonitor) とアラート送信（LINE トークン利用可）
- MonitoringDB: SQLite に監視ログ・トレードログ・ポジション・リスクログ・ダッシュボードを永続化
- Portfolio 構築モジュール: 候補選定、重み算出、単元丸めを含むポジションサイズ計算
- Research モジュール: Momentum / Volatility / Value 等のファクター計算、将来リターン・IC 計算
- AI モジュール: ニュースのセンチメントスコアリング、マクロセンチメントによるレジーム判定
- ツール: Paper Trading の検証レポート生成スクリプト（期間指定可能）

セットアップ手順
----------------

前提
- Python 3.9+（ソースは型ヒントに基づき 3.9 以上を想定）
- システムに duckdb, psutil, openai 等の依存パッケージが必要

1. クローン & 仮想環境作成
   - git clone <repo>
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージインストール
   - pip install -r requirements.txt
   （requirements.txt が無い場合は少なくとも以下をインストールしてください）
   - pip install duckdb psutil openai

   注:
   - monitoring の YAML 検証は PyYAML が必要（任意）。
     - pip install PyYAML

3. 初期設定（.env の作成）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - .env の必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV（development / paper_trading / live）
   - 重要: .env はリポジトリにコミットしないでください

4. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションをつけると警告も失敗扱いになります

5. データディレクトリ等
   - デフォルトでは data/ (monitoring/paper_trading DB 等) と logs/ を利用します。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_DIR を設定してください。

使い方
------

起動スクリプト
- 実行部分はモジュールとして提供されています。直接実行するか、サービスとして登録して下さい。

1. ExecutionEngine を起動
   - 本番/ペーパーを .env の KABUSYS_ENV で切替
   - 起動:
     - python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成すると起動中のエンジンが検知して停止します
   - PID ファイル:
     - デフォルト: data/execution.pid（Settings.pid_file_path で変更可能）

2. Monitoring を起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔:
     - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（デフォルト 60 秒）
   - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使ってログを保持します（環境に依らず）

3. 設定ウィザード（.env の対話式作成）
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - 成功すると exit(0)、エラー時は非ゼロ終了コード

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
   - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: monitoring のポーリング秒数（デフォルト 60）

運用上の注意
- KABUSYS_ENV=live の場合は特に .env の内容を慎重に管理してください（LINE/kill フラグ等）
- kill.flag 機能: KillSwitch はリスク基準を満たすと data/kill.flag を書き込み ExecutionEngine に停止を促します
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を使うと自動的に kill.flag を消しますが、本番では 0 を推奨します

ディレクトリ構成
----------------

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト

  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
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
    - news_nlp.py              — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py       — 市場レジーム判定（OpenAI 呼び出し）

  - data/                     — 実行時に使用するデフォルトデータディレクトリ（例: data/*.db, data/kill.flag）
  - logs/                     — ログ出力先（デフォルト）

  - tools/
    - paper_verification_report.py

ユーティリティ・補足
- ロギング設定: kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼んで統一的にログを出力します（Stream と TimedRotatingFileHandler）
- process priority: kabusys.utils.process_priority.set_process_priority で起動時に優先度を high にする処理を含みます
- DuckDB: Research / AI モジュールは DuckDB 接続を受け取り、prices_daily / raw_financials / raw_news 等のテーブルを参照して処理します
- OpenAI: AI モジュールは OpenAI API キーを OPENAI_API_KEY 環境変数、または関数引数で受け取ります。API 呼び出しはリトライ処理・レスポンスバリデーションを内蔵しています

ライセンス・貢献
----------------
- 本リポジトリに含まれるコードのライセンス・貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を確認してください（無ければプロジェクト管理者に問い合わせてください）。

お問い合わせ
------------
実装上の疑問点や動作確認に関する質問はリポジトリの Issues へお願いします。README の改善提案も歓迎します。