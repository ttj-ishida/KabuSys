KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買・リサーチ・監視ツール群（KabuSys）の一部実装を含みます。
主要機能は Execution（発注エンジン）、Monitoring（監視・Kill Switch）、Research（ファクター計算）、
Portfolio（銘柄選定・配分）、AI（ニュースセンチメント / レジーム判定）などです。

以下は本コードベースの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成の説明です。

プロジェクト概要
----------------
KabuSys は日本株の自動売買ワークフローを想定したモジュール式システムです。主な役割は：

- シグナルに基づく銘柄選定・配分・株数計算（portfolio）
- 発注ロジック・リスク管理・注文の永続化・調整（execution）
- システム稼働状況・注文ログ・リスク監視（monitoring）
- DuckDB を用いたファクター計算・リサーチ（research）
- OpenAI を用いたニュース NLP による銘柄/マクロ評価（ai）
- 実行・監視プロセスの起動スクリプトと運用用ツール群（run_* / tools）

設計上のポイント：
- 環境変数（.env）で設定を切り替える（Settings クラス）
- Paper Trading と Live を分離（Paper は専用 SQLite DB を使用）
- ロギングは共通ユーティリティで一元管理（logs/<app>.log）
- フェイルセーフ：API 失敗やデータ不足時は安全にフォールバックする実装

機能一覧
--------
主な機能（抜粋）：

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントを抽象化し Paper/Live を切替
  - OrderRepository/OrderManager/リコンシリエーション、RiskManager など（execution パッケージ）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度の監視
  - TradeMonitor: 注文ログの健全性チェック（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限監視（Kill Switch トリガ）
  - MonitoringEngine: 上記モニタのポーリング調停、Alert 発行、kill.flag 書込み
  - Monitoring DB（SQLite）用の読み書き層（monitoring_db.py）
  - run_monitoring.py: ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔調整可能）

- Portfolio
  - 候補選定・重み計算（等配分・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - 株数計算（単元丸め、aggregate cap を考慮）

- Research
  - DuckDB 接続でファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン、IC（Information Coefficient）などの分析ツール

- AI
  - news_nlp: OpenAI を使ったニュースの銘柄別センチメント評価（ai_scores へ書込み）
  - regime_detector: ETF（1321）MA とマクロニュースを合わせて市場レジーム判定

- ツール
  - config_setup.py: .env の対話式ウィザード（初期設定）
  - validate_config.py: 起動前の設定チェック（必須環境変数やファイルの存在確認）
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

- ユーティリティ
  - logging_setup: 一貫したロギング設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定関数
  - config: 環境変数読み込み / Settings クラス（KABUSYS_ENV 等）

セットアップ手順
--------------
※ 以下はローカルで動作を確認するための基本手順です。運用環境ではさらに監視・デプロイ手順が必要です。

1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境を作成して有効化する
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（代表例）
   - pip install duckdb psutil openai pyyaml
   - （必要に応じて他のライブラリを追加してください）

3. リポジトリルートに移動
   - この README は src/kabusys に基づく実装を想定しています。プロジェクトルートには .env や data/ ディレクトリが存在している想定です。

4. 環境変数の初期作成
   - 対話式ウィザードで .env を作成する:
     - python -m kabusys.config_setup
   - 生成後、設定を検証：
     - python -m kabusys.validate_config
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-...  （AI 機能を使う場合）

5. ディレクトリ / ファイル
   - data/ や logs/ は自動作成されますが、パーミッション等を確認してください。

使い方（起動例）
----------------

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - 挙動:
    - Settings から環境を読み取り、KABUSYS_ENV=paper_trading の場合は Paper DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を利用します。
    - 起動時に data/stop_requested.flag が既にある場合は起動しません。
    - data/execution.pid に PID を書きます（Engine が PID ファイルを使用）。

- 監視ループ（Monitoring）の起動
  - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 挙動:
    - monitoring は本番 sqlite_path を使用（環境にかかわらず同じ監視 DB に書き込む設計）
    - 停止判定はプロジェクトルート/data/stop_requested.flag（存在検出でループ終了）

- .env を対話で作る / 更新する
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を指定するか PAPER_TRADING_SQLITE_PATH 環境変数で指定

- AI 機能
  - news_nlp.score_news(conn, target_date, api_key) — DuckDB 接続を渡して実行
  - regime_detector.score_regime(conn, target_date, api_key)

運用上の注意
-------------
- KABUSYS_ENV の値
  - development: ローカル開発用（発注なし）
  - paper_trading: ペーパートレード（Mock Broker、専用 DB）
  - live: 実取引（注意して設定してください）

- Kill Switch / Stop フラグ
  - KillSwitch は data/kill.flag を書き込み、run_execution 側はそれを検知して停止します。
  - run_monitoring/run_execution は停止フラグ（stop_requested.flag）によりループ終了／停止を行います。

- ロギング
  - logs/<app_name>.log に日次ローテートで保存（デフォルト logs/）
  - コンソール出力は stdout に出力されます

- データベース
  - DuckDB（分析用）と SQLite（監視・発注履歴）を利用
  - run スクリプトは起動時に必要なテーブルを作成（init_monitoring_db）します

ディレクトリ構成
----------------
（src/kabusys 以下の主なファイルと説明）

- src/kabusys/
  - __init__.py               — パッケージ宣言（バージョン等）
  - config.py                 — 環境変数読み込み・Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - execution/                — 発注関連（OrderManager, Engine, BrokerFactory 等）
    - (各サブモジュール: order_manager, order_repository, reconciler, risk_manager, execution_engine, broker_factory ...)

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム監視（CPU/メモリ/データ鮮度/実行プロセス）
    - trade_monitor.py        — 注文ログの健全性チェック（滞留注文、約定異常等）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — 各 Monitor を束ねる（ポーリング / Alert 発行）
    - alert_manager.py        —（アラート管理: LINE 送信等の抽象、実装はプロジェクトに応じて）

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - position_sizing.py      — 株数決定・aggregate cap・単元丸め
    - __init__.py

  - research/
    - factor_research.py      — momentum / volatility / value ファクター計算（DuckDB ベース）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー等
    - __init__.py

  - ai/
    - news_nlp.py             — ニュースの LLM ベースセンチメント評価（ai_scores へ書込み）
    - regime_detector.py      — ETF MA + マクロニュースで市場レジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
    - __init__.py

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

サンプル .env（抜粋）
-------------------
以下は .env の例（config_setup で生成可）:

JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

よくある質問（FAQ）
-----------------
Q: Paper Trading と Live の DB は分離されていますか？
A: はい。Execution は KABUSYS_ENV=paper_trading の場合 PAPER_TRADING_SQLITE_PATH を使います。Monitoring は常に SQLITE_PATH（監視 DB）を使う設計です。

Q: OpenAI を使うときの注意点は？
A: OPENAI_API_KEY を環境変数に設定するか、ai 関数呼び出し時に api_key を渡してください。API 呼び出しはリトライやフォールバック（失敗時は安全なデフォルト）を組み込んでいますが、コストとレート制限に注意してください。

Q: ログの保存先・世代管理は？
A: logs/<app_name>.log に日次ローテーション（30日分保持）で書きます。LOG_DIR 環境変数で変更できます。

最後に
------
この README はコードベースの要点をまとめたものです。開発・運用時は各モジュールの docstring と実装（src/kabusys 内）を参照してください。追加の実行スクリプト・CI 設定・要件ファイル（requirements.txt）などはプロジェクト要件に応じて整備してください。必要であれば README に実行フロー図や例外処理フロー、監視アラートポリシーなどを追記できます。