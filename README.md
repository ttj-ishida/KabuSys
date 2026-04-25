README — KabuSys
=================

概要
----
KabuSys は日本株自動売買の実験/運用向けライブラリ兼実行フレームワークです。本リポジトリは以下の主要機能群を提供します。

- 実行エンジン（ExecutionEngine）による発注フロー（本番 / ペーパートレード分離）
- 監視ループ（System / Trade / Risk）と Kill Switch による安全停止
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制限）
- リサーチ（ファクター計算、将来リターン・IC 計算、特徴量サマリー）
- AI モジュール（ニュースのセンチメントスコアリング / 市場レジーム判定：OpenAI 利用）
- ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度制御）
- 運用ツール（ペーパートレード検証レポート生成）

バージョン: 0.1.0（src/kabusys/__init__.py）

主な機能（抜粋）
----------------
- 設定管理: .env の自動ロード（.env, .env.local、OS 環境変数優先）および Settings クラス（src/kabusys/config.py）
- 対話式設定ウィザード: python -m kabusys.config_setup による .env 作成
- 設定検証: python -m kabusys.validate_config（--strict で警告を FAIL 扱い）
- 実行エンジン起動: python -m kabusys.run_execution（KABUSYS_ENV=paper_trading 時は paper DB を使用）
- 監視ループ起動: python -m kabusys.run_monitoring（MONITOR_POLL_INTERVAL で間隔指定可）
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report
- AI: kabusys.ai.score_news（ニュースセンチメント）、kabusys.ai.regime_detector.score_regime（市場レジーム）
- ログ設定ユーティリティ、プロセス優先度設定ユーティリティ

前提条件 / 依存関係
-------------------
主な依存パッケージ（プロジェクトで参照されているもの）:
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML パースを有効にする場合）

インストール例:
- 仮想環境作成（例）
  python -m venv .venv
  source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートへ移動。
2. 仮想環境を作成し、依存パッケージをインストール（上記参照）。
3. 初回は .env を作成する:
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 生成した .env を編集して必要なシークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を設定
4. 設定検証:
   python -m kabusys.validate_config
   --strict を付けると警告があると exit(1) になります
5. 必要に応じて data/ ディレクトリ配下（DB、PID、フラグファイル）や logs/ を作成。多くは起動時に自動作成されます。

重要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: Execution は MockBrokerClient を使い data/paper_trading.db を使用
  - live: 本番運用モード（注意喚起あり）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（0/1: 起動時に kill.flag を自動クリアするか）
- PID_FILE_PATH / KILL_FLAG_PATH（デフォルトは data/ 配下）

実行方法（よく使うコマンド）
---------------------------
- 実行エンジン（ExecutionEngine）を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使用し MockBrokerClient が使われます
  - 実行中に data/stop_requested.flag を作成するとループが検知して停止します

- 監視ループを起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path を使用（環境に依らず）

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD
    --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

AI 機能（注意）
--------------
- ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY 環境変数（または明示的な api_key 引数）が必要
  - gpt-4o-mini を想定した実装で、バッチ/リトライ/バリデーションロジックを備えています
- 市場レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI を用いるため API キーが必要
- API 呼び出しはレート制限や 5xx をリトライしますが、失敗時は安全側のフォールバック（例: macro_sentiment=0.0）を取る設計です

停止 / フラグ運用
------------------
- 実行系の外部停止:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して安全停止を行います（run_execution は起動時に既に存在すれば起動しない）。
- Kill Switch:
  - KillSwitch は設定された kill_flag_path（デフォルト: data/kill.flag）へ理由を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にこのフラグを自動クリアします（本番では 0 を推奨）。

ログ
----
- ログはデフォルトで stdout とログファイル（logs/<app_name>.log）に出力します。
- ログローテーションは日次で最大 30 日保持（TimedRotatingFileHandler）。

ディレクトリ構成（抜粋）
----------------------
プロジェクトの主要ファイル/ディレクトリ構成（src/kabusys 配下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py       — （本リストでは省略されたがトレード監視実装あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （通知ロジック）
  - execution/               — ExecutionEngine / order 管理 / broker factory（実行ロジック）
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

開発メモ
--------
- データベース
  - DuckDB は分析用（prices_daily, raw_financials 等）。パスは DUCKDB_PATH。
  - SQLite は監視ログ・注文履歴用（monitoring.db / paper_trading.db）。init_monitoring_db() でスキーマを自動作成・マイグレーションします。
- 設定ロード順:
  OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- テストの観点:
  - OpenAI 呼び出し箇所は _call_openai_api を patch して差し替え可能（ユニットテスト用）。
  - データベース操作はローカルファイル接続を使うためテスト用 DB コピーを使うと良いです。

よくある運用例
--------------
- ローカル開発:
  KABUSYS_ENV=development python -m kabusys.run_execution
  （発注は行わない実装想定のため安全に実行可能）

- ペーパートレード検証:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  結果は data/paper_trading.db に記録される（本番 DB と分離）

- 監視と Kill Switch:
  常に run_monitoring を systemd や cron / 障害監視で動かし、異常時に data/kill.flag を set して Execution を停止させます

補足
----
- 本 README はコードベース内の docstring と実装からまとめています。運用前に必ず python -m kabusys.validate_config による設定検証を行い、本番 (KABUSYS_ENV=live) では特に LINE 通知等のアラート設定を確認してください。

以上。必要であればサンプル .env.example の例や systemd ユニットファイル、よくあるトラブルシュート項目を追記します。どの情報を追加しますか？