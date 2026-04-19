README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。  
主な目的は次のとおりです。

- 戦略・ファクター計算（DuckDB ベースのリサーチ）
- ポートフォリオ構築・ポジションサイジング（純粋関数実装）
- 発注エンジン（実運用／ペーパートレードの切替対応）
- 監視・アラート・Kill Switch（稼働監視・リスク監視）
- ニュース NLP を使った AI スコアリング（OpenAI 経由）
- ペーパートレード検証レポート生成ツール

重要: KABUSYS_ENV=live を設定すると実際の発注が行われます。本番運用前に .env を十分に確認してください。

主な機能
--------
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証ツール（python -m kabusys.validate_config）
- ExecutionEngine（実際の発注実行 / paper_trading 時は MockBroker）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor と KillSwitch）
- AI モジュール（ニュースセンチメント → ai_scores、レジーム判定）
- Research モジュール（モメンタム・ボラティリティ・バリュー等の計算）
- Portfolio モジュール（候補選定、重み付け、ポジションサイズ計算）
- ペーパートレード検証レポート（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------

1. Python 環境を用意する（推奨: 仮想環境）
   - python 3.10+ を想定

2. 依存パッケージをインストールする
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (validate_config の YAML 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

3. プロジェクトルートに移動し、.env を作成する
   - 対話式で作成する:
     - python -m kabusys.config_setup
   - 重要な環境変数（最低限必要なもの）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を利用する場合）
   - .env は絶対に Git にコミットしないでください。

4. 設定検証を実行する
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります。

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ と logs/ を使用します。起動時に自動作成される場合もありますが、権限等を事前に確認してください。

使い方（起動 / 主なコマンド）
----------------------------

- 実行エンジンを起動（実運用／ペーパートレード判定は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution

  挙動メモ:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に操作履歴を記録します（本番 DB とは分離）。
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します。
  - エンジンは実行中に stop を受けると graceful shutdown します。停止は data/stop_requested.flag を作ることでできます。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring

  挙動メモ:
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒単位）。
  - 監視プロセスは本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを永続化します。
  - 停止は同じく data/stop_requested.flag を作成すると検知して終了します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使うこともできます。

停止・Kill Switch
-----------------
- ExecutionEngine を外部から停止させたい場合:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring が検知して停止します。
- Kill Switch（自動停止）:
  - RiskMonitor 等が条件を満たすと data/kill.flag を作成します。これが存在すると明示的なサインとして取り扱われます。
  - 設定により起動時に kill.flag を自動クリアできる KILL_FLAG_CLEAR_ON_START（デフォルト 0）。本番では 0 を推奨。

環境変数（主要）
-----------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- OPENAI_API_KEY — AI 機能用
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings 参照）

ログ
----
- ログはデフォルトで logs/ に出力されます（kabusys.utils.logging_setup.setup_logging）。
- 各アプリケーション別に logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）に日次ローテーションで保存されます。
- LOG_DIR 環境変数や setup_logging の引数で変更できます。

ディレクトリ構成
----------------
（src/kabusys 以下をベースに抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注エンジン関連（BrokerFactory, ExecutionEngine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 操作（テーブル初期化・読み書き）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 注文監視（滞留・約定異常 等）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch ロジック（kill.flag 書き込み）
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       —（アラート送信ロジック）
  - portfolio/               — ポートフォリオ構築（builder / risk_adjustment / position_sizing）
  - research/                — ファクター計算・特徴量解析（DuckDB ベース）
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — マーケットレジーム判定（AI + MA200）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

設計上のポイント / 注意事項
---------------------------
- 設定の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 本番環境注意:
  - KABUSYS_ENV=live の場合は実際に発注が行われます。validate_config で警告が出る項目（LINE 通知設定未設定など）をよく確認してください。
- AI（OpenAI）機能:
  - OPENAI_API_KEY が必要。API のリトライやエラーハンドリングを備えていますが、API 利用時のコスト・レイテンシに注意してください。
- DB の分離:
  - Monitoring 用 SQLite（SQLITE_PATH）と Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）は分離されます。paper_trading モード時は専用 DB を使用します。
- ローカル実行:
  - 開発時は KABUSYS_ENV=development を使用すると実際の発注処理が無効化される挙動（実装による）を保つ設計になっています。必ず設定を確認してください。

追加情報 / トラブルシューティング
---------------------------------
- validate_config を実行して不足項目や怪しい設定がないか確認してください。
- ログディレクトリ作成に失敗するとコンソール出力のみになります。パーミッションやマウントポイントを確認してください。
- psutil による優先度設定や CPU affinity は OS と権限に依存します。AccessDenied 等の警告が出ることがありますが、処理は継続されます。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__（現状 "0.1.0"）を参照してください。

問い合わせ
----------
不具合報告・機能追加希望等はリポジトリの issue に記載してください。README に不明点があればここで追記できます。