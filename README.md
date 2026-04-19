# KabuSys

日本株自動売買システムの Python パッケージ (README)

## プロジェクト概要
KabuSys は日本株向けの自動売買フレームワークです。ファクター計算、ポートフォリオ構築、注文実行、監視・アラート、Paper Trading 検証、LLM を用いたニュース NLP / レジーム判定機能などを含みます。内部データは主に DuckDB（分析用）と SQLite（監視・発注ログ）で管理されます。

主な設計方針:
- 本番/ペーパートレードを環境変数で切り替え可能
- DB はファイルベース（DuckDB / SQLite）
- ロギングは統一的に設定（コンソール + 日次ローテートファイル）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントやレジーム判定をサポート
- フェイルセーフ（API失敗時のフォールバック、部分書き込み保護、冪等なDB操作）

## 主な機能一覧
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重の重み計算
  - リスク調整（セクター上限、レジーム乗数）
  - 株数計算（リスクベース／等分配）、単元株丸めと aggregate cap 対応
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクターを DuckDB 上で計算
  - ランク相関 (IC)、将来リターン計算、統計サマリー
- AI モジュール
  - ニュースのセンチメントを OpenAI で評価し ai_scores に格納
  - マクロニュース＋ETF MA 乖離から日次の市場レジームを判定
- 実行エンジン（ExecutionEngine：発注処理）
  - 環境により実口座または MockBroker（ペーパートレード）を自動選択
  - リスク管理、注文管理、注文ログの永続化
- 監視（Monitoring）
  - システム状態、データ鮮度、滞留注文、ドローダウン等の監視
  - Kill Switch（条件達成で data/kill.flag を書き込み、Execution を停止）
  - 複数 Monitor を束ねる MonitoringEngine（ポーリング）
- 管理用 CLI / スクリプト
  - 環境設定ウィザード（.env 生成）: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
  - 実行・監視プロセス起動スクリプト: run_execution.py / run_monitoring.py

## 必要要件（例）
主な依存ライブラリ（使用する機能により追加で必要）:
- Python 3.9+（型注釈に応じて）
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- PyYAML（config の検証を行う場合に推奨）

インストール例:
pip install -r requirements.txt
（requirements.txt はプロジェクトに含めてください。上記ライブラリを最低限インストールしてください）

## セットアップ手順（基本）
1. リポジトリをクローンしてプロジェクトルートへ移動。
2. Python 仮想環境を作成・有効化して依存をインストール。
3. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 自動ロードは既定で有効（プロジェクトルートに .env があると起動時に読み込まれる）。テスト等で無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
4. 設定の検証（オプション）:
   - python -m kabusys.validate_config
     --strict を付けると警告も失敗として扱う
5. DB 初期化は起動スクリプトが自動で行います（monitoring 用テーブル等を作成）。

## 主要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能使用時)
- KABUSYS_ENV (development / paper_trading / live) — デフォルト development
  - paper_trading: MockBroker を使い、PAPER_TRADING_SQLITE_PATH に記録
  - live: 実口座で発注（注意して設定すること）
- PAPER_FILL_MODE (instant|partial|never|reject) — Paper Trading の約定モード
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 SQLite, デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)
- LOG_DIR (ログファイル保存先, デフォルト: logs/)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒, デフォルト: 60)

※ .env はセキュリティ上 Git にコミットしないでください（config_setup が警告を出します）。

## 使い方

基本的なコマンド例:

- 環境設定ウィザード（.env を生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（発注処理をバックグラウンドで開始）
  - python -m kabusys.run_execution
  - 停止は data/stop_requested.flag を作成することでループを抜ける（run_execution と run_monitoring は stop_requested.flag を参照）。また監視側が kill.flag を書くことで Execution に停止を促す設計です。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に Settings.sqlite_path（監視 DB）を使用してログを書きます（KABUSYS_ENV に依存せず本番の sqlite_path を使います）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使ってデフォルトパスを上書き可能

- AI 機能（ニューススコア / レジーム判定）はそれぞれモジュール関数で使用:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 呼び出し時に api_key を渡すか環境変数 OPENAI_API_KEY を設定してください。

ログ
- setup_logging により root ロガーが設定され、stdout に出力されるほか logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリは LOG_DIR 環境変数で上書き可能。

停止 / Kill Switch
- 実行中のプロセスを外部から停止する仕組み:
  - run_execution / run_monitoring はプロジェクトの data/stop_requested.flag を監視して終了します。
  - 監視側から致命的なリスクが検出された場合、KillSwitch が data/kill.flag を書いて Execution 停止を促します。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動で kill.flag をクリアします（本番では 0 推奨）。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要構成（抜粋）です。プロジェクトルートは src/ をパッケージルートに含む構成を想定しています。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、.env 自動読み込み
  - config_setup.py          — .env 対話ウィザード CLI
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるセンチメント評価
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・集約スケーリング
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算 (DuckDB)
    - feature_exploration.py — 将来リターン, IC 計算, 統計
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 / 永続化レイヤ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文ログ監視）※実装参照
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
    - kill_switch.py         — kill.flag の管理
    - alert_manager.py       — （通知送信）※実装参照
  - execution/
    - execution_engine.py    — 発注 Engine（実行本体）※実装参照
    - broker_factory.py      — Broker クライアント生成（Mock/実装切替）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化 / 参照
    - reconciler.py          — 注文整合処理
    - risk_manager.py        — 発注時リスク制約
  - data/                    — データファイル (例: data/kabusys.duckdb, data/monitoring.db 等)
  - logs/                    — ログ出力ディレクトリ（デフォルト）

（注）上記はコードベースの一部抜粋に基づく構成。実際のリポジトリでは additional modules / scripts / config/ が存在します。

## 開発メモ / 注意点
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0以下の値は無効でデフォルトにフォールバックします。
- run_execution は KABUSYS_ENV=paper_trading の場合に MockBrokerClient を使用し、paper_trading.db に書き込みます（本番 DB と完全分離）。
- 設定検証ツールは PyYAML 未インストール時に YAML 検証をスキップする旨を警告します。
- OpenAI API を使用する機能は API エラーやレート制限に対して指数バックオフでリトライしますが、最終的に失敗する場合はフォールバック動作（スコア 0.0 など）で安全に継続する実装です。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します（ファイル出力を無効化します）。

---

追加で README に記載してほしい内容（デプロイ手順、systemd サービス例、DB スキーマ詳細、API ドキュメント等）があれば教えてください。必要に応じて追記します。