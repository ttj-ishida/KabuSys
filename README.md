README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を行うためのユーティリティ群です。本コードベースは以下の機能群を含みます。

- 注文発行を担う ExecutionEngine（実運用 / ペーパートレード切替対応）
- システム稼働・注文状況・リスクの定期監視（Monitoring）
- ポートフォリオ構築（選定・重み算出・ポジションサイズ計算）
- 研究用ファクター計算・特徴量解析（duckdb 経由）
- ニュース NLP によるセンチメント評価（OpenAI を利用）
- Paper Trading の検証レポート生成ツール 等

主な機能
--------
- ExecutionEngine（run_execution.py）
  - KABUSYS_ENV により本番 / ペーパートレードを切替
  - paper_trading 時は MockBrokerClient を利用し、専用 SQLite（既定: data/paper_trading.db）へ記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視を実装
- Monitoring（run_monitoring.py, monitoring/*）
  - システムリソース・データ鮮度・注文ログ・リスク監視
  - kill.flag による Execution 停止（Kill Switch）
  - 監視ログは SQLite（既定: data/monitoring.db）へ永続化
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等金額/スコア加重、リスクベースのポジションサイズ算出
  - セクター上限やレジーム乗数の適用ロジック
- 研究（research/*）
  - DuckDB を用いたファクター計算（Momentum/Volatility/Value）
  - 将来リターンや IC（Information Coefficient）算出、統計サマリ
- AI（ai/*）
  - OpenAI を用いたニュースセンチメント評価（news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（regime_detector）
  - 冪等書込みやリトライ等のフェイルセーフ実装
- ユーティリティ
  - .env 対話ウィザード（config_setup.py）
  - 起動前の設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）

動作要件（目安）
----------------
- Python 3.9 以上（型注釈の記法等を使用）
- 推奨（機能利用時に必要）:
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（validate_config の YAML 検証オプション）

セットアップ手順
----------------
1. リポジトリをクローン・チェックアウト
   - 例: git clone <repo_url>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限: duckdb, psutil が必要になる箇所あり
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt がある場合はそれを使用）

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 編集後に設定を検証:
     - python -m kabusys.validate_config
     - 警告を FAIL にしたい場合: python -m kabusys.validate_config --strict

重要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - paper_trading: MockBroker を使い data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）へ記録
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（上書き）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時）
- LOG_LEVEL / LOG_DIR — ログレベル・出力ディレクトリ
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — PID / kill flag 関連設定

使い方（主要スクリプト）
-----------------------
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine（注文エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading として起動すると MockBroker が利用され、別 DB を使用します
- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

停止手順・フラグ
----------------
- run_execution / run_monitoring はプロジェクト直下の data/stop_requested.flag ファイルの存在を監視し、存在すると安全に停止します（run_execution は起動時にもチェック）。
- Kill Switch:
  - Kill 条件を満たした場合、data/kill.flag が書き込まれ、ExecutionEngine を停止するトリガーになります。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリア可能（本番では 0 推奨）。

ロギング
-------
- ログはデフォルトで logs/<app_name>.log（日次ローテーション、30 日保持）に出力されます。
- 環境変数 LOG_DIR で出力先を変更可能。LOG_LEVEL でログレベルを指定します。
- 各起動スクリプトは utils.logging_setup.setup_logging を通して統一的に設定されます。

データベース・スキーマ（監視）
-----------------------------
- 監視用 SQLite（init_monitoring_db）で作成される主なテーブル:
  - system_status, trade_logs, positions, risk_logs, dashboard
- init_monitoring_db は冪等でマイグレーション処理も含むため、起動時に呼び出しておけばスキーマ整合を保ちます。

AI / OpenAI 機能の注意点
-----------------------
- news_nlp, regime_detector は OpenAI API（gpt-4o-mini 想定）を利用します。API キーは OPENAI_API_KEY を設定してください。
- API 呼び出しにはリトライ・バックオフ・レスポンス検証等フェイルセーフを実装していますが、API 利用料が発生します。
- テスト時は内部の API 呼び出しラッパーをモックして単体テスト可能に設計されています。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env ウィザード CLI
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py (存在想定)
- execution/                — Execution に関するモジュール群（Engine, OrderManager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- data/                     — 実行時に data/*.db, pid, flag ファイルが配置される（プロジェクトルートに作成）

開発・デバッグのヒント
---------------------
- validate_config で起動前に設定ミスを検出してください。
- ログは stdout にも出力されるため、systemd / cron / コンテナからの監視が容易です。
- 単体機能（ファクター計算、ポジション算出等）は DuckDB や純粋関数として分離されており、外部依存（Api など）なしでテスト可能です。
- AI 関連は API 呼び出しの抽象化がされているため、ユニットテストではモック可能です。

免責・運用上の注意
-------------------
- live 環境での利用は自己責任で行ってください。本番環境では KABUSYS_ENV=live とし、LINE 等の通知設定や Kill Switch の設定を確認してください。
- .env に機密情報（API キーやパスワード）を保存する場合、絶対に Git 等へコミットしないでください。

必要に応じて README の追記・整備、あるいは requirements.txt / Dockerfile 等の提供を行えます。追加で記載してほしい項目（例: 具体的な config/sample、systemd ユニットの例、デプロイ手順）があれば教えてください。