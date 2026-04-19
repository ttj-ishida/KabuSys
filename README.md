README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリはトレード実行エンジン、監視機能、ポートフォリオ構築・リスク制御ロジック、調査（ファクター計算）モジュール、ニュース NLP（LLM）を使ったセンチメント評価などを含むモジュール群で構成されています。

主な設計方針
- 実行ロジックと監視ロジックを分離（ExecutionEngine / MonitoringEngine）
- DuckDB を分析用に、SQLite を稼働ログ／監視データ（およびペーパートレード DB）に使用
- Paper Trading（模擬発注）モードを用意し、本番 DB と分離
- OpenAI（gpt-4o-mini 等）をニュース/マクロ評価に利用（任意）
- 環境設定は .env（.env.local）で管理。config_setup.py による対話式ウィザードあり

機能一覧
--------
- 実行エンジン（ExecutionEngine）
  - Broker クライアント抽象化（本番 / モック）
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager）
  - 約定照合（Reconciler）
  - PID / stop フラグによる制御
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常などの検出（実装参照）
  - RiskMonitor: ドローダウン、ポジション上限の監視とログ記録
  - KillSwitch: 条件に応じた data/kill.flag の生成で Execution 停止
  - MonitoringEngine: 各 Monitor を束ねポーリング（デフォルト 60s）
  - MonitoringDB: SQLite に対する永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額/スコア加重の重み計算
  - セクター集中制限、レジーム乗数
  - 発注株数決定（lot 単位丸め、aggregate cap）
- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン、IC（情報係数）、統計サマリー
- AI（kabusys.ai）
  - ニュース記事を LLM でスコアリングし ai_scores に書き込み（score_news）
  - レジーム判定（regime_detector）: MA200 とマクロニュースを合成
- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

必要条件
--------
- Python 3.10+
- 必須ライブラリ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config の厳密検証を行う場合、任意）
- SQLite（標準ライブラリで利用可能）
- （任意）Broker の実環境接続設定（kabuステーション等）

インストール（例）
-----------------
仮想環境を作成して依存をインストールしてください（requirements.txt がある場合はそれを使用してください）。

例:
1) 仮想環境作成
   python -m venv .venv
   source .venv/bin/activate

2) 必要パッケージをインストール
   pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt があれば pip install -r requirements.txt）

セットアップ手順
--------------
1. プロジェクトルートに移動（.git または pyproject.toml を含むディレクトリ）
2. 環境変数の初期化
   - 対話式ウィザードで .env を生成/更新:
     python -m kabusys.config_setup
   - ウィザードで作成した .env は絶対に Git にコミットしないでください。
3. 設定検証:
   python -m kabusys.validate_config
   - 問題なければ [OK] メッセージが出力されます。
   - --strict を付けると警告もエラー扱いになります。
4. （任意）OpenAI を使う場合は環境変数 OPENAI_API_KEY を設定

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能の利用時）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか: 0/1）

使い方
------
起動スクリプトはパッケージモードで実行します。

- ExecutionEngine を起動（通常）
  python -m kabusys.run_execution

  動作:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動しません。
  - 実行中に data/stop_requested.flag が作成されるとエンジンを安全停止します。
  - PID ファイルデフォルト: data/execution.pid（Settings.pid_file_path で変更可）

- Monitoring を起動
  python -m kabusys.run_monitoring

  動作:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（秒、デフォルト 60）
  - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します
  - 停止は data/stop_requested.flag を作成することで行います

- Paper Trading 検証レポート出力
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  --db PATH : PAPER_TRADING_SQLITE_PATH の代わりに DB ファイルを指定可能

- AI ニューススコア付け（プログラム的に）
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, target_date, api_key="...")

停止／Kill スイッチ
- KillSwitch（kabusys.monitoring.kill_switch）は条件に応じて data/kill.flag を書き込みます。ExecutionEngine は起動時の設定により kill.flag を自動クリアすることもできます（KILL_FLAG_CLEAR_ON_START=1 が必要。※本番では 0 を推奨）。
- run_execution.py/run_monitoring.py はプロジェクト内の data/stop_requested.flag をチェックし、存在すればプロセスを終了します。

ログ
---
- デフォルトログディレクトリ: logs/
- setup_logging により stdout と logs/<app_name>.log（日時ローテーション）へ出力されます。
- ログレベルは LOG_LEVEL または setup_logging の引数で制御可能。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 配下の主なファイル・ディレクトリ（実際のファイル数はさらに多数）:

- src/kabusys/
  - __init__.py                — パッケージ定義、バージョン
  - config.py                  — 環境変数/.env ロード & Settings クラス
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 起動前の設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - execution/                 — 実行系（ExecutionEngine, OrderManager, RiskManager 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/                — 監視系
    - monitoring_db.py         — SQLite テーブル定義 / DB ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/                 — ポートフォリオ構築ロジック（純関数）
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/                  — ファクター計算・調査ユーティリティ
    - factor_research.py
    - feature_exploration.py
  - ai/                        — ニュース NLP / レジーム判定
    - news_nlp.py
    - regime_detector.py
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定

各モジュールの説明（短め）
- config.py: .env の自動ロード、Settings クラスで設定値をラップ
- config_setup.py: .env を対話的に作成/更新
- validate_config.py: 必須 env の存在確認、YAML 設定ファイルの簡易チェック
- run_execution.py: ExecutionEngine の起動フロー（DB 接続、Broker 作成、各コンポーネント組立て、スレッドで run_session）
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
- monitoring_db.py: monitoring 用 SQLite テーブル作成と CRUD 用メソッド群
- portfolio/*: 候補選定、重み算出、株数算出、セクター制限、レジーム乗数
- research/*: DuckDB を使ったファクター算出・解析
- ai/*: OpenAI を使ったニュース/マクロ評価、レジーム判定

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では .env の値に注意してください。validate_config の警告を必ず確認してください。
- kill.flag や stop_requested.flag の扱いに注意: 自動クリア設定（KILL_FLAG_CLEAR_ON_START）は本番で 1 にしないことを推奨します。
- OpenAI の API 呼び出しはコストとレイテンシに注意してください。リトライ・バックオフ・部分書き込み（冪等性）を実装済みですが、API キーの漏洩や料金上限管理は運用面で対処してください。
- DuckDB/SQLite ファイルのバックアップ、ログのローテーション設定（logs/）、ディスク容量監視を忘れないでください。

開発・拡張案
-------------
- Broker 実装の追加（実ブローカー連携）
- リアルタイムウェブ UI の追加（dashboard を活用）
- 銘柄別 lot_size をサポートする設計（position_sizing の TODO）
- テストスイート（unit / integration）の整備

ライセンス
----------
（ここにプロジェクトのライセンス情報を記載してください）

問い合わせ
----------
不明点やバグ報告はリポジトリの Issue に記載してください。

以上。README の内容はコードベース（src/kabusys 以下）に基づいて作成しています。必要であれば、実際の運用フロー（systemd / Supervisor / Docker / Kubernetes 用のサービス定義）やより詳細な運用手順書を追加できます。