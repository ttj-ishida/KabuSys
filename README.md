README — KabuSys（日本株自動売買システム）
========================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした軽量なコードベースです。
主要機能は以下を含みます:
- 注文実行エンジン（本番 / ペーパートレード対応）
- システム / 注文 / リスク監視（kill switch を含む）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ用ファクター計算・特徴量探索（DuckDB ベース）
- ニュース NLP（OpenAI を用いたセンチメント評価）
- 各種ユーティリティ（設定ウィザード・検証ツール・ログ設定 等）

主設計方針:
- 環境変数 / .env による設定（.env 自動読み込み機能あり）
- DuckDB / SQLite をデータ永続化に利用
- 本番とペーパートレードは DB を分離（PAPER_TRADING 用 DB）
- ログは統一的に設定（console + 日次ローテーションファイル）

機能一覧
--------
- 設定管理
  - .env ウィザード（kabusys.config_setup）
  - 起動前設定検証（kabusys.validate_config）
- 実行
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading のときは MockBroker を使い DB を分離
  - Monitoring 起動スクリプト（kabusys.run_monitoring）
    - システム状態・データ鮮度・取引状況・リスク監視
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能
- 監視関連
  - MonitoringDB（SQLite）への永続化
  - KillSwitch（条件に応じて data/kill.flag を書き込み Execution を停止）
  - RiskMonitor（ドローダウン / ポジション数の監視）
  - TradeMonitor / SystemMonitor 等の統合管理（MonitoringEngine）
- ポートフォリオ構築
  - 候補抽出、等配分／スコア配分、リスク調整、ポジションサイズ計算
- リサーチ
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（Spearman）等
- AI
  - ニュースセンチメント取得（OpenAI API を利用）
  - 市場レジーム判定（ma200 + マクロセンチメント合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト

セットアップ手順
----------------
前提
- Python 3.9+（パッケージはコードの意図に合わせて任意の最新安定版を推奨）
- DuckDB, SQLite を使用（DuckDB は Python パッケージ duckdb を利用）
- OpenAI API を使う場合は OPENAI_API_KEY を用意

1. リポジトリをクローン
   - (例) git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必須（例）: duckdb, psutil, openai
   - 例: pip install duckdb psutil openai
   - YAML 検証を使う場合は PyYAML を追加: pip install pyyaml

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants リフレッシュトークン、KABU_API_PASSWORD 等の必須項目を入力
   - 自動ロードは既定で有効（プロジェクトルートに .env/.env.local がある場合）
   - 自動読み込みを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳格モード（警告を FAIL 扱いにする）: python -m kabusys.validate_config --strict

6. データディレクトリ等の準備
   - デフォルトの DB / ログパス:
     - data/kabusys.duckdb (DUCKDB_PATH)
     - data/monitoring.db (SQLITE_PATH)
     - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
     - logs/ (LOG_DIR のデフォルト)
   - 必要なら事前にディレクトリを作成（setup_logging が自動で作成することもあります）

使い方
------
基本的にはパッケージモジュールとして起動します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は data/stop_requested.flag を監視し、存在するとループを終了します

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper トレード用の MockBrokerClient を使用し、
    data/paper_trading.db に記録します（本番 DB とは分離）
  - ExecutionEngine は data/stop_requested.flag を検知して安全停止します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パス指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- プログラム的利用
  - ai.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research.calc_momentum(conn, date), calc_volatility(), calc_value() 等
  - portfolio.calc_position_sizes(), apply_sector_cap() 等
  - いずれも DuckDB 接続や SQLite コネクションを引数として受ける設計です

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag を自動クリアするか（0/1）

停止・制御
----------
- stop リクエスト（run_* 用）
  - data/stop_requested.flag を作成すると run_monitoring/run_execution は安全に停止します
- Kill Switch（Execution 停止要求）
  - kill_switch は条件を満たすと data/kill.flag を書き込みます
  - ExecutionEngine 起動時に kill.flag の扱いは Settings.kill_flag_clear_on_start による
- PID ファイル
  - 実行エンジンは data/execution.pid（デフォルト）に PID を書きます

ログ
---
- 共通のセットアップ: kabusys.utils.logging_setup.setup_logging(app_name=...)
  - コンソール (stdout) と日次ローテーションファイル（logs/<app_name>.log）を自動設定
  - LOG_DIR / LOG_LEVEL の環境変数で挙動を変更可能

ディレクトリ構成（主なファイル）
-------------------------------
src/
  kabusys/
    __init__.py
    run_monitoring.py              — Monitoring ポーリング起動スクリプト
    run_execution.py               — ExecutionEngine 起動スクリプト
    config.py                      — 環境変数 / Settings
    config_setup.py                — .env 対話ウィザード
    validate_config.py             — 設定検証 CLI
    utils/
      logging_setup.py             — ログ設定ユーティリティ
      process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
    monitoring/
      monitoring_db.py             — SQLite 永続化層
      system_monitor.py            — システム状態監視
      trade_monitor.py             — 取引監視（実装ファイルあり）
      risk_monitor.py              — ドローダウン / ポジション監視
      monitoring_engine.py         — 各 Monitor の統合ループ
      kill_switch.py               — kill.flag 関連
      alert_manager.py             — アラート送信管理（実装ファイルあり）
    execution/
      execution_engine.py          — ExecutionEngine
      order_manager.py             — 発注管理
      order_repository.py          — 発注リポジトリ
      reconciler.py                — 注文状態整合
      broker_factory.py            — ブローカークライアント生成
      risk_manager.py              — 発注前リスクチェック
    portfolio/
      portfolio_builder.py         — 候補選定・重み計算
      position_sizing.py           — 株数決定・スケーリング
      risk_adjustment.py           — セクター制限・レジーム乗数
    research/
      factor_research.py           — ファクター計算
      feature_exploration.py       — 将来リターン / IC / 統計
    ai/
      news_nlp.py                  — ニュース NLP（OpenAI 経由）
      regime_detector.py           — 市場レジーム判定（ma200 + LLM）
    data/ (実行時に作られる想定)
    logs/ (ログ出力先)

開発・拡張のポイント
--------------------
- DuckDB / SQLite のスキーマはコード内に定義があり、init_monitoring_db で冪等に作成されます
- AI モジュールは OpenAI のレスポンスの冗長性・エラーを考慮して堅牢に設計されています
- 監視・停止はフラグファイル方式（data/kill.flag, data/stop_requested.flag）で単純に行います
- portfolio / research モジュールは純粋関数で実装され、ユニットテストしやすい構造です

よくある質問（短く）
-------------------
Q: ペーパートレードと本番はどう分けるの？
A: KABUSYS_ENV=paper_trading にすると paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い、
   MockBrokerClient による発注処理が行われます。本番と DB は分離されています。

Q: 自動で .env は読み込まれますか？
A: はい。プロジェクトルートに .env/.env.local があれば自動読み込みされます。無効化する場合は
   KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: 監視の間隔を変えたい
A: MONITOR_POLL_INTERVAL を秒で設定してください（デフォルト 60）。例: MONITOR_POLL_INTERVAL=30

サポート / 貢献
----------------
- バグや機能追加は Issue を作成してください。Pull Request は歓迎します。
- 重要な設計決定や外部 API の使用（OpenAI 等）は README に追記していってください。

以上。必要があれば README の英文化、例のコマンドスニペット追加、依存関係の requirements.txt 化等も対応します。