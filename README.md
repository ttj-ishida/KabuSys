README — KabuSys (日本株自動売買システム)
========================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下を含む主要コンポーネントを持ちます。

- ExecutionEngine：発注・リスク管理・注文管理の実行ロジック
- Monitoring：システム・注文・リスク監視、Kill Switch による安全停止
- Data / Research：DuckDB を用いたファクター計算・特徴量解析
- Portfolio：候補選定、重み付け、ポジションサイズ計算、セクター制限
- AI：ニュース NLP（OpenAI）を用いたセンチメント算出・レジーム判定
- ユーティリティ：環境設定ウィザード、設定検証、paper trading 検証レポート など

主な設計方針：
- 本番・ペーパートレードを環境変数 KABUSYS_ENV で切り替え
- DB は DuckDB（分析）と SQLite（監視 / ペーパートレード）を使用
- AI 機能は OpenAI API（OPENAI_API_KEY）が必要（任意）

機能一覧
--------
- 環境設定ウィザード（.env 生成 / 更新）：kabusys.config_setup
- 起動前設定検証 CLI：kabusys.validate_config（--strict オプションあり）
- Execution 起動スクリプト：kabusys.run_execution（本番 / paper_trading 切替）
- Monitoring ポーリングループ：kabusys.run_monitoring（MONITOR_POLL_INTERVAL で間隔変更可）
- モニタリング機能：
  - SystemMonitor：CPU/メモリ/ディスク監視、データ鮮度チェック、PID ステータス
  - TradeMonitor：滞留注文、約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み Execution を安全停止
  - AlertManager（実装箇所あり）経由で通知（LINE 等は設定に依存）
- Portfolio 構築：候補選定、等金額/スコア加重、リスクベースの発注株数計算、セクター制限
- Research：モメンタム・ボラティリティ・バリュー計算、将来リターン・IC 計算、統計要約
- AI：
  - news_nlp: ニュースを銘柄ごとに集約して LLM でセンチメントを算出し ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して日次レジーム判定
- ツール：
  - paper_verification_report：ペーパートレードの稼働率・注文成功率・レイテンシ等を集計してレポート出力

セットアップ手順
----------------
前提：Python 3.10+（型注釈からの想定）。プロジェクトルートに移動して作業します。

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージインストール
   - 必須（例）:
     - duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそれを使用してください）

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env を Git にコミットしないこと

4. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

5. DB 初期化
   - run_execution / run_monitoring 起動時に必要テーブルは自動作成されます（monitoring 用 SQLite は init_monitoring_db で準備されます）
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

使い方
------
起動・操作の主な例を示します。

1. ExecutionEngine を起動
   - デフォルト（環境変数 KABUSYS_ENV に依存）:
     - python -m kabusys.run_execution
   - ペーパートレードで起動する場合:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
     - ペーパー環境では MockBrokerClient を使い data/paper_trading.db にログを残します。

   注意:
   - 実行時は data/execution.pid（デフォルト）が作成されます。
   - 停止は run_execution が監視する stop_requested.flag（data/stop_requested.flag）を作成するか、KillSwitch により data/kill.flag が書き込まれると実行エンジンが停止します。

2. Monitoring を起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
   - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用して監視ログを書きます

3. Kill Switch / 停止制御
   - KillSwitch は条件（ドローダウン超過やポジション上限超過）で data/kill.flag を書き込みます
   - 手動で停止フラグを立てる（Execution 側が検知して安全停止する）:
     - touch data/stop_requested.flag
     - （停止後や起動前に kill.flag を削除したい場合）: rm data/kill.flag

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit code 1）として扱います

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - 環境変数 PAPER_TRADING_SQLITE_PATH でデフォルト DB を上書きできます

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live）（default: development）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite, default: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の注文約定挙動）
  - valid: instant | partial | never | reject（default: instant）
- OPENAI_API_KEY（AI 機能を使う場合、news_nlp / regime_detector で参照）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、default: 60）
- PID_FILE_PATH, KILL_FLAG_PATH など（Settings クラス参照）

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定読み込みロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリング起動スクリプト
  - utils/
    - process_priority.py   — psutil を使った優先度 / CPU affinity 設定
  - execution/              — 発注関連（OrderManager, Engine 等）※詳細は該当モジュール参照
  - monitoring/
    - monitoring_db.py      — SQLite テーブル初期化・読み書き
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      — アラート送信管理（実装に依存）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュースを LLM でセンチメント化
    - regime_detector.py    — マーケットレジーム判定（ma200 + macro sentiment）
  - tools/
    - paper_verification_report.py

実運用上の注意
--------------
- .env やシークレット（API トークン）は絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live を設定する前に validate_config を実行し、LINE などの通知設定や Kill Switch の挙動を確認してください。
- Run スクリプトは stop_requested.flag（data/stop_requested.flag）や kill.flag を用いて協調停止します。運用オペレーションでこれらのファイルの扱いを明確にしてください。
- AI（OpenAI）利用は API コストがかかります。rate limit / retry ロジックは実装済みですが、運用時はキー管理とコスト管理に注意してください。
- psutil によるプロセス優先度設定は権限に依存します。失敗した場合は警告ログが出て処理は継続します。

開発者向け補足
--------------
- 設定自動ロード: プロジェクトルートに .env/.env.local を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- monitoring_db.init_monitoring_db は冪等で実行可能。既存 DB に対する簡易マイグレーション（列追加）も実装されています。
- AI 呼び出し部分の外部依存は抽象化されており、ユニットテスト時は _call_openai_api を patch してテスト可能です。
- DuckDB 接続は各モジュールに渡す形（依存注入）になっているため、テストではインメモリ DB を用いた検証が容易です。

サポート / コントリビューション
-------------------------------
バグ報告や改善提案は Issue でお願いします。大きな設計変更や互換性を壊す改修は事前に Issue で相談してください。

以上。必要であればサンプル .env のテンプレートや運用手順（デプロイ / systemd ユニット例）を追加で作成します。どの情報が欲しいか教えてください。