README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤を想定した Python パッケージです。
主な機能として、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ（ファクター計算・特徴量解析）、
Paper Trading 検証ツール、LLM を使ったニュースセンチメント評価などを含みます。

設計のポイント
- 実稼働／ペーパートレードを環境変数 KABUSYS_ENV により切り替え（development / paper_trading / live）。
- SQLite（監視・トレードログ）と DuckDB（分析・リサーチ）を組み合わせた設計。
- OpenAI（gpt-4o-mini）を利用する NLP モジュールは API 失敗時に安全にフォールバックする実装。
- ログは統一的に設定（stdout と日次ローテーションファイル出力）。
- .env を対話式ウィザードで作成・検証する仕組みあり。

主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に記録
  - リスク管理、オーダー管理、調整（reconciler）を組み合わせて注文を発行
- 監視ループ（run_monitoring.py）
  - CPU/メモリ/ディスクやデータ鮮度、Execution プロセスの状態をポーリングしてログに記録
  - Kill Switch（条件を満たすと data/kill.flag を書き込む）と連携
- 監視永続化レイヤ（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブル管理
- リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- ポートフォリオ構築（portfolio）
  - 候補選定、等比重／スコア加重、ポジションサイズ計算、セクターキャップ適用
- AI モジュール（ai）
  - ニュースのセンチメント評価（OpenAI を利用）と市場レジーム判定
- 運用補助ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

前提・依存
- Python 3.10+
- 必要な Python パッケージ（一例）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証に使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime 等

セットアップ手順
--------------
1. リポジトリをチェックアウト
   - この README はパッケージの src/kabusys 配下を前提とします。

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （検証用）pip install pyyaml

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 手動で作成する場合はプロジェクトルートに .env を置く（.env.example を参照）
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合:
     - python -m kabusys.validate_config --strict

使い方
------
1. 実行エンジンを起動
   - デフォルト（KABUSYS_ENV の値を参照）:
     - python -m kabusys.run_execution
   - paper_trading モードで起動する場合:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - この場合、データは settings.paper_sqlite_path（デフォルト data/paper_trading.db）に書き込まれます。

   動作のポイント:
   - 実行中は data/execution.pid に PID が書き込まれます。
   - 停止はプロセス内で stop flag を検出すると安全に停止します。外部から停止するにはプロジェクトルートの data/stop_requested.flag を作成してください（両起動スクリプトともこれを監視します）。

2. 監視ループを起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔を変更する場合:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は環境に依らず production 用の sqlite_path を使用します（Settings.sqlite_path）。

3. Kill Switch / 強制停止
   - Kill Switch は条件を満たすと data/kill.flag を作成します（ExecutionEngine はこれを検知して停止する想定）。
   - 手動で停止ループ（両スクリプト）を要求するには data/stop_requested.flag を作成します。起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていれば kill.flag を自動で消去しますが、本番では 0 を推奨します。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスを直接指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. プログラム的に各モジュールを利用する
   - 例: リサーチ（DuckDB 接続が必要）
     - import duckdb
     - from kabusys.research import calc_momentum
     - conn = duckdb.connect("data/kabusys.duckdb")
     - results = calc_momentum(conn, date(2026, 4, 10))
   - 例: ポートフォリオ関数
     - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging により設定されます。
- デフォルトで stdout に出力し、日次ローテーションで logs/<app_name>.log に保存（30日分保持）。
- ログレベルは環境変数 LOG_LEVEL または引数で制御可能。

重要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: execution 環境。development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0|1）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・設定管理（Settings クラス）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ/モジュール
- ai/
  - news_nlp.py            — ニュースセンチメント評価（OpenAI 呼び出し）
  - regime_detector.py     — 市場レジーム判定（MA + macro sentiment 合成）
- monitoring/
  - monitoring_db.py       — SQLite スキーマ / DB 操作ラッパー
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py       — （注文系監視、コード内参照）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag の生成/管理
  - monitoring_engine.py   — 各モニタを束ねるエンジン
  - alert_manager.py       — （アラート通知管理）
- execution/
  - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
  - order_manager.py       — 注文管理
  - order_repository.py    — 発注履歴保存
  - reconciler.py          — ブローカー整合性処理
  - broker_factory.py      — BrokerClientFactory（実/モックの切り替え）
  - risk_manager.py        — 発注時リスクチェック
- portfolio/
  - portfolio_builder.py   — 候補選定・重み算出
  - position_sizing.py     — 株数決定ロジック
  - risk_adjustment.py     — セクター制限・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン・IC・統計
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - その他ユーティリティ

運用上の注意
------------
- 本番運用（KABUSYS_ENV=live）では必須環境変数の確認・LINE 通知設定などを慎重に行ってください。validate_config は本番向けのガードチェックを含みます。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険なので、本番では 0 を推奨します。
- monitoring は Settings.sqlite_path を使用するため、監視ログが本番 DB と分離されているか設計に注意してください（run_execution は paper_trading 時に専用 DB を使います）。
- OpenAI API を利用するモジュールは API 失敗時の挙動をフェイルセーフに設計していますが、API 利用料金やレート制限に注意してください。

貢献・拡張案
-------------
- stocks マスタに単元（lot_size）を持たせ、銘柄別単元対応する拡張
- スリッページ・手数料モデルをプラグイン化して position sizing に反映
- monitoring のアラート送信先に PagerDuty / Slack などを追加
- テストカバレッジ拡充（OpenAI 呼び出し部分はモック化しやすいよう分離済み）

ライセンス
---------
（ここにライセンスを記載してください）

以上。README に不足があれば、利用シナリオ（開発 vs 本番）や特定のファイルの詳細説明を追加します。