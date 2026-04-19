README
======

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買フレームワーク（プロトタイプ）です。  
主な目的は、データ取得・ファクター計算・ポートフォリオ構築・発注（本番/ペーパー）・監視・アラート・簡易的な AI 補助（ニュースセンチメント／レジーム判定）を統合することです。  
このリポジトリには実行スクリプト、監視コンポーネント、ポートフォリオ構築ロジック、リサーチ用ユーティリティ、OpenAI を用いたニュース NLP モジュールなどが含まれます。

機能一覧
--------
- 環境設定ウィザード（.env の生成 / 更新）
- 起動前設定検証（設定漏れやパスの警告）
- ExecutionEngine（発注エンジン）:
  - KABUSYS_ENV に応じて本番／ペーパートレード切替（paper_trading では MockBrokerClient を使用）
  - 発注管理、リスク管理、リコンシリエーション等のオーケストレーション
- Monitoring（監視）:
  - システム状態（CPU/メモリ/ディスク）の定期記録
  - 発注ログ / ポジション / リスクログの永続化（SQLite）
  - Kill Switch（ドローダウンやポジション上限検出時に Execution を停止するフラグ）
  - アラート連携のフック（LINE 等）
- ポートフォリオ構築モジュール（純粋関数群）:
  - 候補選定、重み計算、セクター制約、ポジションサイジング（単元株丸め含む）
- リサーチ／ファクター計算（DuckDB を用いる）:
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン、IC 計算、統計サマリ
- AI ツール（OpenAI）:
  - ニュース記事のセンチメント評価（ai_scores への書き込み）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定
- ツール:
  - Paper Trading 検証レポート生成スクリプト（期間指定可）
- 共通ユーティリティ:
  - 統一ログ設定（コンソール + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定

必要条件（ざっくり）
-------------------
- Python 3.10 以上（コード内での型ヒントに | 演算子等を使用）
- 推奨 Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（validate_config が YAML の検証を行う場合に任意で使用）
- SQLite（組み込み）、ファイル書き込み権限

インストール（例）
-----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（requirements.txt があればそれを使用）
   - pip install duckdb psutil openai pyyaml
   - または: pip install -r requirements.txt

セットアップ手順
----------------
1. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参照）
   - 自動ロード: config モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

2. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 必須項目やファイルパスの警告・エラーを確認できます
   - --strict を付けると警告も失敗（exit(1)）扱いになります

3. データディレクトリ / ログディレクトリ
   - デフォルトで data/ と logs/ を使用します。必要であれば .env で以下を上書きしてください:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパー時の DB、デフォルト: data/paper_trading.db）
     - LOG_DIR（デフォルト: logs/）

4. OpenAI を使う機能を利用する場合:
   - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡してください。

環境変数（主なもの）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルト:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知の設定（任意）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリア（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — ペーパートレードの約定動作（instant / partial / never / reject、デフォルト: instant）

使い方（主要コマンド）
--------------------
- 環境設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動:
  - 本番（注意して使用）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（MockBroker を使用、専用 DB に書き込まれる）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行前に data/kill.flag をクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると自動クリアできます（本番では推奨しません）。

- Monitoring を起動:
  - MONITOR_POLL_INTERVAL を秒数で上書き可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視ループは data/stop_requested.flag の存在で終了します（停止制御用）。run_execution/run_monitoring ともにこのファイルの存在をチェックします。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- ライブラリ的に利用する:
  - research や ai モジュールは DuckDB 接続を渡して関数を呼び出す形です（例: kabusys.research.calc_momentum、kabusys.ai.score_news）。

停止 / Kill Switch
-----------------
- KillSwitch は条件（ドローダウン超過・ポジション上限等）で data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（Execution 側は Settings.kill_flag_path を参照して停止します）。
- 開発や手動停止には data/stop_requested.flag が使われます。run_* スクリプトはこのファイルが存在するとループを終了します。

ログ
---
- デフォルトで logs/<app_name>.log に日次ローテーション（30 日保管）で出力されます（setup_logging 使用）。
- コンソール出力は stdout へ行われます。

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内 src/kabusys 以下の主要ファイル・パッケージの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレードの検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（system_status 等）
    - system_monitor.py             — システム / データ鮮度監視
    - trade_monitor.py              — （発注関連監視）※詳細は同ディレクトリ参照
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - kill_switch.py                — kill.flag 制御
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
    - alert_manager.py              — （アラート送信ハンドラ）
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 株数決定・リスク制限
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py            — ファクター計算（momentum / value / volatility）
    - feature_exploration.py        — IC / 将来リターン / 統計
    - __init__.py
  - utils/
    - logging_setup.py              — ログ初期化ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity
    - __init__.py
  - monitoring/monitoring_db.py     — 監視 DB 初期化 / Access 層

補足・運用上の注意
-----------------
- KABUSYS_ENV=live の設定は本番運用に直結します。LINE 通知や kill flag の挙動を必ず事前確認してください。
- .env は機密情報（API キー等）を含むため Git 等にコミットしないでください。
- OpenAI を使う処理は API 呼び出しやレート制限に関する再試行ロジックを含みますが、コストやレイテンシ面を十分考慮して運用してください。
- ペーパートレードは本番 DB と分離されるため、安全に検証できます（PAPER_TRADING_SQLITE_PATH を使用）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（参照用）。

問い合わせ / 開発
------------------
- コードを拡張する場合は、まず config_setup と validate_config で動作確認を行ってください。  
- テストや CI の整備、requirements.txt / packaging の追加を推奨します。

以上。必要があれば各モジュールの詳細ドキュメントや実行例（system_monitor.check_once の戻り値、ExecutionEngine のパラメータなど）を追記します。