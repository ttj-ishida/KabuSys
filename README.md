# KabuSys

日本株向け自動売買システムのコアライブラリ（README 日本語版）

概要
---
KabuSys は日本株の自動売買／バックテスト／運用支援を目的としたモジュール群です。  
本リポジトリには、以下の主要機能を提供する Python モジュールが含まれます。

- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化（paper/live 両対応）
- 監視・アラート機能（System / Trade / Risk のモニタリング、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- ニュース NLP / レジーム判定（OpenAI API を利用したセンチメント評価）
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading 検証レポート等）
- ログ設定・プロセス優先度ユーティリティ

機能一覧
---
主要な機能/モジュール（抜粋）：

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper/live/development 分岐）
  - run_monitoring.py: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
- 設定管理
  - config.py: 環境変数/.env の読み込み・アクセスラッパー（Settings クラス）
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の前検証 CLI
- 監視関連
  - monitoring/monitoring_db.py: SQLite による永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring/system_monitor.py: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - monitoring/trade_monitor.py, monitoring/risk_monitor.py, monitoring/kill_switch.py, monitoring/monitoring_engine.py（各種監視・Kill Switch 実装）
- 発注関連（execution パッケージ）
  - ExecutionEngine、OrderManager、RiskManager、Reconciler、BrokerClientFactory（paper/live 切替）
- ポートフォリオ（portfolio パッケージ）
  - portfolio_builder.py: 候補選定・等金額/スコア加重
  - position_sizing.py: 株数計算、利用可能資金に対するスケーリング、単元処理
  - risk_adjustment.py: セクター上限、レジーム乗数
- リサーチ（research パッケージ）
  - factor_research.py: momentum / volatility / value ファクター計算（DuckDB を使用）
  - feature_exploration.py: 将来リターン、IC、要約統計
- AI（ai パッケージ）
  - news_nlp.py: ニュース記事を OpenAI API でセンチメント評価し ai_scores に書き込み
  - regime_detector.py: ETF (1321) の MA とマクロニュースで市場レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading 結果の検証レポート生成

セットアップ手順
---
1. Python 環境（推奨: 3.10+）を準備し、仮想環境を作成する
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールする
   - duckdb
   - psutil
   - openai
   - （任意）PyYAML（validate_config の YAML 検証に使用）
   例:
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

3. プロジェクトルート配下に .env を配置する
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます

5. データディレクトリ等の権限・作成
   - デフォルトでは data/ に DB や PID/flag ファイルを作成します。必要に応じてディレクトリを作ってくださいが、ロガー / DB 初回接続時に自動生成されることもあります。

主要な環境変数
---
主に Settings で参照される主要変数（抜粋）：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 用）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先（デフォルト logs/）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時の kill.flag 自動クリア (0/1)
- PID_FILE_PATH / KILL_FLAG_PATH: デフォルトは data/ 以下
- OPENAI_API_KEY: OpenAI API を使う機能で必要

使い方（起動・運用）
---
- ExecutionEngine を起動（本番/ペーパートレード/開発は KABUSYS_ENV で制御）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=development は発注を伴わない設定（テスト向け）

  挙動:
  - paper_trading: MockBrokerClient を使用し、データは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に保存されるため本番 DB と完全分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動しません（停止フラグ）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は Settings にかかわらず本番 sqlite_path を利用して監視ログを永続化します（monitoring の DB は環境に依らず production path を参照する設計）

- .env の作成 / 更新（ウィザード）
  - python -m kabusys.config_setup

- 設定の事前検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いに

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - --from / --to で期間指定、--db で DB パス指定可能

- AI 関連
  - OpenAI API を使う機能（news_nlp.score_news, regime_detector.score_regime）は OPENAI_API_KEY を設定してください
  - これらは DuckDB 接続を受け取り、AI 評価→テーブル書込を行います

停止・フラグ操作
---
- run_execution / monitoring の停止制御
  - data/stop_requested.flag を作成すると起動中のループは検知して終了します
  - Kill Switch は data/kill.flag を用いて ExecutionEngine に停止指示を送ります（monitoring が条件を満たすと書き込む）
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 を推奨）

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます。
- デフォルトは stdout 出力＋日次ローテーションのファイル出力（logs/<app_name>.log、30日分保持）
- LOG_DIR または引数で出力先を変更可能

ディレクトリ構成（主要ファイル）
---
プロジェクトの主要なディレクトリ/ファイル（src/kabusys を基準）:

- kabusys/
  - __init__.py
  - config.py                      # 環境変数/.env のロードと Settings
  - config_setup.py                # .env 対話式ウィザード
  - validate_config.py             # 設定検証 CLI
  - run_execution.py               # ExecutionEngine 起動スクリプト
  - run_monitoring.py              # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  # Paper Trading 検証レポート
  - ai/
    - news_nlp.py                   # ニュース NLP スコアリング
    - regime_detector.py            # 市場レジーム判定
  - monitoring/
    - monitoring_db.py              # SQLite スキーマ + MonitoringDB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (通知管理 - 実装参照)
  - execution/                       # ExecutionEngine, broker, order 管理（実装ファイル群）
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
  - data/ (デフォルトの DB / PID / flag 保存場所)
  - config/ (YAML 設定ファイル群: system_config.yaml 等)

開発者向けメモ / 注意事項
---
- 自動 .env ロードはデフォルトで有効。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で受け取ります（不正値はデフォルト 60 秒へフォールバック）。
- process_priority 設定はプラットフォーム差（Windows/Linux/macOS）を吸収しようとしていますが、権限不足で失敗する可能性があります。その場合はログ警告が出ます。
- DuckDB を利用するリサーチ・AI モジュールは、十分な prices_daily / raw_financials / raw_news 等のデータが前提です。テスト時はダミーデータを用意してください。
- OpenAI 呼び出しはネットワーク・レート制限に対してリトライやフォールバックを行う設計ですが、API キーやコスト管理は運用者が行ってください。

ライセンス / バージョン
---
- package version: __version__ = "0.1.0"（kabusys/__init__.py）

最後に
---
この README はコードベースの主要点を抜粋してまとめたものです。各モジュールの詳細な使い方や内部ロジックはソース内の docstring とコメントを参照してください。質問や追加のドキュメントが必要であれば教えてください。