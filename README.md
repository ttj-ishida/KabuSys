# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買を目的とした軽量なフレームワークです。本リポジトリには設定管理・検証、発注エンジン、ブローカー抽象化、リスクガード、監視ループ、データ関連ユーティリティ（カレンダー・ニュース収集）などの主要コンポーネントが含まれます。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方
- 環境変数一覧（主要）
- ディレクトリ構成

---

プロジェクト概要
- 日本株自動売買システムのコア部分を提供するライブラリ兼実行スクリプト群。
- 設定は .env ファイル（または環境変数）で管理。対話式ウィザードで .env を作成可能。
- 本番（live） / ペーパートレード（paper_trading） / 開発（development）を区別して動作。
- 実際のブローカー接続実装（kabuステーション）およびテスト用のモック実装を持つ。

---

主な機能
- .env 対話式ウィザード（kabusys.config_setup）
  - .env の初期作成・更新を対話的に支援。
- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml の存在・基本整合性を起動前に検査。--strict モードあり。
- 実行エンジン（kabusys.run_execution / ExecutionEngine）
  - シグナル読み取り → リスクチェック（Gate1/2） → 発注 → push ドレイン → Gate3（ドローダウン）を組み合わせた一日セッション実行。
  - Paper trading / development では MockBrokerClient を使用。
- 監視ループ（kabusys.run_monitoring / SystemMonitor 単位）
  - システムメトリクスや監視イベントをポーリングして監視データベースへ記録。
- ブローカー抽象化（kabusys.execution.broker_api）
  - BrokerAPIProtocol によるインターフェース、KabuStationClient（実環境）および MockBrokerClient（テスト用）。
- 注文永続化・状態管理（OrderRepository / OrderRecord / OrderManager）
  - SQLite に注文を保存し、状態遷移や再同期（Reconciler）機能を持つ。
- リスク管理（RiskManager）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューションレベル（レート制限・サーキットブレーカー）
  - Gate3: メトリクス（ドローダウン）監視
- データユーティリティ
  - calendar_management: J-Quants ベースのマーケットカレンダー管理
  - news_collector: RSS ベースのニュース収集（SSRF対策・正規化・前処理等）

---

セットアップ手順（ローカル開発向け）
1. Python（3.10 以上推奨）環境を用意
   - 型注釈で Path | None 等を使用しているため Python 3.10+ を想定しています。

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージのインストール（最低限）
   - pip install duckdb httpx websocket-client defusedxml PyYAML
   - 追加で logging 周りや sqlite3 は標準ライブラリで提供されます。
   - 実運用では requirements.txt を用意している場合はそれを使ってください。

4. .env ファイルの作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
     - デフォルトはプロジェクトルートの .env を作成します（--env-file でパス指定可）。
   - もしくは手動で .env を作成（例は下記参照）。

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict を付与:
     - python -m kabusys.validate_config --strict

6. 実行スクリプトの起動
   - 発注エンジン（Execution）を起動:
     - python -m kabusys.run_execution
   - 監視ループを起動:
     - python -m kabusys.run_monitoring

注意:
- 自動で .env を読み込む仕組みがあり（プロジェクトルートの .env → .env.local の順）、OS 環境変数が優先されます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 実行時に DB（DuckDB / SQLite）や監視用のテーブルは必要に応じて初期化メソッドを呼び出すことで作成されます（スクリプト実行中に初期化される場合あり）。

---

主要な環境変数（必須 / 任意）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意（代表）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード実行時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用アクセストークン（任意）
- LINE_USER_ID — LINE 通知先ユーザーID（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

PAPER_FILL_MODE（paper_trading 用）:
- instant / partial / never / reject（デフォルト: instant）
  - instant: 発注即時約定（全量）
  - partial: 一部約定（デフォルトで半量）
  - never: 注文は保留（OrderSentPendingError を発生）
  - reject: 発注拒否（OrderRejectedError）

サンプル .env（最低限）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

※ .env は絶対に Git にコミットしないでください。config_setup も同様に警告を表示します。

---

使い方（主要コマンド）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - オプション: --env-file PATH で保存先を指定

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code=1）

- 発注エンジン（1日セッションを実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて MockBrokerClient（paper_trading / development） または本番クライアントを使用
  - 停止制御: プロジェクトルートの data/stop_requested.flag を作成するとループは停止します
  - PID は data/execution.pid（デフォルト）に書き出されます

- 監視ループ（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定（秒、デフォルト 60）
  - 監視は設定にかかわらず本番 sqlite_path を使用します（監視用 DB の分離に注意）

---

設計上の注意点 / 運用メモ
- OrderManager の send_order は二相的永続化を行うことでクラッシュ・再起動時に整合性を保つように設計されています（OrderSent 状態の検出と Reconciler による復旧）。
- Reconciler は起動時に OrderSent の注文をブローカーと突合して自動で同期し、ポジション差分を検出します。
- kill.flag（設定で指定されたファイル）により外部からの全停止（kill switch）を実装しています。KILL_FLAG_CLEAR_ON_START=1 を本番で有効にすることは危険です（デフォルト 0 を推奨）。
- run_monitoring は監視専用 DB（sqlite）を使うため、監視データは運用環境での DB 設定に注意してください。
- YAML の検証は PyYAML がインストールされている場合のみ行われます（validate_config が警告を出します）。

---

ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py — パッケージ定義（__version__）
- config.py — 環境変数読み込み / Settings クラス（アプリ設定）
- config_setup.py — .env 対話式ウィザード CLI
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ: execution
- execution/__init__.py — 公開 API 集約
- execution/broker_api.py — BrokerAPIProtocol, データモデル, 例外, ファクトリ
- execution/kabu_client.py — kabuステーション REST クライアント
- execution/mock_client.py — MockBrokerClient（テスト用）
- execution/broker_factory.py — Settings に応じたブローカー作成ファクトリ
- execution/order_record.py — OrderRecord（状態遷移の純粋ロジック）
- execution/order_repository.py — SQLite 永続化層（orders テーブル定義含む）
- execution/order_manager.py — 発注フロー（create/send/sync/cancel）
- execution/execution_engine.py — ExecutionEngine（シグナル処理・push drain・kill）
- execution/reconciler.py — 再起動復旧・突合
- execution/risk_manager.py — Gate1/2/3 の実装

サブパッケージ: data
- data/calendar_management.py — マーケットカレンダー管理（DuckDB / J-Quants 連携）
- data/news_collector.py — RSS ニュース収集・前処理（SSRF対策等）

サブパッケージ: monitoring, utils, その他
- 監視・ログ設定・プロセス優先度設定などのユーティリティが含まれます（run_* スクリプトから利用）。

（リポジトリの全ファイル一覧は上記に含まれる主要ファイルを参照してください）

---

トラブルシューティング
- validate_config が "PyYAML がインストールされていません" と警告する場合:
  - PyYAML をインストールすると config/*.yaml のパースチェックが有効になります。
  - pip install PyYAML
- KABUSYS_ENV に unknown 値を設定するとエラーになります。development / paper_trading / live のいずれかを指定してください。
- run_execution/run_monitoring の停止:
  - data/stop_requested.flag の作成でループは安全に停止します。
  - kill.flag は ExecutionEngine が検知すると kill_switch（全 active 注文のキャンセル）を発動します。

---

ライセンス・貢献
- 本 README はコードベースに基づく技術ドキュメントです。実際の運用・接続（特に本番ブローカー接続）を行う前に十分なテストとレビューを行ってください。

---

以上。起動・設定で不明点があれば、実行時のログ（LOG_LEVEL）を DEBUG にして詳細を確認してください。