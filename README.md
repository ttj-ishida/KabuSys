README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本リポジトリは、取引実行エンジン、監視（モニタリング）機能、ポートフォリオ構築やリスク管理ロジック、リサーチ用ファクター計算、LLM を使ったニュース解析などのモジュール群を含みます。

主な設計方針
- ランタイム設定は .env または環境変数で管理
- Paper Trading（ペーパートレード）と Live（本番）を明確に分離
- DuckDB（分析用）と SQLite（監視・注文ログ）を併用
- LLM 呼び出し（OpenAI）を扱うモジュールはフェイルセーフ実装（リトライ・フォールバック）
- 可能な限り副作用を抑えた純粋関数設計（portfolio / research 等）

機能一覧
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 環境変数 KABUSYS_ENV によって paper_trading / live / development を切替
  - paper_trading 時は MockBroker を使用し、data/paper_trading.db に記録（本番 DB と分離）
  - リスク管理（RiskManager）、OrderManager、Reconciler を組み合わせて起動
- Monitoring（run_monitoring.py / monitoring モジュール）
  - SystemMonitor（CPU/Mem/Disk・プロセス・データ鮮度監視）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（危険検出時に data/kill.flag を書き込み Execution を停止）
  - AlertManager（アラート送信の抽象化）
  - Monitoring DB（SQLite）へのログ保存（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio コンポーネント
  - 候補選定、等金額・スコア加重配分、セクター制限、ポジションサイズ決定
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI 系
  - news_nlp: raw_news を LLM（OpenAI）へ送り銘柄別センチメントを ai_scores に記録
  - regime_detector: ETF に基づく MA200 乖離とマクロニュース LLM を合成して市場レジーム判定
- 開発支援ツール
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: 環境変数 / config/*.yaml の事前検証 CLI
  - tools/paper_verification_report.py: ペーパートレード DB を用いたパフォーマンス検証レポート生成

セットアップ手順
----------------
前提
- Python 3.10+（typing の記法に依存）
- システムに sqlite3 が利用可能
- 必要な外部ライブラリ（下記参照）

インストール（例）
1. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は config 検証を行う場合に推奨: pip install PyYAML

3. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data

.env の初期設定
1. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   （対話プロンプトに従って必須値を入力してください）

2. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合: python -m kabusys.validate_config --strict

主要な依存ライブラリ
- duckdb: 分析用 DB
- psutil: プロセス優先度 / CPU 情報取得
- openai (公式 SDK): LLM 呼び出し（news_nlp / regime_detector）
- PyYAML（任意）: config/*.yaml の構文チェック用

重要な環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用トークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（"1" で有効）

使い方
------
起動例（CLI モジュール）
- 環境セットアップ（.env を用意）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ExecutionEngine を起動
  - 本番相当（KABUSYS_ENV=live）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - ペーパートレード:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - この場合、MockBrokerClient が使われ paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL を指定（任意）:
    - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用します（監視 DB は本番 DB を参照する設計）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db でパスを指定可能。

プロセス制御・Kill Switch
- 監視モジュールはリスクやプロセス停止等を検出した場合に data/kill.flag を書き込みます（ExecutionEngine 側はこのフラグを見て安全に停止します）。
- Execution 起動時に kill.flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定（本番では 0 を推奨）。

プロセス優先度
- 起動スクリプトは最初に set_process_priority("high") を呼び出します（psutil に依存。権限によっては設定に失敗しますが無害にスキップされます）。

設定自動ロード
- デフォルトでプロジェクトルートの .env（続いて .env.local）を自動読み込みします。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要部分）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 自動読み込み・Settings クラス
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュースを LLM でスコアリング、ai_scores に書込
  - regime_detector.py     — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py       — SQLite を用いた監視ログ永続化層（テーブル定義・CRUD）
  - system_monitor.py      — CPU/Mem/Disk、データ鮮度、PID チェック
  - trade_monitor.py       — 注文滞留 / 約定異常検出
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — kill.flag の書込/確認ロジック
  - monitoring_engine.py   — 各 Monitor を束ねたポーリング実行ロジック
  - alert_manager.py       — アラート送信を抽象化（実装箇所により派生）
- execution/
  - (ExecutionEngine / OrderManager / BrokerFactory 等の実装がここに入ります)
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定ロジック（リスクベース・等金額等）
  - risk_adjustment.py     — セクター上限 / レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum / volatility / value）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ等
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

その他
-----
- Monitoring DB スキーマは monitoring_db.init_monitoring_db() で冪等に作成されます（マイグレーション措置あり）。
- AI モジュールを使用するには OPENAI_API_KEY を設定してください。モデルは gpt-4o-mini がデフォルト設定です（コード内定義）。
- config/*.yaml は存在する場合 YAML をパースして検証します（PyYAML を利用）。存在しない場合は警告となります。
- 開発時のヒント: 自動 .env 読み込みはプロジェクトルート検出（.git または pyproject.toml）によって行われるため、配布後や別ディレクトリでテストする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 の設定や手動で環境変数を渡してください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報が含まれている場合はプロジェクトルートの LICENSE を参照してください（本README には記載がありません）。
- バグ報告・機能要望は issue を通してお願いします。プルリクエストは歓迎します。

補足（よくある質問）
-------------------
Q: Monitoring はどの DB を見るの？
A: run_monitoring.py は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。Execution の paper_trading モードは専用の PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離します。

Q: MONITOR_POLL_INTERVAL の設定方法は？
A: 環境変数 MONITOR_POLL_INTERVAL に秒数（整数）を設定します。1 未満や不正値はデフォルト 60 秒にフォールバックします。

Q: OpenAI 失敗時の挙動は？
A: LLM 呼び出しはリトライやフォールバック（スコア 0.0 等）を実装しており、API が失敗してもプロセス全体を停止させないフェイルセーフ設計です。

問い合わせ
--------
不明点・改善要望はリポジトリの issue に詳細を記載して報告してください。