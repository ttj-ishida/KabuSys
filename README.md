KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買のためのユーティリティ群・実行エントリポイント・研究用モジュールを含む Python パッケージです。
README ではプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を説明します。

プロジェクト概要
---------------
KabuSys は以下の目的を持つコンポーネント群から構成されています。

- ExecutionEngine（発注エンジン）: ブローカークライアントを通して注文を送信／管理するメイン実行ロジック（run_execution.py）。
- Monitoring（監視）: システム状態、注文状態、リスク指標をポーリングしてログ化・アラート・Kill Switch を管理（run_monitoring.py / monitoring/*）。
- Portfolio construction（ポートフォリオ構築）: 候補選定・重み計算・ポジションサイズ算出・セクター制限などの純粋関数群（portfolio/*）。
- Research（リサーチ）: DuckDB 上の価格データを使ったファクター計算、特徴量解析ユーティリティ（research/*）。
- AI（ニュース NLP / レジーム判定）: OpenAI を用いたニュースセンチメント評価・市場レジーム判定（ai/*）。
- ツール類: ペーパートレード検証レポート生成スクリプト等（tools/*）。
- 設定補助・検証: .env 対話式ウィザード（config_setup.py）・設定検証 CLI（validate_config.py）。
- 共通ユーティリティ: ロギング設定、プロセス優先度設定等（utils/*）。
- 永続化: 監視ログ用 SQLite の初期化・読み書き（monitoring/monitoring_db.py）。

主な機能一覧
------------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV が paper_trading の場合はモックブローカーを用いて data/paper_trading.db に記録（本番 DB と分離）。
  - 実プロセスはデーモンスレッドで ExecutionEngine を起動し、data/stop_requested.flag による停止を監視。
- 監視ループ（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行し、監視ログ（SQLite）へ記録。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。
  - 監視は環境にかかわらず production 用 sqlite_path（Settings.sqlite_path）を使用。
- Kill Switch（monitoring/kill_switch.py）
  - 指定条件（ドローダウン超過、ポジション数上限など）で data/kill.flag を書き込み ExecutionEngine を停止させる仕組み。
- ポートフォリオ構築（portfolio/*）
  - 候補選定（select_candidates）、重み計算（等重・スコア加重）、ポジションサイズ決定（calc_position_sizes）、セクター上限適用、レジーム乗数。
- Research（research/*）
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 利用）。
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー。
- AI モジュール（ai/*）
  - ニュースから銘柄別センチメントを LLM（OpenAI）で算出して ai_scores テーブルに記録。
  - マクロニュースと ETF MA 乖離を組み合わせた市場レジーム判定。
  - API 呼び出しは堅牢なリトライ・バリデーションを備える。
- ツール
  - Paper Trading 検証レポートを生成（tools/paper_verification_report.py）。
- 設定支援
  - .env を対話式で作成する config_setup.py。
  - 起動前に設定をチェックする validate_config.py。

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo_url>
   - 例: リポジトリルートに src/ と config/ 等が存在します。

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

3. 依存パッケージをインストール
   - 必須パッケージ（少なくとも）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定ファイル検証を行う場合にあれば詳細検証を実行）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. .env の作成
   - 対話式ウィザードを使って .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 推奨/重要な環境変数（例とデフォルト）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を使う場合に必須
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
   - .env は Git 管理に含めないでください（config_setup も警告します）。

5. DB ディレクトリとファイル
   - data/ ディレクトリは自動的に作成される箇所がありますが、手動で作る場合:
     - mkdir -p data logs

6. ログディレクトリ
   - デフォルトは logs/ にアプリ名ごとの日次ローテーションログを出力します（設定: kabusys.utils.logging_setup）。

使い方（実行方法）
-----------------

起動スクリプト（パッケージモジュールとして実行）

- ExecutionEngine を起動（本番/ペーパートレード）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBroker を使います。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動しません。
    - 実行中に data/stop_requested.flag を作成するとエンジンを停止します。
    - 実行中の PID は data/execution.pid（デフォルト）に書き込まれます。

- Monitoring を起動（監視ループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 注意:
    - 監視は Settings.sqlite_path（監視用 DB）を常に使用します（KABUSYS_ENV に依存せず本番 DB を参照）。
    - data/stop_requested.flag を作成すると監視ループが終了します。

その他コマンド・ツール

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証 CLI
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（SQLite DB をレポート）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

ランタイム制御 / フラグ類

- 停止フラグ（run_execution / run_monitoring で参照）
  - data/stop_requested.flag — 存在するとループを終了する（実行中プロセスの監視用）。
- Kill Switch（自動停止トリガ）
  - monitoring が条件を満たすと data/kill.flag を生成。ExecutionEngine はこのフラグを検出して停止することを想定。
  - KILL_FLAG_CLEAR_ON_START 環境変数が "1" の場合、起動時に kill.flag を自動クリアする（本番では推奨しない）。

設定（重要な環境変数）
---------------------
主な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckb）
- SQLITE_PATH — 監視用 SQLite ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 用）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア）

ライブラリとしての利用例
-----------------------
KabuSys はモジュールをライブラリとしても利用できます。主な公開 API 例:

- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- 研究用ファクター:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- AI:
  - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None) — DuckDB 接続と日付を渡してニューススコアを生成
- 監視 DB:
  - from kabusys.monitoring.monitoring_db import MonitoringDB — SQLite 接続を渡して読み書き API を利用可能

ディレクトリ構成（主要部分）
---------------------------
（src/kabusys 以下を抜粋して示します）

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数 / .env 自動読み込み / Settings
    - config_setup.py         — .env ウィザード（CLI）
    - validate_config.py      — 設定検証 CLI
    - run_execution.py        — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py      — ロギング設定ユーティリティ
      - process_priority.py   — プロセス優先度 / CPU affinity
    - execution/              — 発注エンジン関連（Engine / OrderManager 等）
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - data/ (実行時に生成される想定)
      - monitoring.db (デフォルト)
      - paper_trading.db
      - kill.flag
      - stop_requested.flag
    - logs/ (ログファイル出力先、デフォルト)

注意事項 / 運用上のポイント
----------------------------
- .env ファイルは機密情報を含むため、絶対にリポジトリへコミットしないでください。
- Monitoring は「本番の監視 DB（SQLITE_PATH）」を参照するので、開発時に監視を動かす場合は設定に注意してください。
- Paper Trading (= KABUSYS_ENV=paper_trading) は発注先をモックに切り替え、本番 DB と分離する設計になっています。
- OpenAI を利用する機能は API キーが必須です。API 利用時の費用・レートリミットに注意してください。
- プロダクション運用では KABUSYS_ENV=live の設定、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）などを必ず確認してください（validate_config の live ガード参照）。

開発・貢献
-----------
- 新しい機能やバグ修正は PR を作成してください。
- 大きな設計変更を行う場合は事前に issue/設計書で議論してください。
- ユニットテストや型チェックを追加すると品質向上に寄与します（現状のコードは外部依存を持つ箇所があるためモック化が必要です）。

ライセンス / バージョン
------------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンスについてはリポジトリルートの LICENSE を参照してください（存在しない場合はメンテナに確認してください）。

補足（よくある操作）
--------------------
- 監視のポーリング間隔を 30 秒にしたい:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- 実行を停止させたい（安全に）:
  - touch data/stop_requested.flag
  - ExecutionEngine と Monitoring はこのファイルを検知して終了します。
- Kill Switch を手動でクリア:
  - rm data/kill.flag

必要であれば README を README.md としてプロジェクトルートに出力します。追加で「導入手順のスクショ」「設定 .env.example」「systemd / supervisor 用の service ファイル例」等も作成できますので、希望があれば教えてください。