KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買システムの参照実装です。以下の主な機能を備え、実運用（live）・ペーパートレード（paper_trading）・開発（development）それぞれの環境に対応します。

主な特徴
--------
- 発注エンジン（ExecutionEngine）と監視（Monitoring）を分離して運用可能
- ペーパートレード用に本番 DB と完全分離された MockBroker を利用可能
- DuckDB を使ったリサーチ／ファクター計算モジュール
- OpenAI を用いたニュース NLP（銘柄ごとセンチメント）および市場レジーム判定
- 監視ログは SQLite（monitoring.db）へ永続化
- Kill Switch（data/kill.flag）で安全に ExecutionEngine を停止可能
- 簡易的な CLI ツール（設定ウィザード・設定検証・ペーパートレード検証レポートなど）

機能一覧
--------
- execution: 発注処理の組み立てと実行（Broker クライアント抽象化）
- monitoring: システム状態、注文状態、リスク監視、Kill Switch、アラート連携
- portfolio: 候補選定・配分・ポジションサイズ計算・セクター制限
- research: DuckDB 上でのファクター計算（モメンタム・ボラティリティ・バリュー等）
- ai: OpenAI を利用したニューススコアリング（news_nlp）、市場レジーム判定（regime_detector）
- tools: Paper Trading の検証レポート生成スクリプトなど
- utils: ログ設定・プロセス優先度設定などのユーティリティ

前提条件 / 必要ライブラリ
-----------------------
以下は本リポジトリで使われている主要なパッケージです。プロジェクトに requirements.txt がある場合はそれを使用してください。

- Python 3.9+（型ヒントの利用状況から推奨）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の妥当性チェックを行う場合）
- SQLite（標準ライブラリで利用）
- （オプション）その他開発用ライブラリ

セットアップ手順
----------------

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ...
   - cd <project_root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai PyYAML
   - （必要に応じてその他パッケージを追加）

4. 環境変数設定（.env の作成）
   - 対話式ウィザードで .env を作成: 
     - python -m kabusys.config_setup
   - もしくはリポジトリ直下に .env を手動で作成（.env.example を参考にしてください）

   自動ロード：
   - config.py はプロジェクトルート（.git または pyproject.toml を検知）から .env/.env.local を自動読み込みします。
   - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります。

使い方
------

主要な起動／操作例：

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、data/paper_trading.db へ結果を記録します。
  - 実行中に data/stop_requested.flag が作られると安全に終了処理を行います。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - デフォルトで 60 秒間隔のポーリング（環境変数 MONITOR_POLL_INTERVAL で上書き可）
  - 監視は常に本番の sqlite_path を使用（環境に依らず monitoring は本番 DB のパスを参照）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを指定する場合: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

注意事項 / 運用メモ
------------------
- 環境に応じた DB:
  - 本番（live） / development: data/monitoring.db (SQLITE_PATH のデフォルト)
  - paper_trading: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH により変更可）
- Kill Switch:
  - data/kill.flag を作成すると ExecutionEngine に停止シグナルを送ります（KillSwitch 経由）。
  - KillSwitch はリスク監視（ドローダウン / ポジション数超過）によっても自動で書き込まれます。
  - kill.flag をクリアするには KillSwitch.clear() を使うか手動でファイルを削除してください。
  - 起動時に kill flag を自動でクリアする設定 KILL_FLAG_CLEAR_ON_START=1（本番では 0 推奨）。
- ログ:
  - デフォルトのログディレクトリは logs/、各アプリケーションごとに日次ローテートされます（logs/execution.log など）。
  - ログレベル: LOG_LEVEL で制御（例: DEBUG, INFO）。
- プロセス優先度:
  - run_execution / run_monitoring は起動時に set_process_priority("high") を呼びます（psutil 経由）。権限がない場合は警告が出ます。
- DuckDB:
  - research / ai モジュールは DuckDB 接続を受け取り、prices_daily / raw_financials / raw_news 等のテーブルを参照します。
- OpenAI（AI 機能）:
  - ニューススコアリング・レジーム判定は OPENAI_API_KEY を環境変数で設定する必要があります（引数で渡すことも可）。
  - レスポンスの堅牢性向上のためリトライ・バリデーション処理が入っています。
- マイグレーション:
  - monitoring_db.init_monitoring_db() は既存 DB に対して必要なカラム追加（例: peak_value, latency_ms）を行うため起動時の互換性維持を行います。

環境変数一覧（主要）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 推奨 / 任意:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番でのアラート通知に使用（任意）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=有効、デフォルト 0）

ディレクトリ構成（抜粋）
-----------------------
リポジトリの主要構成（src/kabusys 配下を中心に説明）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定読込ロジック（.env 自動読み込み）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前の設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度/CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（テーブル作成・読み書き）
    - system_monitor.py     — システム監視（CPU/メモリ/ディスク・データ鮮度）
    - trade_monitor.py      — （注文監視: 滞留・約定異常など）※実装ファイルあり
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 管理
    - monitoring_engine.py  — 複数モニタを束ねるエンジン
    - alert_manager.py      — アラート送信（LINE など）※実装ファイルあり
  - execution/
    - execution_engine.py   — 実際の発注ループ（Engine）
    - broker_factory.py     — Broker クライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

開発者向け補足
---------------
- DuckDB や SQLite のスキーマはコード内に示された SQL を参照してください（monitoring_db.init_monitoring_db 等）。
- AI 周りの外部 API 呼び出しはリトライやレスポンスバリデーションを実装しているため、テスト時は _call_openai_api をモック化してテストしてください。
- .env は絶対にリポジトリへコミットしないでください（config_setup.py にも同旨の注意があります）。

よくある操作のコマンドまとめ
--------------------------
- .env を作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベースの主要な使い方と構造を簡潔にまとめたものです。詳細な設計（ポートフォリオ構築の数式や戦略仕様）はコード内の docstring や設計ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）を参照してください。質問や補足があれば教えてください。