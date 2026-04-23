KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を想定した軽量なフレームワークです。  
主に以下を目的とします:

- シグナルに基づく発注フロー（ExecutionEngine）
- 注文状態管理（OrderRecord / OrderRepository / OrderManager）
- ブローカー抽象化（MockBroker / KabuStation クライアント）
- 起動前の環境設定ウィザードと検証ツール（.env 作成・検証）
- 監視ポーリング（SystemMonitor）・簡易監視 DB（SQLite）
- マーケットカレンダー管理やニュース収集などのデータ周辺処理

重要な設計方針
- ビジネスロジック（OrderRecord 等）は DB 操作と分離されるよう実装。
- 発注フローはクラッシュ耐性を考慮した 2 段階永続化を採用。
- paper_trading 環境用に MockBrokerClient を提供し、本番 DB と分離する設計。

主な機能一覧
----------------
- 環境設定ウィザード: python -m kabusys.config_setup により .env を対話式で作成
- 設定検証 CLI: python -m kabusys.validate_config で .env と config/*.yaml のチェック
- 実行エンジン: ExecutionEngine によるシグナル読み取り → 発注（8:50–15:30 のセッションモデル）
- 注文管理: OrderRecord（状態遷移）、OrderRepository（SQLite 永続化）、OrderManager（送信/同期/取消）
- ブローカー抽象化: BrokerAPIProtocol（KabuStationClient / MockBrokerClient）
- リスク管理: RiskManager（Gate1/2/3 — シグナル・実行・ドローダウン）
- リコンシリエーション: 再起動時に OrderSent を broker と突合して状態回復
- 監視プロセス: run_monitoring.py による定期チェック（監視 DB は SQLite）
- データ処理: calendar_management（営業日管理）, news_collector（RSS 収集）

セットアップ手順
----------------
前提
- Python 3.9+ を推奨（typing の記法に依存）
- システムに sqlite3 が利用可能であること（標準ライブラリ）
- DuckDB を利用するため duckdb パッケージが必要

推奨インストールパッケージ（代表例）
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config/*.yaml のパース検証を行う場合）
実プロジェクトでは requirements.txt を用意して pip install -r する想定ですが、以下のように個別インストールできます:

例:
- pip install duckdb httpx websocket-client defusedxml PyYAML

リポジトリ取得（例）
- git clone <repo-url>
- cd <repo-root>

.env の作成
1. 対話式ウィザードで作成:
   - python -m kabusys.config_setup
   - 対話終了後、.env がプロジェクトルートに保存されます。

2. 手動で作る場合は .env.example 相当を参考に作成（必須環境変数は下記参照）。

必須 / 推奨環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- オプション（よく使うもの）:
  - KABUSYS_ENV  (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH  (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH  (監視 DB; デフォルト: data/monitoring.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - KABU_API_BASE_URL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
- その他:
  - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動でクリアする、テスト用）
  - PAPER_FILL_MODE（paper_trading の MockBroker 動作: instant|partial|never|reject）

.env の最小例
（JQUANTS と KABU のパスワードは必ず設定してください）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

DB の初期化
- 監視用 SQLite DB の初期化は run_monitoring.py / run_execution.py 内で init_monitoring_db を呼んでおり、
  最低限のテーブルは自動で作成されます。
- orders テーブルの作成ヘルパー: kabusys.execution.init_orders_db（必要に応じて呼び出して準備してください）。
  例: python -c "import sqlite3; from kabusys.execution import init_orders_db; conn=sqlite3.connect('data/monitoring.db'); init_orders_db(conn); conn.close()"

使い方（コマンド）
----------------
1) 設定ウィザード（.env 作成 / 更新）
- python -m kabusys.config_setup
  - 対話形式で各種環境変数を入力し .env を生成します。

2) 設定検証
- python -m kabusys.validate_config
  - .env の必須変数や config/*.yaml の存在/パースをチェックします。
- 厳格モード（警告も失敗扱い）:
  - python -m kabusys.validate_config --strict

3) 実行エンジン起動（本番/ペーパートレード）
- python -m kabusys.run_execution
  - KABUSYS_ENV に応じて MockBroker（paper_trading / development）または本番クライアントを使います。
  - paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にデータを記録します。
  - stop リクエストはプロジェクトルート/data/stop_requested.flag を作成することで行います。

4) 監視プロセス起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視は常に sqlite_path（本番の監視 DB）を使います。

停止・kill フラグ
- 実行プロセスを安全に停止したい場合:
  - プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。
- kill.switch（致命的なドローダウン等で全注文キャンセル）:
  - settings.kill_flag_path に対応するファイル（デフォルト data/kill.flag）を用いる設計です。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると、起動時に既存の kill.flag を自動でクリアします（開発用。実運用では 0 推奨）。

注意事項
- KABUSYS_ENV=live は設計上の想定値ですが、現在 Broker の Live クライアントは未実装で NotImplementedError を投げます。運用時は paper_trading / development を使用してください。
- config/*.yaml を用いる構成（system_config.yaml 等）があり、PyYAML がインストールされていると検証時に内容のパースも行われます。インストールがない場合は検証で YAML 内容検査をスキップします。
- .env は絶対にリポジトリにコミットしないでください（README 内のテンプレートや例は公開用にトークン等を含めないこと）。

主要ディレクトリ構成
--------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み・Settings（自動 .env ロードロジック含む）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前の設定検証 CLI
- run_execution.py         — ExecutionEngine を起動するスクリプト
- run_monitoring.py        — SystemMonitor をポーリング起動するスクリプト

src/kabusys/execution/
- __init__.py
- broker_api.py            — BrokerAPIProtocol, データモデル, 例外, ファクトリ
- broker_factory.py        — Settings に応じた Broker クライアント生成
- kabu_client.py           — kabuステーション用 HTTP / WebSocket クライアント
- mock_client.py           — テスト・開発用 MockBrokerClient
- order_record.py          — 注文状態遷移ロジック（純粋なビジネスルール）
- order_repository.py      — SQLite を用いた永続化層
- order_manager.py         — 発注フローを実行する上位 API（create/send/sync/cancel）
- execution_engine.py      — 実際のセッション実行ロジック（シグナル処理・push ドレイン）
- reconciler.py            — 起動時のリコンシリエーション（OrderSent の突合）
- risk_manager.py          — Gate1/2/3 によるリスクチェック（rate limit, cb, drawdown）

src/kabusys/data/
- calendar_management.py   — マーケットカレンダー管理（営業日 / next/prev / calendar update job）
- news_collector.py        — RSS ニュース収集（SSRF/XML 脆弱性対策考慮）
- ... (jquants_client など、外部 API ラッパーを想定)

src/kabusys/monitoring/
- monitoring_db.py         — 監視 DB 初期化とログ関数（run_monitoring.py で利用）
- system_monitor.py        — システム監視ロジック（CPU/メモリ/ディスク 等）

src/kabusys/utils/
- logging_setup.py         — ログ設定ユーティリティ
- process_priority.py      — プロセス優先度設定ユーティリティ

開発者向けメモ
- 各モジュールは DB 操作とビジネスロジックを分離する方針で書かれています。単体テストはビジネスロジック（OrderRecord / RiskManager / Reconciler 等）を Mock Broker や in-memory DB で検証するのが容易です。
- ExecutionEngine はセッション時間の概念（signal_send_start/signal_send_end/market_close）を持ち、テスト時は _process_signals() / _drain_push_queue() を直接呼び出すことで制御しやすく実装されています。
- 発注トランザクションにおけるクラッシュ時の回復設計（OrderSent を残す / broker_order_id の早期永続化）は Reconciler により起動時に回復されます。

サポートや拡張
- Live ブローカーの実装（KabuStationClient の本番向け調整や認証周りの追加）は今後の拡張です。
- 既存の MockBrokerClient を元に自動テストの追加、監視ルールの拡張、通知チャネル（LINE など）の拡張が容易に行えます。

ライセンス
- 本 README はコードベースの説明を目的としたもので、実際のリポジトリの LICENSE を参照してください。

以上。必要であれば README に含める .env の完全なテンプレートや、よくあるトラブルシュート（よくあるエラーと対処法）を追加できます。どの程度詳細に追記しますか？