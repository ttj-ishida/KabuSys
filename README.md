KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内の主要スクリプト・モジュールの使い方とセットアップ手順を日本語でまとめたものです。

概要
----
KabuSys は日本株向けの自動売買システムの骨格実装です。主な機能は次のとおりです。

- 実行エンジン (ExecutionEngine)：発注・注文管理・リスク管理の実行ループ
- 監視 (Monitoring)：システム状態・発注ログ・リスクを定期チェックしてアラート／Kill Switch を制御
- ポートフォリオ構築：シグナルから候補選定・重み付け・株数決定までの純粋関数群
- リサーチ：DuckDB を使ったファクター計算・将来リターンや統計解析
- AI モジュール：ニュース記事を LLM（OpenAI）でスコアリングし、レジーム判定に利用
- ツール：ペーパートレード履歴の検証レポート生成など
- 設定管理：.env ウィザードと検証ツール

主な特徴
--------
- 環境分離：KABUSYS_ENV による運用モード（development / paper_trading / live）。paper_trading では MockBrokerClient を使い、専用の paper_trading.db に記録します。
- ロギング：統一的なログ設定（コンソール + 日次ローテートファイル）
- 監視/Kill Switch：監視モジュールがドローダウン等の閾値を検出すると data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
- DuckDB（分析用）と SQLite（監視・発注履歴）の併用
- AI（OpenAI）を使ったニュースセンチメント評価と市場レジーム判定（オプション）

セットアップ
-----------
前提
- Python 3.9+（コードは型アノテーションと標準モジュール API を使用）
- SQLite は標準ライブラリで利用可能
- 必要な外部パッケージ（最低）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config 検証で YAML を解析したい場合)

インストール例（仮想環境推奨）:
  python -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
  pip install --upgrade pip
  pip install duckdb psutil openai PyYAML

.env の作成
- リポジトリルートに .env を作成するか、対話式ウィザードで生成します：
  python -m kabusys.config_setup
- 重要な環境変数（主要なもの、デフォルト／説明）:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY — OpenAI を利用する場合に設定
  - LOG_LEVEL / LOG_DIR — ログ出力設定
  - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）

設定検証
- .env と config/*.yaml（存在する場合）の整合性をチェックする:
  python -m kabusys.validate_config
  --strict を付けると警告も失敗扱いになります。

使い方（起動とツール）
--------------------

1) 監視ループを起動
- 監視スクリプトは定期的に SystemMonitor を呼び出し system_status 等を記録します。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト: 60）。
  - 起動:
    python -m kabusys.run_monitoring

2) 実行エンジン（ExecutionEngine）を起動
- 発注／オーダー管理／リスク管理を行う主プロセスです。
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データベースは paper_trading 用に分離されます。
  - 起動例（ペーパートレード）:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
  - 起動例（本番）:
    export KABUSYS_ENV=live
    python -m kabusys.run_execution

3) .env の対話式作成
  python -m kabusys.config_setup

4) 設定検証（前述）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

5) Paper Trading 検証レポート生成
- ペーパートレード DB を解析して各種指標（稼働率、成功率、レイテンシ等）を出力します。
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

環境変数の挙動（抜粋）
- KABUSYS_ENV: development / paper_trading / live（無効な値はエラー）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject）
- LOG_DIR / LOG_LEVEL: ログ出力先・レベル
- OPENAI_API_KEY: AI 機能（news_nlp, regime_detector）を利用する際に必要

停止・Kill Switch
- 監視モジュール群および実行エンジンは data ディレクトリに置かれるフラグファイルで停止制御を行います。
  - data/stop_requested.flag: run_monitoring / run_execution のループを優雅に止めるためのフラグ（存在するとループ終了）
  - data/kill.flag: Kill Switch が発動したときに作成され、ExecutionEngine に停止シグナルを送る
- KillSwitch は閾値（ドローダウン、ポジション上限など）を超えた場合に data/kill.flag を書き込みます。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除します（本番では 0 を推奨）。

ログ・データベースの場所（デフォルト）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db
- ログ: logs/<app_name>.log（デフォルト日次ローテート）
- PID ファイル: data/execution.pid（run_execution で使用）

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数・設定管理（Settings）
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

subpackages
- ai/
  - news_nlp.py           — ニュースの LLM センチメント評価（ai_scores 生成）
  - regime_detector.py    — マクロ + ETF MA200 を組み合わせた市場レジーム判定
- monitoring/
  - monitoring_db.py      — SQLite のテーブル初期化 + 永続化 API
  - system_monitor.py     — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py      — (発注ログなどを監視するコンポーネント) ※実装の詳細参照
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - kill_switch.py        — Kill Switch 実装（flag ファイル操作）
  - monitoring_engine.py  — 各 Monitor を束ねる実行ループ
- execution/
  - execution_engine.py   — 実行エンジン本体（EngineConfig, run_session 等）
  - broker_factory.py     — BrokerClient の生成（本番/Mock 切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
- portfolio/
  - portfolio_builder.py   — 候補選定・重み付け
  - position_sizing.py     — 株数決定・スケーリング（lot 単位考慮）
  - risk_adjustment.py     — セクター上限・レジーム乗数
- research/
  - factor_research.py     — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py       — ロギング初期化ユーティリティ
  - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ

開発・運用に関する注意
---------------------
- 本リポジトリは実運用コード例を含みます。KABUSYS_ENV=live での実行は実際に発注を行います。設定値・API鍵を十分に確認してから実行してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup も README に警告を出力します）。
- AI 機能を有効にする場合、OPENAI_API_KEY を正しく設定し、API 利用料に注意してください。AI API が失敗した場合のフォールバック（多くの関数で 0.0 を使う等）がありますが、期待通りに動作するか事前確認してください。
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）はリサーチ／AI モジュールが前提とするため、適切なデータ投入が必要です。

トラブルシューティング
---------------------
- ログが出力されない場合は LOG_DIR のパス権限や環境変数 LOG_LEVEL を確認してください。logs/ ディレクトリは自動作成を試みますが、権限エラー時はコンソールのみ出力します。
- run_execution 起動後すぐ終了する場合: data/stop_requested.flag や data/kill.flag が存在していないか確認してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB に対してカラム追加（例: latency_ms, peak_value）を試みます。権限／ファイル破損時はエラーになります。

ライセンス・バージョン
--------------------
- パッケージ初期バージョン: 0.1.0（src/kabusys/__init__.py の __version__）

最後に
------
この README はコードベースの主要な使い方と構成を簡潔にまとめています。詳細な実装や追加設定は各モジュール（src/kabusys/以下の docstring やコメント）を参照してください。不明点があればどの機能について知りたいか指定していただければ、README を拡張します。