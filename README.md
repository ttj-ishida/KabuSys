README
=====

本ドキュメントは、KabuSys（日本株自動売買システム）のコードベースの概要、セットアップ、起動方法、各種ユーティリティの使い方、ディレクトリ構成をまとめた README です。

プロジェクト概要
----------------
KabuSys は日本株を対象とした自動売買 / リサーチ基盤です。主な役割は以下の通りです。
- 注文実行エンジン（ExecutionEngine） — 発注、リスク管理、約定の管理
- 監視（Monitoring） — システム稼働、注文滞留、ドローダウンなどの監視と Kill Switch（停止信号）
- ポートフォリオ構築ロジック — 候補選定・重み付け・株数計算・セクター制限
- リサーチ（ファクター計算、特徴量解析）
- AI 支援モジュール — ニュースの NLP スコアリング、レジーム判定（OpenAI を使用）
- 運用ツール — ペーパートレード検証レポート生成など

特徴 / 機能一覧
---------------
- 実行環境切替（KABUSYS_ENV=development / paper_trading / live）
  - paper_trading 時は MockBrokerClient を使い、専用 DB（data/paper_trading.db）に記録
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch 機能
- Logging 設定ユーティリティ（コンソール + 日次ローテートファイル出力）
- DuckDB を使ったデータ分析・ファクター計算
- OpenAI (gpt-4o-mini 等) を利用したニュースセンチメントおよび市場レジーム判定
- 簡易的な .env ウィザードおよび設定検証 CLI
- Paper Trading 向けの検証レポート生成スクリプト

必要な依存関係（主なもの）
-------------------------
必須:
- Python 3.9+（コード内の型注釈や API 使用を前提）
- duckdb
- psutil
- openai（AI 機能を使う場合）
任意 / 推奨:
- PyYAML（config/*.yaml の構文検証に使用）
- SQLite（標準ライブラリの sqlite3 を使用）
インストール例:
    pip install duckdb psutil openai pyyaml

環境変数（主要）
----------------
必須（最低限動かすには設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用関連（デフォルト値あり）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 用）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

ファイルベースの制御:
- data/stop_requested.flag — run_monitoring / run_execution が存在を見て動作停止を行うためのフラグ
- data/kill.flag — KillSwitch が作成する停止シグナル（ExecutionEngine 停止用）
- data/execution.pid — ExecutionEngine の PID 保存（デフォルトパスは Settings.pid_file_path）

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動
2. 依存パッケージをインストール
   - 例: pip install -r requirements.txt （存在する場合）
   - または個別に: pip install duckdb psutil openai pyyaml
3. .env ファイルの作成（例）
   - 対話式ウィザード:
       python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参考に必要変数を設定
4. 設定検証:
       python -m kabusys.validate_config
   - --strict を付けると警告も FAIL として扱う
5. データディレクトリ作成（必要なら）:
       mkdir -p data logs

起動・使い方
------------

基本コマンド（パッケージモードで実行）
- 監視ループ起動（Monitoring）
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用（環境に依存せず本番 DB を参照）
  - 停止方法: data/stop_requested.flag を作成すると監視ループが検知して終了

- 実行エンジン起動（Execution）
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込む
  - 起動前に data/stop_requested.flag が既にある場合は起動をスキップ
  - 実行中は data/execution.pid に PID を書き込み、data/stop_requested.flag を置くことで停止可能
  - 実行中の優先度は自動で "high" に設定されます（プラットフォーム依存）

- .env ウィザード（対話形式で .env を作成）
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB 指定可能

AI 関連
- ニュース NLP / レジーム判定機能は OPENAI_API_KEY を必要とします（関数単位で api_key 引数から渡すことも可能）
- AI 呼び出しは失敗時にフェイルセーフ（0 相当）で継続する設計です

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日保持）
- setup_logging() によりコンソール（stdout）とファイルの両方に出力されます

停止 / Kill Switch
- KillSwitch によって data/kill.flag が書かれると ExecutionEngine 側で停止トリガーになります（KillSwitch はリスク監視から生成）
- 開発時に監視/実行を素早く停止したい場合は data/stop_requested.flag を作成します（両スクリプトが検知して終了）

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・設定管理（.env 自動ロードロジック含む）
- config_setup.py          — .env ウィザード（対話式）
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリングループ起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）で ai_scores を生成
  - regime_detector.py     — マーケットレジーム判定（MA + マクロ NLP）
- monitoring/
  - monitoring_db.py       — SQLite ベースの永続化（テーブル作成・Upsert 等）
  - system_monitor.py      — システム稼働・データ鮮度監視
  - trade_monitor.py       — 注文関連の監視（ファイルは存在）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — KillSwitch（flag 書き込み）
  - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
  - alert_manager.py       — アラート送信（ファイルの存在を想定）
- execution/
  - 複数の実行関連モジュール（Engine・BrokerFactory・OrderManager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py     — モメンタム / ボラティリティ / バリュー 等
  - feature_exploration.py — IC / 将来リターン / 統計サマリー
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

設定ファイル（外部）
- config/*.yaml            — system_config.yaml 等（validator が存在チェックおよび YAML パース検証を行う）

マイグレーション / データベース
- monitoring_db.init_monitoring_db() は起動時に必要なテーブルとインデックスを冪等に作成します。既存 DB に対する小さなスキーマ追加（カラム追加）も含まれています。

注意事項 / FAQ
----------------
- 本番運用時は KABUSYS_ENV=live を設定してください。validate_config が live 時の追加ガードを出力します（LINE 通知等）。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup でも注意書きを出力します）。
- OpenAI を使う処理は API レートやエラーに対してリトライ・バックオフの仕組みを備えていますが、コストに注意してください。
- monitoring は Settings.sqlite_path（監視 DB）を常に参照します。paper_trading 環境でも監視 DB は本番用パスを使う設計になっています（Execution は paper_trading 時に専用 DB を使用）。

開発・貢献
----------
- 新しい設定項目を追加した場合は config_setup.py と validate_config.py を更新してください。
- データベーススキーマを変更する際は monitoring_db.init_monitoring_db() にマイグレーションを追加してください（既存 DB に対して冪等で動作すること）。
- AI モジュールのテストを行う場合は API 呼び出し部分（_call_openai_api 等）をモックする設計になっています。

以上。必要に応じて README に具体的なコマンドや .env のサンプルを追加しますので、追記が必要な箇所（例: CI 用の起動手順、Dockerfile、systemd ユニット例 など）を教えてください。