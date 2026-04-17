README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。本リポジトリは以下の主要機能を含みます。

- 発注実行エンジン（ExecutionEngine）およびブローカークライアントの抽象化（paper_trading 時はモック利用）
- 実行・監視のための独立したプロセスランナー（run_execution, run_monitoring）
- 監視ログ保存用の SQLite 層（MonitoringDB）
- リスク監視・Kill Switch（ドローダウン／ポジション上限で停止フラグを出す）
- ポートフォリオ構築ロジック（候補選定、重み付け、ポジションサイズ決定、セクター制限等）
- リサーチ用モジュール（ファクター計算、将来リターン、IC 計算など）
- ニュース NLU（OpenAI を用いたニュースセンチメント/レジーム判定）
- ペーパートレード検証レポート生成スクリプト

主な特徴
--------
- 環境切替: KABUSYS_ENV による development / paper_trading / live 切替
- Paper trading は本番 DB と完全分離（デフォルト: data/paper_trading.db）
- DuckDB を用いたリサーチ向け高速集計（デフォルト: data/kabusys.duckdb）
- 監視用 SQLite（デフォルト: data/monitoring.db）に監視・トレードログ・ダッシュボードを永続化
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント・レジーム判定（API キーは環境変数で指定）
- フラグファイルによるプロセス制御（data/kill.flag, data/stop_requested.flag 等）
- プロセス優先度設定ユーティリティ（Windows / POSIX を吸収）

必要条件（推奨）
----------------
- Python 3.10+
- 主要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config 検証を行う場合に必要）

例:
  pip install duckdb psutil openai pyyaml

セットアップ手順
----------------

1. リポジトリをクローンしてプロジェクトルートへ移動
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. .env を作成
   - 対話式ウィザードで作成する:
     python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考にしてください（.env は絶対にコミットしないこと）。

3. 必須環境変数を設定（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...（AI 機能を使う場合）
   - KABUSYS_ENV=development|paper_trading|live
   - その他: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, PAPER_FILL_MODE など

4. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

5. データディレクトリの作成（必要に応じて）
   デフォルト DB/フラグファイルは data/ 下に作られます。自動作成されますが、適宜アクセス権等を確認してください。

主要環境変数（抜粋）
-------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG, INFO, …）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

使い方
------

1. 環境ウィザード（.env 作成 / 更新）
   python -m kabusys.config_setup

2. 設定検証
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict

3. ExecutionEngine（発注エンジン）起動
   - 本番 / 開発 / paper_trading は KABUSYS_ENV に従って挙動が変わります。
   - 起動:
     python -m kabusys.run_execution
   - 特記事項:
     - paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します（本番 DB と分離）。
     - プロセス優先度を "high" に設定し PID ファイル（デフォルト: data/execution.pid）を書きます。
     - 停止は data/stop_requested.flag を作成するか、Kill Switch により data/kill.flag が書かれると停止処理が行われます。

4. 監視ループの起動（Monitoring）
   - 起動:
     python -m kabusys.run_monitoring
   - オプション:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
   - 役割:
     - SystemMonitor, TradeMonitor, RiskMonitor を定期実行し、監視ログを SQLite に保持、必要に応じて kill.flag を書きます。

5. Paper Trading 検証レポート生成
   - 起動:
     python -m kabusys.tools.paper_verification_report
   - 期間指定:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

6. AI / ニューススコアリング（開発者向け）
   - OpenAI API キーが必要です（OPENAI_API_KEY）。
   - news_nlp.score_news(conn, target_date, api_key=None) を呼び出すと ai_scores テーブルに書き込みます。
   - regime_detector.score_regime(conn, target_date, api_key=None) で日次レジーム判定・書き込みが行えます。

プロセス制御 / フラグ・PID
--------------------------
- 起動時に ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を書きます。
- 監視プロセスは data/stop_requested.flag を検知して自身を終了します（run_monitoring/run_execution 共通の振る舞い）。
- KillSwitch（条件が満たされた場合）により data/kill.flag が書かれると ExecutionEngine 停止を誘発します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 推奨）。

ディレクトリ構成
----------------
リポジトリの主要なディレクトリ・ファイル構成（src/kabusys 以下）。実際のファイルやサブパッケージはさらに多くあります。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前の設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py              — ニュース NLP / OpenAI 呼び出しとスコア保存
    - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 層（テーブル作成 / CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （アラート送信の管理、実装ファイルあり）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - execution/
    - （ExecutionEngine、OrderManager、OrderRepository などの実装）
  - data/                      — 実行時に生成されるディレクトリ（DB, pid, flag 等）

補足・運用上の注意
-----------------
- .env の自動ロード:
  - プロジェクトルートが特定できる場合、.env を自動で読み込みます（.env.local は .env を上書き）。
  - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用等）。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等にテーブル作成・簡単なマイグレーション（カラム追加）を行います。

- Paper trading と本番 DB:
  - paper_trading モード時は paper_sqlite_path を使用し、monitoring の記録も paper_trading DB に分離します（安全確保のため）。

- OpenAI 呼び出し:
  - API 安定性のためリトライ・バックオフ処理を実装していますが、API キー制限やコストに注意してください。
  - レスポンスのバリデーションを厳密に行い、部分的な失敗があっても既存データを不必要に上書きしない設計になっています。

開発者向け
----------
- Python の型注釈や docstring を重視した設計です。ユニットテストやモック差し替えを使ったテストがしやすいよう関数分割されています。
- OpenAI 呼び出し部はモジュール内で分離しているため、テスト時に patch して API をモック化できます。
- リサーチコードは DuckDB 接続を受け取り SQL + Python で計算します。データテーブル (prices_daily, raw_financials など) に依存します。

ライセンス / バージョン
-----------------------
- パッケージ内バージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

貢献・改善提案
--------------
バグ報告・改善提案は Issue を立ててください。開発方針、設計文書（PortfolioConstruction.md, StrategyModel.md 等）に沿った変更を歓迎します。

以上。必要であれば README に実際の .env.example のテンプレートや systemd / docker でのデプロイ手順、さらに詳しい監視アラートフローや API 使用量の注意点などを追記します。どの情報を追加したいか教えてください。