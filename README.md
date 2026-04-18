README
======

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
戦略・銘柄選定・ポジションサイジング・リスク管理・監視・分析ツール群、さらに一部で OpenAI を使ったニュース NLP／レジーム判定機能を備えています。  
このリポジトリはライブラリ本体（src/kabusys）と、起動スクリプト／コマンドラインツール群を含みます。

主な特徴
--------
- ポートフォリオ構築モジュール（候補選定、重み算出、ポジションサイズ算出）
- リスク調整（セクターキャップ、レジーム乗数）
- 実行エンジン起動スクリプト（paper_trading / live を切替）
  - paper_trading 時は MockBroker を用いて専用 SQLite に記録（本番 DB と分離）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（フラグファイルで ExecutionEngine を停止）
- 監視ログ永続化（SQLite）
- Research：DuckDB を用いたファクター計算・特徴量探索ユーティリティ
- AI 機能（ニュース NLP による銘柄感情スコアリング、レジーム検出） — OpenAI API を利用
- ツール：Paper Trading 検証レポート生成スクリプト
- 簡易的な .env ウィザード（config_setup）と設定検証ツール（validate_config）

前提／必須ソフトウェア
--------------------
- Python 3.10+
- SQLite（標準で同梱）
- DuckDB（Python パッケージ）
- 推奨パッケージ（後述の pip インストール参照）

インストール（開発環境）
-----------------------
1. リポジトリをクローン／配置
2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - 監視・設定検証の一部機能で PyYAML があると config/*.yaml の検証が可能:
     - pip install PyYAML

（requirements.txt がある場合はそちらを利用してください）

環境変数（主なもの）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要オプション:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - paper_trading: 実取引は行わず MockBroker を使用（DB 分離）
  - live: 本番モード（実際に発注）
- OPENAI_API_KEY — OpenAI を使う場合に必要（ai.news_nlp / ai.regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- PAPER_FILL_MODE — paper_trading 時の約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（1: 有効、0: 無効。デフォルト 0）
- MONITOR_POLL_INTERVAL — (監視スクリプト専用) ポーリング間隔（秒、デフォルト 60）

起動・使用方法
--------------

1) 初期 .env 作成（対話ウィザード）
   - python -m kabusys.config_setup
   - 対話形式で .env を生成します（.env は Git 管理しないこと）

2) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

3) ExecutionEngine（エンジン）起動
   - python -m kabusys.run_execution
   - 注意:
     - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用（PAPER_TRADING_SQLITE_PATH）
     - _STOP_FLAG（data/stop_requested.flag）があると起動せず終了します
     - 実行中は data/execution.pid に PID を書きます
     - 起動前に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag をクリアします（本番では 0 推奨）

4) Monitoring（監視）起動
   - python -m kabusys.run_monitoring
   - 動作:
     - Settings.sqlite_path（監視用 DB）に接続して監視テーブルを初期化
     - SystemMonitor.check_once を定期実行（デフォルト 60 秒）
     - ポーリング間隔を変えるには環境変数 MONITOR_POLL_INTERVAL を整数秒で設定
     - 停止は data/stop_requested.flag を作成することで行えます

5) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

6) AI 機能（プログラム内呼び出し）
   - ニューススコアリング（ai.news_nlp.score_news）
     - 引数に DuckDB 接続と target_date を渡して実行
     - OpenAI API キーを OPENAI_API_KEY 環境変数か引数で指定
   - レジーム判定（ai.regime_detector.score_regime）
     - DuckDB 接続と target_date を渡して実行

停止フラグ・キルスイッチ
------------------------
- 停止要求: data/stop_requested.flag — run_monitoring/run_execution はこのファイルの存在を検知して停止します
- Kill Switch: data/kill.flag — KillSwitch（リスク超過等を検出した際に書き込む）により ExecutionEngine の停止をトリガできます
- 実行時の挙動:
  - ExecutionEngine は起動時に kill.flag を自動でクリアするかどうかを KILL_FLAG_CLEAR_ON_START に従って制御できます（本番では自動クリアを無効にすることを推奨）

ロギング
--------
- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...") を各起動スクリプトが呼び出します
- ログは標準出力（stdout）とファイル（日次ローテーション）に出力されます
- デフォルトログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で決まります

ファイル／ディレクトリ構成（主要部分）
-------------------------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成スクリプト
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite のテーブル初期化 / 永続化レイヤ
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 制御
    - monitoring_engine.py    — 各 Monitor をまとめるエンジン
    - (他に TradeMonitor / AlertManager 等が想定される)
  - portfolio/
    - portfolio_builder.py    — 候補選定、重み計算
    - position_sizing.py      — 株数計算・スケール調整
    - risk_adjustment.py      — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py  — 将来リターン / IC / 要約統計
  - monitoring/               — 監視系（上記）
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - data/  (実行時に使用)
    - monitoring.db           — デフォルト監視 DB（SQLite）
    - paper_trading.db        — paper_trading 用 DB（分離）
    - kill.flag               — Kill Switch ファイル（生成される）
    - stop_requested.flag     — 実行停止フラグ（ツール等で作成）
  - logs/                     — デフォルトログ出力先

注意事項 / 運用上のヒント
-----------------------
- .env は絶対に Git にコミットしないこと（README、.gitignore を確認）
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定し、自動クリアを無効化することを推奨します
- paper_trading モードは本番 DB と完全分離しています。テストや検証には paper_trading を使用してください
- OpenAI の呼び出しは失敗時にフェイルセーフ（0.0 のフォールバックなど）で続行する設計ですが、API キーは必ず設定してください（ai 機能を使わない場合は不要）
- process_priority.set_process_priority はプラットフォーム依存の権限や制限を受けます。アクセス権がない場合は警告が出てスキップされます

開発・拡張
----------
- DuckDB を用いた分析・ファクター計算は副作用を持たない純粋関数群として実装されています（テストが書きやすい）
- AI 呼び出し部分は API エラー・レート制限を考慮した再試行ロジック・バリデーションを持っています。テスト時は内部の API 呼び出し関数をモックしてください（モジュールにコメントあり）

よく使うコマンド例
-----------------
- .env を作る（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
- Paper Trading レポート（期間指定）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア実行（サンプル、Python REPL などで）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date=date(2026,4,11), api_key="sk-...")

ライセンスと貢献
----------------
本リポジトリに関するライセンス情報・貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

サポート
-------
実装や運用に関して不明点がある場合は、リポジトリの issue を作成するか、チーム内ドキュメントを参照してください。

---  
以上。README の内容はコード中の設定・挙動を元に作成しています。実際の運用前に python -m kabusys.validate_config を実行して環境変数やファイルパスを確認してください。