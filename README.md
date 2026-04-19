README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の参照実装です。  
このコードベースは以下の主要機能を含みます。

- 発注・リスク管理を行う ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働状況・注文ログ・リスク監視を行う Monitoring
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量解析、将来リターン・IC 計算）
- ニュース NLP を使った銘柄スコアリング（OpenAI 統合）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 結合）
- 各種 CLI ツール（.env 設定ウィザード、設定検証、Paper Trading レポート生成 など）

主な設計方針:
- DuckDB を分析用 DB として使用、SQLite を監視・注文ログ用に使用
- 本番・ペーパートレードの DB は分離（KABUSYS_ENV による切替）
- LLM 呼び出しは失敗に対してフェイルセーフ（失敗時はスキップまたはデフォルト値）
- ルックアヘッドバイアス回避のため、日時参照は慎重に扱う

機能一覧
--------
- 実行関連
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
  - ExecutionEngine は PID ファイル（data/execution.pid）を管理し、stop フラグで停止可能

- 監視関連
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定可）
  - MonitoringEngine: System / Trade / Risk 各モニタを束ねてアラート・Kill Switch 評価を実施
  - monitoring_db: SQLite を用いた監視テーブルの初期化と CRUD

- ポートフォリオ構築
  - 候補選定、等比率・スコア加重、セクター上限、レジーム乗数、株数決定（単元丸め・aggregate cap）

- リサーチ
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン / IC（スピアマンランク相関） / 統計サマリー

- AI 統合
  - news_nlp: OpenAI でニュースを集約して銘柄別センチメントを ai_scores に保存
  - regime_detector: ETF MA とマクロセンチメントを合成して market_regime を書き込み

- ユーティリティ
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 環境変数・設定ファイル検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート生成

セットアップ手順
----------------
前提:
- Python 3.9+（一部の型注釈やモジュール互換性に依存）
- SQLite は標準ライブラリで利用
- DuckDB, psutil, openai 等のパッケージをインストールする必要あり

推奨依存パッケージ例:
- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証を行う場合に必要）

インストール例:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install duckdb psutil openai PyYAML

（requirements.txt がある場合は pip install -r requirements.txt）

初期設定:
1. .env を生成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV は development / paper_trading / live のいずれか

2. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit 1

デフォルトのファイルパス（.env に設定しなければ下記が使われます）
- DuckDB: data/kabusys.duckdb
- SQLite (監視): data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- ログディレクトリ: logs/
- PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

使い方
------
主な起動方法（プロジェクトルートで実行）:

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を .env に設定すると paper_trading 用 DB に記録され、MockBroker が使われます

- Monitoring（常駐）を起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30  python -m kabusys.run_monitoring

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

フラグ・停止方法:
- Kill Switch:
  - KillSwitch はリスク閾値を満たすと data/kill.flag を作成し ExecutionEngine に停止シグナルを与える（ExecutionEngine は起動時にこれを検査して停止します）。
- 手動停止（全プロセス）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して終了します。
- PID ファイル:
  - run_execution が実行中は data/execution.pid に PID を書きます。実行中判定 / 再起動制御で使用されます。

ログ:
- ログは標準出力と logs/<app_name>.log（日次ローテーション、30日保持）に出力されます。
- app_name は起動スクリプト毎に "execution" / "monitoring" 等が使われます。

主な環境変数（重要なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

簡単な .env の例（機密値は伏せてください）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成
----------------
（src 以下をパッケージとして記載）

src/
  kabusys/
    __init__.py
    config.py                # 環境変数/.env ロード & Settings
    config_setup.py          # .env 対話式ウィザード
    validate_config.py       # 設定検証 CLI
    run_execution.py         # ExecutionEngine 起動スクリプト
    run_monitoring.py        # SystemMonitor ポーリング起動スクリプト

    execution/               # 発注エンジン関連（ブローカーファクトリ 等）
      ... (OrderManager, ExecutionEngine など)

    monitoring/
      monitoring_db.py       # SQLite テーブル初期化・永続化 API
      system_monitor.py      # システム状態・データ鮮度監視
      trade_monitor.py       # 注文ログ監視（滞留・約定異常）
      risk_monitor.py        # ドローダウン・ポジション上限監視
      kill_switch.py         # kill.flag 管理
      monitoring_engine.py   # 複数モニタの実行統括
      alert_manager.py       # アラート送信（LINE など）※実装箇所参照

    portfolio/
      portfolio_builder.py   # 候補選定・重み付け
      position_sizing.py     # 株数決定、aggregate cap
      risk_adjustment.py     # セクター上限、レジーム乗数

    research/
      factor_research.py     # ファクター計算（momentum/value/volatility）
      feature_exploration.py # 将来リターン / IC / 統計サマリー

    ai/
      news_nlp.py            # ニュース NLP スコアリング（OpenAI 統合）
      regime_detector.py     # 市場レジーム判定（MA + マクロ LLM）
      __init__.py

    utils/
      logging_setup.py       # ログ設定ユーティリティ
      process_priority.py    # プロセス優先度 / CPU affinity 設定
      __init__.py

    tools/
      paper_verification_report.py   # ペーパートレード検証レポート
      __init__.py

data/                 # 実行時に使用する DB / フラグ / PID を格納する既定フォルダ（.gitignore 推奨）
logs/                 # ログファイル保存先（デフォルト）

追加注意事項 / 運用メモ
-----------------------
- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知等を適切に設定してください（validate_config は本番向け追加チェックを行います）。
- OpenAI を使う機能（news_nlp / regime_detector）は API 呼び出しに料金がかかります。API キー管理とコール頻度に注意してください。
- run_execution は paper_trading と live（実際の発注）を切替えます。paper_trading モードでは DB を分離しているため、本番データと混ざりませんが、運用時は設定ミスに注意してください。
- データファイル（data/）や .env は必ず秘密管理（Git にはコミットしない）してください。

問題報告・貢献
---------------
バグ報告や改善提案は Issue を作成してください。プルリクエスト歓迎です。変更を行う際はユニットテスト・静的解析の追加をお願いします。

-----
必要があれば README にサンプル .env のテンプレートや、よくあるトラブルシューティング（DB マイグレーション失敗、OpenAI 接続エラー、psutil の権限エラーなど）を追記できます。どの情報を優先的に追加したいか教えてください。