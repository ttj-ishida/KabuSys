KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）向けライブラリ群です。
主な機能としては以下を含みます：

- 実行エンジン（ExecutionEngine）と監視モジュール（MonitoringEngine）を独立して起動・運用
- Paper Trading（模擬発注）を本番 DB と分離して安全に検証可能
- ポートフォリオ構築（候補選定・配分・ポジションサイズ決定）用の純粋関数群
- 監視ログ永続化（SQLite）とモニタリングロジック（システム、トレード、リスク）
- AI を使ったニュースセンチメント / レジーム判定（OpenAI）
- 研究用ファクター計算・特徴量探索（DuckDB）
- 各種ユーティリティ（ロギング設定、プロセス優先度、設定ウィザードなど）
- 検証レポート生成ツール（Paper Trading 検証）

主要な機能一覧
----------------
- 実行（run_execution.py）
  - KABUSYS_ENV に応じて実ブローカー or MockBroker（paper_trading）を使用
  - Paper Trading は data/paper_trading.db（デフォルト）へ記録して本番 DB と分離
- 監視（run_monitoring.py / MonitoringEngine）
  - システム状態、トレードログ、リスク（ドローダウン・保有上限）を定期チェック
  - kill.flag を書き込む KillSwitch により ExecutionEngine を停止できる
- 設定管理
  - config_setup.py：.env を対話式に作成/更新するウィザード
  - validate_config.py：起動前チェック（必須環境変数や config/*.yaml の存在等）
  - Settings（config.py）：環境変数からの設定読み込み（デフォルト値・妥当性検証）
- 研究（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算・統計サマリー
- AI（ai）
  - news_nlp: raw_news を OpenAI で評価し ai_scores を生成
  - regime_detector: ma200 とマクロニュースを合成して market_regime を判定
- ポートフォリオ（portfolio）
  - 候補選定、等ウェイト・スコア加重、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ算出
- ツール
  - paper_verification_report: Paper Trading DB から検証レポート生成
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------
前提
- Python 3.9+（コードは型ヒントに依存）
- 必要な外部ライブラリ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - （任意）PyYAML（config ファイル検証時に利用）

1. リポジトリをチェックアウトして依存をインストール
   - 例: pip install -r requirements.txt（requirements.txt があれば）
   - または個別に pip install duckdb psutil openai

2. .env を作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考にする

3. 設定の検証
   - python -m kabusys.validate_config
   - 致命的な問題があると exit(1) を返します
   - 警告をエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

4. DB の初期化
   - 実行/監視スクリプトが起動時に必要なテーブルを作成します（init_monitoring_db）
   - DuckDB / SQLite のファイルはデフォルトで data/ 以下に作成されます（設定で変更可）

主要な環境変数（よく使うもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant/partial/never/reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を利用する場合の API キー
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring: デフォルト 60）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH / KILL_FLAG_PATH — PID / kill flag のパス設定

使い方（起動例）
----------------
- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- 監視（バックグラウンド監視ループ）
  - MONITOR_POLL_INTERVAL を上書きする例（60秒がデフォルト）
    - export MONITOR_POLL_INTERVAL=30
  - 起動:
    - python -m kabusys.run_monitoring
  - 停止:
    - data/stop_requested.flag を作成するとループが検知して終了する

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading DB にのみ記録します
  - 実行中に停止させる:
    - data/stop_requested.flag を作成するとエンジンが停止を開始
  - Kill Switch（監視が致命的事象を検出した場合に書き込む）
    - data/kill.flag によって ExecutionEngine に停止シグナルを送ることができます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI（ニューススコア / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime を呼び出す（プログラム経由）
  - 実行には OPENAI_API_KEY が必要

ログと監視
----------
- setup_logging は各起動スクリプトから呼び出され、stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）を設定します
- デフォルトログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定可能

停止・強制停止（フラグファイル）
------------------------------
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring.py / run_execution.py はこのファイルの存在を監視し、検出時に安全に終了します
- kill.flag（data/kill.flag）
  - Monitoring の KillSwitch がトリガーした場合に書き込まれ、ExecutionEngine 停止の合図として利用されます
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に自動クリアされます（本番では 0 推奨）

ディレクトリ構成（概要）
-----------------------
以下はソースツリー内の主なファイル/ディレクトリです（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動ローディング
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ma200）
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層・MonitoringDB クラス
    - system_monitor.py      — システム状態監視
    - trade_monitor.py       — （トレード監視ロジック）
    - risk_monitor.py        — ドローダウン / 保有上限監視
    - kill_switch.py         — Kill Switch 実装（kill.flag 書込）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信ロジック）
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 株数決定 / リスク制限 / 単元丸め
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 & CPU affinity
  - data/ (runtime: DB / flag / pid 等を置くディレクトリ。デフォルトで作成されることがある)

補足 / 注意点
-------------
- Paper Trading は本番データと完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）
- OpenAI を使う機能は API キーとネットワークアクセスが必要です。API エラーはリトライロジックで保護されていますが、キー未設定では例外となる箇所があります
- validate_config は PyYAML が無い場合でも動作しますが、config/*.yaml の内容検証はスキップされ警告が出ます
- ローカルでの開発や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効化できます
- 最低限必要な環境変数は validate_config で確認できます（JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD 等）

開発者向けメモ
---------------
- 設定は Settings クラス（config.py）経由で読み取ってください。settings = Settings() が提供されています
- 監視 DB（MonitoringDB）は sqlite3.Connection をラップし、row_factory を sqlite3.Row に設定するため、接続の副作用に注意してください（ただし監視用 DB と注文用 DB は別ファイルで分かれています）
- logging_setup.setup_logging を各スクリプトの先頭で呼ぶことで一貫したログ出力が得られます
- プロセス優先度設定（set_process_priority）は psutil を使って実行環境に合わせて最適化しますが、権限不足時は警告を出してスキップします

バージョン
---------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

問い合わせ / 貢献
-----------------
バグ報告やプルリクエストはリポジトリの Issue / PR を利用してください。設計思想や API の互換性に関するディスカッションは歓迎します。

以上が本リポジトリの README です。必要に応じてセットアップ手順や利用例を追加しますので、特に詳しく知りたい箇所があれば教えてください。