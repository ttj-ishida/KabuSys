README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算・リサーチ、ポートフォリオ構築、AI ベースのニュース判定などのコンポーネント群を含みます。設計は本番環境とペーパートレードを区別しており、設定は .env で管理します。

主な特徴
--------
- ExecutionEngine と Monitoring の起動スクリプト（run_execution.py, run_monitoring.py）
- Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し、本番 DB と分離（デフォルト: data/paper_trading.db）
- 監視用 SQLite（デフォルト: data/monitoring.db）と分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- モジュール化されたポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- ファクター計算（モメンタム/バリュー/ボラティリティ）および研究用ユーティリティ（IC 計算など）
- AI モジュール（ニュースのセンチメント評価、レジーム判定）— OpenAI API（例: gpt-4o-mini）を利用
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）および Kill Switch（data/kill.flag）による安全停止メカニズム
- ログ設定ユーティリティ（stdout + 日次ローテートファイル）

必須・推奨依存ライブラリ
-----------------------
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config 検証で YAML 構成を検証する場合）
（インストール例）
pip install duckdb psutil openai pyyaml

セットアップ手順
----------------

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .\.venv\Scripts\activate   # Windows

3. 依存パッケージをインストール
   pip install duckdb psutil openai pyyaml

4. .env の作成（対話式ウィザード）
   python -m kabusys.config_setup
   ウィザードは .env を生成/更新します。J-Quants のリフレッシュトークンや kabuAPI パスワードなどは必須です。

5. 設定検証
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

6. データディレクトリとログディレクトリ
   デフォルトでは以下ファイル/ディレクトリを利用します。必要に応じて .env でパスを変更してください。
   - SQLite（監視）: data/monitoring.db
   - Paper Trading DB: data/paper_trading.db
   - DuckDB（分析）: data/kabusys.duckdb
   - ログ: logs/<app_name>.log
   - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

基本的な使い方
--------------

環境変数の例（.env）:
- KABUSYS_ENV=development|paper_trading|live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- OPENAI_API_KEY=（AI 機能を使う場合）

主要スクリプト
1) ExecutionEngine を起動（通常はサービスとして実行）
   python -m kabusys.run_execution

   動作ポイント:
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録します。
   - 起動時に data/stop_requested.flag が存在する場合は起動しません。
   - 停止は data/stop_requested.flag を作成するか（run_execution が検知して engine.stop() を呼ぶ）、kill.flag による停止を評価します。

2) Monitoring を起動（監視ループ）
   python -m kabusys.run_monitoring

   動作ポイント:
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60）。
   - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV にかかわらず）。
   - 停止: data/stop_requested.flag を配置すると監視ループが終了します。

3) 設定・運用系ツール
   - 環境設定ウィザード:
     python -m kabusys.config_setup
   - 設定検証:
     python -m kabusys.validate_config [--strict]
   - Paper Trading 検証レポート:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     オプション --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH と併用）

AI 機能の利用
- kabusys.ai.score_news(conn, target_date, api_key=None)
  DuckDB 接続と日付を与えると raw_news からニュースを集約して OpenAI に送信し、ai_scores テーブルへ保存します。
  OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定します。

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  ETF（1321）とマクロニュースを組み合わせて市場レジームを判定し、market_regime テーブルに書き込みます。

注意点 / オペレーション
------------------------
- Kill Switch:
  - KillSwitch は RiskMonitor の検出結果（ドローダウン超過など）に応じて data/kill.flag を書き込み、ExecutionEngine にシステム停止を促します。
  - .env の KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では推奨されません。

- stop_requested.flag:
  - run_execution.py / run_monitoring.py は data/stop_requested.flag を監視して安全にシャットダウンします。管理者はこのファイルを作成して停止を指示できます。

- ロギング:
  - setup_logging() により標準出力（stdout）と logs/<app_name>.log（日次ローテート、30日保持）に出力します。
  - ログディレクトリは LOG_DIR 環境変数またはデフォルトの logs/ を使用します。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db はテーブル作成や既存 DB に対する冪等なマイグレーション処理を行います（例: dashboard.peak_value 列追加、trade_logs.latency_ms 列追加）。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前の設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py  — Paper Trading 検証レポート生成
- ai/
  - __init__.py
  - news_nlp.py             — ニュースセンチメント（OpenAI 呼び出し）
  - regime_detector.py      — 市場レジーム判定（OpenAI 呼び出し）
- monitoring/
  - monitoring_db.py        — 監視用 SQLite 永続化レイヤ
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py        — （省略されたが取引監視ロジックが想定される）
  - risk_monitor.py         — ドローダウン/ポジション上限監視
  - kill_switch.py          — kill.flag 書き込み/評価
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - alert_manager.py        — （アラート送信ロジック、ファイルに含まれる想定）
- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- data/
  - pipeline.py             — prices_daily などを扱う想定（モジュール参照あり）
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度/CPU affinity 設定

開発者向けメモ
---------------
- 自動 .env ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml）を自動検出し、.env/.env.local を読み込みます。テスト時などに自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テストしやすさ:
  - OpenAI 呼び出し箇所は内部で _call_openai_api 等の関数に切り出しており、unittest.mock.patch で差し替えてテスト可能です。
- ログと例外:
  - 各起動スクリプトは setup_logging() を最初に呼び出し、set_process_priority("high") によって優先度設定を試みます（psutil のアクセス権により失敗する場合はログに警告を出します）。

よくある運用コマンド例
--------------------
# .env の対話式生成
python -m kabusys.config_setup

# 設定検証
python -m kabusys.validate_config

# ペーパートレード検証レポート（期間指定）
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# Execution 起動（バックグラウンド / supervisor 等で管理推奨）
python -m kabusys.run_execution &

# Monitoring 起動
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring &

ライセンス・貢献
----------------
（ここにライセンス、貢献方法、連絡先などを記載してください）

補足
----
この README はソースコードの注釈と設計意図に基づいて作成しています。実行環境や運用フローに合わせて .env の設定やデータベースパス、ログ保存先などを適切に調整してください。