KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内の主要スクリプト・ユーティリティの使い方、設定、ディレクトリ構成をまとめたものです。コードベースは src/kabusys 以下にあり、取引実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI 補助処理などのモジュールで構成されています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムフレームワークです。主な機能は以下を含みます。

- 実行エンジン（ExecutionEngine）：ブローカークライアント経由で注文を発行・管理
- 監視（Monitoring）：システム稼働状況、注文ログ、リスク（ドローダウン・ポジション数）監視とアラート／Kill Switch
- ポートフォリオ構築：シグナルから候補選定・重み計算・株数決定
- リサーチ：DuckDB を使ったファクター計算・特徴量解析
- AI 支援：OpenAI を用いたニュースセンチメント（ニュースNLP）・市場レジーム判定
- ツール：.env ユーザ対話ウィザード、設定検証、ペーパートレード検証レポート生成 等

機能一覧（抜粋）
----------------
- run_execution.py：ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading.db に記録（本番 DB と分離）
  - 起動時に process priority を "high" に設定
  - ストップフラグ（data/stop_requested.flag）があれば起動を中止
- run_monitoring.py：SystemMonitor ポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を使用
- config_setup.py：対話式 .env 作成ウィザード
- validate_config.py：.env と config/*.yaml の妥当性検証 CLI
- tools/paper_verification_report.py：ペーパートレード実行結果の検証レポート生成
- ai/news_nlp.py：ニュースを OpenAI でスコアリングして ai_scores に書き込む
- ai/regime_detector.py：ETF MA とマクロ記事の LLM センチメントを合成してレジーム判定
- monitoring/*：MonitoringDB（SQLite 永続化）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、AlertManager など
- portfolio/*：候補選定、重み算出、ポジションサイズ計算、セクターキャップなど純粋関数群

セットアップ手順
----------------
1. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - pyyaml（config ファイル検証用、任意）
   例:
     pip install duckdb psutil openai pyyaml

   注意: プロジェクトに requirements.txt があればそれを使ってください。
   pip install -r requirements.txt

3. 環境変数の設定（.env）
   - 対話式ウィザードで .env を作成:
     python -m kabusys.config_setup
   - もしくは .env を手動作成（例は後述）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格に扱いたい場合:
     python -m kabusys.validate_config --strict

5. DB ディレクトリの作成（通常は自動で作成されますが確認）
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視用): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

使い方
------

環境ファイル（.env）について（主要項目）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite ファイルパス（監視 DB）（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（1=クリア, 0=しない）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）で必要

（.env の生成には python -m kabusys.config_setup を推奨）

主要コマンド
- ExecutionEngine を起動（起動中は data/execution.pid を書く）
  - python -m kabusys.run_execution

- Monitoring（監視ループ）を起動
  - MONITOR_POLL_INTERVAL で間隔秒を指定（デフォルト 60）
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

Kill Switch / 停止制御
- kill.flag（デフォルト data/kill.flag）: KillSwitch が書き込むアラートフラグ（ExecutionEngine に停止を指示）
- stop_requested.flag（data/stop_requested.flag）: 手動で作成すると run_execution / run_monitoring が起動・ループ中に検知して終了します
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動でクリアします（本番では 0 推奨）

ログ
- ログは logs/<app_name>.log に日次ローテーションで出力（デフォルト logs/）
- setup_logging が全スクリプトで共通して設定されます。ログディレクトリ作成失敗時はコンソール出力のみになります。

AI 機能（OpenAI）
- news_nlp.score_news / ai.regime_detector.score_regime は OPENAI_API_KEY を必要とします
- 大量の API 呼び出しやレート制限に対応したリトライロジックを備えています
- 開発時は API 呼び出し部分の差し替え（テスト用モック）を想定しています

環境変数の上書き・特殊設定
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）。デフォルト 60。0 や負値は無効でデフォルトにフォールバック。
- PAPER_FILL_MODE — ペーパートレードの fill モード（instant / partial / never / reject）
- KABUSYS_ENV によって run_execution は paper_trading 用 DB を使うか本番 DB を使うか切り替わります（paper_trading 時は PAPER_TRADING_SQLITE_PATH を使う）。

ディレクトリ構成
----------------
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py — パッケージ初期化、__version__
  - config.py — 環境変数/.env の自動ロードと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）
    - regime_detector.py — マーケットレジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・DB ラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — 注文ログ・滞留注文検出（ファイル未掲示部分あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を統合してポーリング
    - alert_manager.py — （アラート送信ロジック、ファイルに含まれている想定）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定 / 投下資金スケーリング
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring_db.py — 監視 DB（実装は monitoring/monitoring_db.py にまとまっています）

実例: 典型的な起動フロー
-----------------------
1. .env を生成
   python -m kabusys.config_setup

2. 設定を検証
   python -m kabusys.validate_config

3. ExecutionEngine を起動（バックグラウンドで動かすなど）
   python -m kabusys.run_execution

4. 別プロセスで監視を起動
   MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

5. 停止（手動）
   touch data/stop_requested.flag  # どちらのスクリプトもこのファイルを検知して終了します

注意事項 / トラブルシューティング
---------------------------------
- 本番（KABUSYS_ENV=live）での運用前に必ず validate_config を実行し、LINE 通知設定等を確認してください。
- .env は機密情報を含むため Git にコミットしないでください（config_setup でもその旨を出力します）。
- OpenAI を使う機能は API キーとコストがかかります。開発時は無効にするかモックを使ってください。
- DuckDB / SQLite のパスは Settings で指定できます。監視は run_monitoring が常に本番 sqlite_path を読みます（意図的な挙動）。

サンプル .env（config_setup で生成される内容の抜粋）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0
- OPENAI_API_KEY=...

ライセンス / 貢献
-----------------
（プロジェクトにライセンスファイルがあればここに追記してください）

最後に
------
この README はコードベース内の主要なエントリポイントと設定をまとめたものです。細かい内部実装や未掲載のユーティリティ（例: execution/*.py の OrderManager/ExecutionEngine 詳細）はソースコードのドキュメントと docstring を参照してください。質問や追加ドキュメントの要望があれば教えてください。