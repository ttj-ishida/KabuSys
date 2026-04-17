README — KabuSys（日本株自動売買システム）
====================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。
本リポジトリには以下の主要機能群が含まれます（監視、発注エンジン、ポートフォリオ構築、
ファクター計算、AI を用いたニュースセンチメント評価、ペーパートレード検証レポート等）。

主な特徴
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード（KABUSYS_ENV により分離）に対応
  - Paper Trading 時は MockBroker を使い専用 DB に記録
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム稼働監視、注文滞留・約定異常検出、リスク監視、Kill Switch
  - SQLite に監視ログ永続化（monitoring_db）
- Portfolio 構築ライブラリ
  - 候補選定、等重/スコア加重、ポジションサイズ算出、セクター制限、レジーム乗数
- Research（DuckDB ベース）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI）連携
  - ニュースの NLP によるセンチメント算出（gpt-4o-mini を想定）
  - 市場レジーム判定（MA + マクロセンチメント）
- ツール
  - ペーパートレード検証レポート生成スクリプト
  - .env 対話式セットアップ（config_setup.py）
  - 設定検証 CLI（validate_config.py）

前提・依存
-----------
主に標準ライブラリで実装されていますが、実行には以下が必要です（抜粋）:
- Python 3.9+
- duckdb (DuckDB Python)
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の構文チェックを行う場合に任意で必要）

pip でのインストール例:
- pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

3. .env の準備
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
       → J-Quants トークンや kabu API パスワード、DB パス等を対話で作成します。
   - あるいは .env を手動で作成（下の「環境変数」参照）。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. DB 初期化
   - monitoring 用の SQLite と DuckDB ファイルは起動時に必要に応じて作成されます。
   - run_execution / run_monitoring の起動で monitoring DB のテーブル作成（冪等）を行います。

環境変数（主なもの）
--------------------
（config_setup.py に定義されている項目と Settings クラスで参照するキー）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading 時の fill 動作: instant|partial|never|reject, デフォルト instant)
- KABUSYS_ENV (development | paper_trading | live, デフォルト development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト INFO)
- KILL_FLAG_CLEAR_ON_START (0|1, デフォルト 0)
- OPENAI_API_KEY (AI 機能を使用する場合に必須)

デフォルトパス
-------------
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID / フラグ類: data/execution.pid, data/kill.flag, data/stop_requested.flag

起動・使い方
------------

1) 監視プロセス（SystemMonitor）を起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60秒）。
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存しない）。
  - data/stop_requested.flag を作成すると監視ループが終了します。

2) 実行エンジン（ExecutionEngine）を起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い paper_sqlite_path（data/paper_trading.db）へ記録。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。stop は stop_requested.flag により検知します。

3) 設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告で exit(1) になります。

4) .env 対話式セットアップ
- python -m kabusys.config_setup

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db オプションや PAPER_TRADING_SQLITE_PATH 環境変数で DB ファイルを指定可能。

AI 関連（OpenAI）
-----------------
- OpenAI を使う機能:
  - kabusys.ai.news_nlp.score_news
  - kabusys.ai.regime_detector.score_regime
- 環境変数 OPENAI_API_KEY を設定してください（関数呼び出し時に api_key を渡すことも可）。
- 使用モデル: gpt-4o-mini（コード中で明示）
- API 呼び出しはリトライ・バックオフ・パース検証の仕組みを備えていますが、APIキー未設定時は例外になります。

停止・Kill Switch
-----------------
- KillSwitch（data/kill.flag）をファイルとして書き込むことで ExecutionEngine に停止指示を出します。
- monitoring はリスク条件（ドローダウンやポジション数超過など）を検出すると kill.flag を書き込むことがあります。
- run_* スクリプトは stop_requested.flag や execution.pid を使ってプロセス状態を管理します。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み / Settings
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor 起動スクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）
  - regime_detector.py      — 市場レジーム判定（OpenAI + MA）
- monitoring/
  - monitoring_db.py        — SQLite 永続化層
  - system_monitor.py       — システム監視（CPU/メモリ/データ鮮度等）
  - trade_monitor.py        — 注文滞留 / 約定異常検出
  - risk_monitor.py         — ドローダウン・ポジション監視
  - kill_switch.py          — kill.flag 書込みロジック
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - alert_manager.py        — （ファイル末尾に未表示の実装がある想定）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/ (前述)
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

サンプル .env（最低限）
----------------------
以下は .env の最小例（実際は secret 値を設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...

注意事項 / 運用メモ
-------------------
- KABUSYS_ENV によって本番 / ペーパートレードの挙動が切り替わります。paper_trading は発注を模擬し DB を分離します。
- 監視は monitoring DB（SQLite）へ書き込みます。run_monitoring は常に本番 sqlite_path を参照する実装です。
- OpenAI の API 呼び出しはコストが発生します。利用時は注意してください。
- .env は機密情報を含むため、決してバージョン管理にコミットしないでください。
- system の優先度変更や CPU affinity 設定は psutil を介して行われます。権限によっては設定に失敗することがあります（ログに警告が出ます）。

サポート・拡張
---------------
- config/*.yaml（system_config.yaml 等）は設定テンプレートとして生成/編集して利用する想定（generate_config.py のようなスクリプトで生成可能）。
- DuckDB 上の prices_daily / raw_financials / raw_news 等のテーブルを用いてファクターや AI 処理が動作します。
- Execution 実装（broker, engine, order_manager 等）は別モジュール群（execution パッケージ）を参照するため、そこを実装・調整して運用してください。

以上。必要であれば README に追加したいコマンド例や設定項目の詳細（各 env の意味、監視の閾値、ログ出力例など）を追記します。どの部分を詳述しますか？