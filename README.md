README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のコードベースです。本リポジトリは以下を含みます:
- ExecutionEngine（発注・注文管理・リスク管理） — 実口座 / ペーパートレード対応
- Monitoring（システム稼働監視・注文監視・リスク監視・Kill Switch）
- Portfolio 構築ユーティリティ（候補選定、重み付け、ポジションサイズ算出）
- Research（ファクター計算、特徴量探索、IC 計算 等）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- CLI 補助ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

本 README は開発者向けにプロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

主な機能
--------
- 発注エンジン（ExecutionEngine）
  - 本番（live）とペーパートレード（paper_trading）を環境変数で切替可能
  - Broker クライアントの抽象化（MockBroker をテスト／ペーパートレードで利用）
  - OrderManager / RiskManager / Reconciler による注文管理・監視
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、実行プロセスの有無、データ鮮度をチェック
  - TradeMonitor：滞留注文・約定価格異常を検出
  - RiskMonitor：ドローダウン・ポジション上限を監視しログ／アラート
  - KillSwitch：閾値を超えた場合にフラグファイルを書き ExecutionEngine に停止指示
  - MonitoringEngine：上記をまとめてポーリング実行
- ポートフォリオ構築
  - 候補選定（スコア降順）、等金額・スコア加重配分、リスクベースのポジションサイズ
  - セクター集中排除、レジームに応じた資金乗数
- リサーチ
  - Momentum / Volatility / Value 等ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）
  - ニュース記事から銘柄ごとにセンチメントを算出して ai_scores テーブルへ保存
  - ETF + マクロニュースを組み合わせて市場レジームを判定・保存
  - 再試行や JSON バリデーション等の回復ロジックを備えた実装
- ツール
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト

前提条件 / 依存パッケージ
------------------------
主要依存（抜粋）:
- Python 3.10+
- duckdb
- psutil
- openai
- （任意）PyYAML：config/*.yaml の検証に使用
これらは pyproject.toml / requirements.txt に定義されている想定です。pip または Poetry 等でインストールしてください。

セットアップ手順
---------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. Python 環境を作成・アクティベート（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または適宜 pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - 生成後、必要な環境変数（特に JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD）を確認します。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗（exit code 1）にできます:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトでは data/ 以下に DB やフラグファイルが置かれます。権限とディレクトリ作成を確認してください。
   - もしカスタムパスを使う場合は .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等を設定してください。

使い方
------
起動系
- 実行エンジンを起動（本番/ペーパーは KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 実行前に .env で KABUSYS_ENV=paper_trading や PAPER_TRADING_SQLITE_PATH を設定すると、ペーパートレード専用 DB に記録され、本番 DB と分離されます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH を参照します（未指定時は data/paper_trading.db）。

環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 動作環境:
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DB 関連:
  - DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- AI:
  - OPENAI_API_KEY — OpenAI 呼び出しに使用
- ログ / 制御:
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL
  - KILL_FLAG_CLEAR_ON_START — 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
- Monitoring 固有:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH — Settings で参照されるパス（.env で上書き可）
- Paper モード:
  - PAPER_FILL_MODE — instant | partial | never | reject（ペーパートレードの約定挙動）

プロセス制御 / 停止方法
- Stop フラグ（run_execution / run_monitoring 共通）
  - data/stop_requested.flag を作成すると、監視ループ・エンジン起動中に検知して安全に停止します。
- Kill Switch（自動停止トリガ）
  - KillSwitch は所定の条件（例: ドローダウン超過）で data/kill.flag を書き込みます。
  - ExecutionEngine は起動時やループでこの kill.flag を参照し、停止します。
- PID ファイル
  - ExecutionEngine はデフォルトで data/execution.pid を使います。SystemMonitor はこの PID を確認してプロセス健全性を評価します。

内部 API / ライブラリ利用方法（プログラムから）
- Research / AI 等の関数は Python モジュールとしてインポート可能:
  - 例: from kabusys.research import calc_momentum; from kabusys.ai.news_nlp import score_news
- DuckDB 接続を生成して渡す設計になっています:
  - import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    calc_momentum(conn, date(2026, 4, 1))

注意点 / 運用上のヒント
- .env は絶対にリポジトリにコミットしないこと（config_setup がヘッダーで注意喚起を出します）。
- 本番（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を適切に設定してください。validate_config は本番時のガードチェックを行います。
- OpenAI を使う機能は API コストやレート制限に注意してください。実行時は OPENAI_API_KEY を設定し、適切なリトライ・バックオフの挙動を確認してください。
- DuckDB / SQLite のパスをカスタマイズすることで、本番データとテストデータを安全に分離できます（paper_trading 用 DB はデフォルトで分離されています）。

ディレクトリ構成（抜粋）
-------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み・Settings
- config_setup.py           — .env 対話式ウィザード（CLI）
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py             — ニュース NLP スコアリング
  - regime_detector.py      — 市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py        — （アラート送信をまとめるモジュール）
- execution/
  - execution_engine.py     — ExecutionEngine 本体
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
  - order_record.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

付記
----
- モジュール docstring に設計上の注意（ルックアヘッドバイアス回避、フェイルセーフ動作、冪等性等）が詳述されています。運用時は該当ファイルのコメントを参照してください。
- 本 README はコードベースの主要部分から要点をまとめたものであり、実運用前に必ず validate_config、手動テスト、ステージングでの検証を行ってください。

質問や追加で README に記載したい情報（CI・デプロイ手順、より詳細な環境変数一覧など）があれば教えてください。必要に応じて追記・補足します。