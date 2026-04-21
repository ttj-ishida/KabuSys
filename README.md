# KabuSys

日本株向け自動売買システムのコアライブラリ群です。  
このリポジトリには、シグナル生成・ポートフォリオ構築・発注エンジン・監視類・研究用ユーティリティ・AI を使ったニューススコアリング等の機能が含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（基本コマンド）
- 環境変数（主要項目）
- ファイル・ディレクトリ構成

---

プロジェクト概要
- KabuSys は、日本株自動売買に必要なコア機能を提供する Python モジュール群です。
- 主な責務:
  - ファクター計算（momentum / value / volatility 等）
  - ポートフォリオ構築（候補選定・重み計算・株数決定）
  - 発注エンジン（ExecutionEngine）および発注関連ユーティリティ
  - 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
  - AI を使ったニュース NLP（OpenAI）と市場レジーム判定
  - 開発用 CLI（.env ウィザード / 設定検証 / レポート生成）
  - ロギング・プロセス優先度などの運用ユーティリティ

---

機能一覧（抜粋）
- portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（リスクベース／等配分／スコア重み）
  - apply_sector_cap（セクター集中の制限）
  - calc_regime_multiplier（レジームに応じた乗数）
- research:
  - calc_momentum / calc_volatility / calc_value（DuckDB 上の prices_daily/raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary（特徴量評価）
- ai:
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、ai_scores に書き込む
  - regime_detector.score_regime: MA + マクロニュースで市場レジームを判定し保存
  - リトライ・バリデーション・レスポンスクリッピング等の安全策を実装
- monitoring:
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard を管理
  - SystemMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - run_monitoring.py: 定期ポーリングループで監視を実行（MONITOR_POLL_INTERVAL 環境変数で間隔指定）
- execution:
  - run_execution.py: 実際に ExecutionEngine を起動（KABUSYS_ENV=paper_trading の際は MockBrokerClient を使用し paper_trading 用 DB に分離）
- tools:
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定レポートを出力
- utils:
  - logging_setup.setup_logging: stdout + 日次ローテートログ設定
  - process_priority.set_process_priority / set_cpu_affinity: プロセス優先度・CPU 固定

---

セットアップ手順（ローカル開発向け）
1. Python 環境
   - 推奨: Python 3.9+（DuckDB / psutil / openai 等を利用）
2. 依存パッケージをインストール
   - 必要なパッケージ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証を使う場合）
   - 例: pip install duckdb psutil openai pyyaml
   - （リポジトリに requirements.txt がある場合は pip install -r requirements.txt）
3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を配置
4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
5. DB の準備
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
   - run_monitoring / run_execution は起動時に DB 初期化（監視テーブル等）を行います
6. OpenAI を利用する場合
   - 環境変数 OPENAI_API_KEY を設定してください（ai/news_nlp.py, ai/regime_detector.py で参照）
7. ログ
   - デフォルトログディレクトリ: logs/
   - LOG_DIR 環境変数で変更可。LOG_LEVEL でログレベル設定。

---

主要な使い方（コマンド）
- .env を対話式に作る:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き（デフォルト 60 秒）
  - 監視は settings.sqlite_path（本番 sqlite_path）を常に使用します
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します
- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い paper_trading 用 DB に記録（SQLITE は分離）
  - 停止: data/stop_requested.flag を作成すると実行エンジンに停止シグナルを送ります
  - 実行時は PID ファイル（data/execution.pid）を出力
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）
- ライブラリ呼び出し（Python API）
  - AI ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - research のファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value

---

環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 動作モード:
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
    - paper_trading: 発注はモック、専用 DB (PAPER_TRADING_SQLITE_PATH) を使用
    - live: 実口座で発注が行われます（注意）
- DB / ログ:
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（監視 DB）ファイルパス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログディレクトリ
- その他:
  - OPENAI_API_KEY — OpenAI API キー（ai 機能利用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading の MockBrokerClient の約定モード（instant/partial/never/reject）

簡易 .env の例
（機密情報は伏せて記入すること。 .env は決して Git にコミットしない）
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

運用上の注意
- run_monitoring は環境に関わらず settings.sqlite_path（本番監視 DB）を使用する設計です。
- run_execution は KABUSYS_ENV=paper_trading の場合、DB を完全に分離してペーパートレードを行います。
- Kill Switch:
  - KillSwitch はリスク基準（ドローダウン等）に応じて data/kill.flag を書き込みます。ExecutionEngine はこれを検出して安全に停止できます。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 は危険（production では 0 推奨）。
- ログ:
  - logs/<app_name>.log に日次ローテートで出力。ログディレクトリ作成に失敗した場合、コンソールのみ出力になります。
- OpenAI:
  - API 呼び出しはリトライやレスポンス検証を組み込んでいますが、API キーやクォータに注意してください。
- DB マイグレーション:
  - monitoring DB は init_monitoring_db でテーブルを冪等作成します。古い DB に対しては ALTER 等のマイグレーション処理も一部含まれます（例: latency_ms, peak_value カラム追加）。

---

ディレクトリ構成（主要）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定取得
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）・ai_scores 書き込み
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / ...）
    - system_monitor.py      — システム・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 操作
    - monitoring_engine.py   — 各 Monitor を束ねる
    - ...（alert_manager, trade_monitor 等）
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
    - logging_setup.py
    - process_priority.py
  - (その他、execution/, data/, strategy/ 等のサブパッケージ)

---

開発上のヒント
- テスト時に .env の自動ロードを無効にしたい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数で設定すると自動ロードをスキップします
- logging_setup.setup_logging を各起動スクリプトで呼ぶことで統一的ログ管理が可能です
- 各モジュールは副作用を最小化する設計（DuckDB 接続や sqlite3 接続を外から注入する）になっています

---

ライセンス / 貢献
- 本 README はコードから読み取れる範囲での使用方法・注意点をまとめたものです。  
- 実行前に .env を正しく設定し、特に本番モード（KABUSYS_ENV=live）では API キーや通知設定を十分に確認してください。

--- 

問題の報告や改善案はリポジトリの Issue をご利用ください。