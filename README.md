KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買システム「KabuSys」のコードベースです。
本READMEは開発者／運用担当者向けに、プロジェクト概要・機能・セットアップ手順・基本的な使い方・ディレクトリ構成をまとめたものです。

要点（短く）
- 実行スクリプト
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report
- 設定: .env（config_setup で作成可）。Settings クラスが .env / .env.local を自動ロード（無効化可）。
- データ: デフォルト DB は data/kabusys.duckdb（DuckDB）, data/monitoring.db（SQLite）。Paper trading は分離された data/paper_trading.db を使用。

プロジェクト概要
----------------
KabuSys は以下を主な目的とする自動売買プラットフォームです。
- ファクター算出・リサーチ（DuckDB を用いた履歴データ解析）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- Execution エンジン（本番 / ペーパートレード切替、ブローカークライアント抽象化）
- 監視（システム状態・注文・リスク監視、Kill Switch）
- AI モジュール（ニュースセンチメント / レジーム判定：OpenAI API を利用）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

主な機能一覧
-------------
- config
  - Settings: .env/.env.local の自動ロードと環境変数取得ラッパー
  - config_setup: 対話式に .env を作成・更新するウィザード
  - validate_config: 起動前の環境検証 CLI（--strict で警告を FAIL 扱い）
- execution
  - ExecutionEngine（EngineConfig）: 発注・注文管理・リスク管理を統合して運用するエンジン
  - BrokerClientFactory: 本番とペーパートレードでクライアントを切り替え
  - ペーパートレードは本番 SQLite DB と分離（PAPER_TRADING_SQLITE_PATH）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine: 定期ポーリングで状態チェック、アラート出力、Kill Switch 評価
  - monitoring_db: SQLite を用いた監視ログの永続化（テーブル＆マイグレーション対応）
  - run_monitoring: ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
- research
  - factor_research: Momentum / Volatility / Value などのファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC、統計サマリ等の解析ユーティリティ
- portfolio
  - 候補選定、重み計算、リスク調整、ポジションサイズ算出（純粋関数）
- ai
  - news_nlp: OpenAI を使ったニュースセンチメント集約・ai_scores 書込み
  - regime_detector: MA200 とマクロニュースの組合せで市場レジーム判定し DB に書込
- tools
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを生成

前提 / 必要環境
----------------
- Python 3.9+（型注釈に沿うためなるべく新しいバージョンを推奨）
- 必須ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai
- 任意 / 運用時に便利:
  - PyYAML（validate_config で config/*.yaml のパース検証を行う場合）
- OS: Linux / macOS / Windows で動作するよう考慮されていますが、プロセス優先度設定等はプラットフォーム差分あり

セットアップ手順
-----------------
1. リポジトリを取得
   - git clone <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - PyYAML（オプション）: pip install pyyaml

   ※ requirements.txt がある場合:
   - pip install -r requirements.txt

4. .env の作成
   - 対話式に作る: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 注意: .env は機密情報を含むため Git にコミットしないこと

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 本番なら: python -m kabusys.validate_config --strict

6. データディレクトリ等の作成
   - data/ ディレクトリは必要に応じ自動作成されますが、手動で作っておくと権限問題を回避できます。
   - logs/ ディレクトリはログ出力先（環境変数 LOG_DIR で変更可）

使い方（運用・開発）
-------------------

共通: モジュールをそのまま Python モードで実行できます（package モード）。
例:
- 実行エンジン（本番／ペーパー切替は KABUSYS_ENV で制御）
  - python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PaperTrading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）へ記録します。
  - ストップは data/stop_requested.flag を作成すると実行エンジンが検出して停止します。
  - 実行時に pid ファイル（デフォルト data/execution.pid）を出力します。

- 監視ループ
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（デフォルト 60）。
  - 監視は本番用 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env ファイルを対話式に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - 起動前に必須環境変数や DB パス等をチェックします。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 期間内の稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL を出力します。

主要な環境変数（代表例）
-----------------------
- KABUSYS_ENV: 実行モード（development / paper_trading / live）
  - development: 開発用（発注なし等の安全設定）
  - paper_trading: MockBroker を使ったペーパートレード（DB: PAPER_TRADING_SQLITE_PATH）
  - live: 本番（実際に発注）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定振る舞い（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- KILL_FLAG_PATH / PID_FILE_PATH: ファイルパスの上書きが可能

サンプル .env（抜粋）
--------------------
以下は .env に入れる代表的な項目の例です（実際は config_setup を利用してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

運用上の注意
-------------
- .env は機密情報を含むため Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。
- monitoring は監視用 DB（sqlite_path）を参照します。MONITOR_POLL_INTERVAL の値は 1 秒以上にしてください（0 以下は無効で 60 秒にフォールバックします）。
- OpenAI 呼び出しは課金対象であり、API キーや呼び出し頻度に注意してください。
- Paper Trading は本番 DB と分離されていますが、設定ミスで上書きしないよう DB パスを確認してください。

ディレクトリ構成
-----------------
（src/kabusys 配下を主要ファイル中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定読み込み（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - data/                    — データ関連モジュール（別途）
  - research/
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 株数算出・スケーリング
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - execution/               — 実行エンジン関連（broker factory 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤー
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文関連監視（ファイルあり）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag 書込みロジック
    - alert_manager.py       — アラート送信（LINE 等、実装次第）
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコア計算
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity 設定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力

ログ・データファイル（デフォルト）
- logs/<app_name>.log        — 日次ローテーションでログを保持（デフォルト logs/）
- data/monitoring.db         — 監視ログ用 SQLite（Settings.sqlite_path）
- data/paper_trading.db      — ペーパートレード専用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb        — DuckDB（履歴データ / リサーチ用）
- data/execution.pid         — Execution の PID（既定）
- data/stop_requested.flag   — 手動停止フラグ（run_execution / run_monitoring の検出対象）
- data/kill.flag             — Kill Switch が書き込む停止フラグ

開発者向けメモ
----------------
- DuckDB を使った research モジュールは SQL を直接実行して値を取得します。ローカルで DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）を準備しておくと機能確認が容易です。
- OpenAI を使う機能は API のエラー（429、タイムアウト、5xx）に対してリトライやフォールバック（0.0 スコア等）を実装しており、失敗時に全体を壊さない設計になっていますが、キーの漏洩や課金には注意してください。
- logging_setup.setup_logging() を全スクリプトで呼んでいるため、ログの一元管理が容易です。ログ出力先は環境変数 LOG_DIR で変更できます。

サポート / 追加情報
-------------------
- 設定ファイル雛形: config/*.yaml や .env.example（リポジトリにある場合）を参照してください。
- 既知の挙動や設計思想はコード内の docstring / コメントに随所に記載されています。新しい開発や変更を加える際はこれらの注釈を参照してください。

以上。環境構築や実行で不明点があれば、どの部分で詰まっているか（エラーメッセージや実行コマンド等）を教えてください。設定例や起動スクリプトの具体的なコマンド例も提供します。