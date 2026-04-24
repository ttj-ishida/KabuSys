README.md

KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買サンプルシステムです。戦略算出、ポートフォリオ構築、注文実行、監視・アラート、研究/バックテスト向けユーティリティなどをモジュール化して提供します。本リポジトリのスクリプトから ExecutionEngine（発注エンジン）や監視ループを起動し、設定は .env ファイルで管理します。

主な特徴
--------
- ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、本番 DB と分離（data/paper_trading.db）。
  - プロセス優先度設定、PID ファイル管理、停止フラグによる安全停止対応。
- Monitoring（監視）起動スクリプト（run_monitoring.py）
  - システム稼働状態、データ鮮度、注文ログ、リスク（ドローダウン・ポジション上限）をポーリング監視。
  - Kill Switch による ExecutionEngine 停止フラグ生成。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
- ポートフォリオ構築ユーティリティ（等重・スコア加重・リスクベースの株数計算など）
- 研究用モジュール（ファクター計算、特徴量解析、IC 計算）
- AI 関連モジュール（ニュース NLP によるセンチメント評価、レジーム検出）※OpenAI API を使用
- .env 対話式ウィザード（config_setup.py）と起動前の設定検証ツール（validate_config.py）
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

必要条件
--------
- Python 3.9+
- 推奨ライブラリ（用途に応じて）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の構文チェックを行う場合）
- 標準で利用する組み込み: sqlite3, logging, pathlib など

インストール（例）
-----------------
1. リポジトリをクローン:
   git clone <repo-url>
2. 仮想環境を作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（最低限の例）:
   pip install duckdb psutil
   # OpenAI 機能を使う場合:
   pip install openai
   # YAML バリデーションを有効にするなら:
   pip install pyyaml

環境変数 / .env
----------------
設定は .env ファイルまたは環境変数で行います。リポジトリルートに .env を置くと自動ロードされます（.env.local を併用可能）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（必須・代表）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI を使うモジュールで必要
- PAPER_FILL_MODE — paper_trading の約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（省略時 60）

.env 作成ウィザード
------------------
対話式ウィザードで .env を作るには:
  python -m kabusys.config_setup
ウィザードは既存 .env を読み込み、Enter で既存値を再利用できます。

設定検証
--------
起動前に設定を検証する:
  python -m kabusys.validate_config
警告も失敗扱いにする厳密モード:
  python -m kabusys.validate_config --strict

起動・使い方
------------

1) ExecutionEngine（発注エンジン）起動
- 標準起動:
  python -m kabusys.run_execution
- 動作:
  - Settings に従って SQLite/DuckDB に接続
  - paper_trading の場合は paper 用 DB を使用し MockBrokerClient を使う（本番と分離）
  - 実行中は pid ファイル（data/execution.pid）を作成
  - data/stop_requested.flag を検知すると安全に停止

2) Monitoring（監視）起動
- 標準起動:
  python -m kabusys.run_monitoring
- 挙動:
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - 監視結果を SQLite（monitoring.db）へ保存
  - KillSwitch 判定により条件成立時に data/kill.flag を書き込む（ExecutionEngine 停止トリガー）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

3) Paper Trading 検証レポート
- 日次集計・検証レポートを生成:
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- Paper Trading DB がデフォルト（data/paper_trading.db）にない場合は --db で指定、または環境変数 PAPER_TRADING_SQLITE_PATH を設定

4) AI 機能
- ニュース NLP（センチメント付与）:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要
- 市場レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要
（これらは DuckDB 接続を受け取り、DB 上のテーブルを参照・更新します）

停止フラグ / Kill Switch
-----------------------
- run_execution と run_monitoring は外部からの停止要求を以下のファイルで検知します:
  - data/stop_requested.flag — ループを優雅に終了するためのフラグ（手動作成で停止要求）
  - data/kill.flag — Kill Switch による ExecutionEngine 停止指示（監視側が書き込む）
- KillSwitch はリスク条件（ドローダウン、ポジション上限等）を満たすと kill.flag に理由を書き込みます。
- execution 起動時は pid ファイルが作成され、停止時に解放されます。

ログ
----
- 共通のログセットアップ機能 setup_logging が用意されています（logs/<app_name>.log に日次ローテーション）。
- ログ出力先は環境変数 LOG_DIR で変更可能。ファイル出力に失敗した場合はコンソール出力のみにフォールバックします。

データベースとマイグレーション
----------------------------
- 監視用テーブル群は monitoring_db.init_monitoring_db() で初回作成・必要なカラム追加（簡易マイグレーション）を行います。
- Paper Trading は別 SQLite ファイル（PAPER_TRADING_SQLITE_PATH）を使用するため、本番データと分離できます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数/設定管理（Settings クラス）
- config_setup.py                   — .env 対話式ウィザード
- validate_config.py                — 設定検証 CLI
- run_execution.py                  — ExecutionEngine 起動スクリプト
- run_monitoring.py                 — Monitoring 起動スクリプト

subpackages / modules:
- ai/
  - news_nlp.py                      — ニュース NLP（OpenAI 依存）
  - regime_detector.py               — レジーム判定（OpenAI 依存）
- monitoring/
  - monitoring_db.py                 — SQLite 永続化層（テーブル定義・CRUD ユーティリティ）
  - monitoring_engine.py             — 各 Monitor を束ねるエンジン
  - system_monitor.py                — CPU/メモリ/ディスク/データ鮮度監視
  - risk_monitor.py                  — ドローダウン・ポジション監視
  - kill_switch.py                   — kill.flag の生成/管理
  - (trade_monitor / alert_manager など 他ファイル)
- portfolio/
  - portfolio_builder.py             — 候補選定・重み計算
  - position_sizing.py               — 株数算出・リスク制御
  - risk_adjustment.py               — セクターキャップ・レジーム乗数
- research/
  - factor_research.py               — ファクター計算（momentum/value/volatility 等）
  - feature_exploration.py           — 将来リターン・IC・統計サマリ
- utils/
  - logging_setup.py                 — 共通ログ設定
  - process_priority.py              — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py     — Paper Trading 検証レポート生成

注意事項 / 運用上のポイント
----------------------------
- KABUSYS_ENV=live を設定する場合は特に注意してください（本番発注が行われます）。validate_config の警告を十分確認してください。
- .env は機密情報を含むため Git にコミットしないでください（config_setup はこの旨を注意喚起します）。
- AI モジュールは OpenAI API を呼び出します。API レート制限や料金に注意してください。API エラーはリトライ/フォールバック処理が組み込まれていますが、運用時はログの監視を推奨します。
- Paper Trading 用 DB を使えば発注ロジックや手数料処理の挙動検証が可能です。本番 DB とファイルを分離する設計になっています。

貢献・拡張
----------
- strategy / execution / broker クライアントは容易に差し替え可能な設計を目指しています。BrokerClientFactory を拡張して実運用ブローカーを追加できます。
- 研究用モジュールは DuckDB を用いた SQL ベースの処理なので、データ追加や新しいファクター導入が比較的容易です。

参考コマンドまとめ
------------------
- .env ウィザード:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
- Execution 起動:
  python -m kabusys.run_execution
- Monitoring 起動:
  python -m kabusys.run_monitoring
- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

以上。必要であれば README にサンプル .env テンプレートや systemd / Supervisor 用のサービス定義例、より詳細な運用手順（バックアップ、ログローテーション、監視ダッシュボード連携など）を追記できます。どの内容を追加したいか教えてください。