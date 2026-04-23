README.md

KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を想定した軽量なフレームワークです。  
主に以下を目的とします:

- シグナルに基づく発注（ExecutionEngine）
- 発注の状態管理・永続化（SQLite）
- ブローカー API 抽象化（実装: Mock / kabuステーション クライアント）
- リスクガード（Gate1/2/3）とサーキットブレーカー
- システム監視ループ（SystemMonitor）
- データプラットフォームの補助（DuckDB を用いたカレンダー管理、ニュース収集等）
- 環境設定ウィザード・設定検証ツール

重要: ライブブローカー（KABUSYS_ENV=live）用クライアントは未実装（BrokerClientFactory は NotImplementedError を投げます）。開発・テストは paper_trading / development モードと MockBrokerClient を使用してください。

主な機能
--------
- 環境設定ウィザード (.env 作成) — python -m kabusys.config_setup
- 設定検証ツール (.env と config/*.yaml の検査) — python -m kabusys.validate_config
- ExecutionEngine — シグナル読み取り → 発注 → push ドレイン処理
- Order 管理
  - OrderRecord（状態遷移の純粋ロジック）
  - OrderRepository（SQLite 永続層）
  - OrderManager（発注/同期/キャンセルの高レベル API）
- ブローカークライアント
  - MockBrokerClient（テスト用。fill_mode を指定可能）
  - KabuStationClient（kabuステーション API 実装）
- RiskManager（Gate1: シグナル/余力 等、Gate2: レート制限/CB、Gate3: ドローダウン監視）
- Reconciler（再起動時の OrderSent 状態の突合とポジション差分検出）
- データ系ユーティリティ
  - DuckDB を用いた市場カレンダー管理、next_trading_day 等
  - ニュース収集（RSS）補助関数（SSRF対策・正規化・前処理など）
- 監視プロセス（run_monitoring） — 監視ループと監視 DB 書き込み

セットアップ手順
----------------
1. リポジトリをクローン:
   - git clone <repo-url>
   - cd <repo-root>

2. Python（3.10 以上推奨）と仮想環境を用意:
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（代表的なもの）:
   - pip install duckdb httpx websocket-client PyYAML defusedxml
   - （テスト用に追加で必要なパッケージがある場合は requirements.txt を参照してください）

   代表的な依存ライブラリ
   - duckdb: 分析用 DB
   - httpx: HTTP クライアント（kabu クライアント）
   - websocket-client: WebSocket（kabu push）
   - PyYAML: config/*.yaml のパース（未インストールでも警告）
   - defusedxml: RSS パースの安全化

4. .env を作成:
   - 対話式ウィザード: python -m kabusys.config_setup
     - デフォルトのまま Enter で進められます。J-Quants トークンや kabu API パスワードは必須項目です。
   - あるいは直接 .env を手動作成（.env.example を参考にしてください）

5. 設定を検証:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにするには --strict を付加: python -m kabusys.validate_config --strict

使い方（実行コマンド）
--------------------

- 環境設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup
  - オプション: --env-file を指定して保存先を変更可能

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) 扱い

- 実行エンジン（発注）
  - python -m kabusys.run_execution
  - 注意: stop フラグは <repo-root>/data/stop_requested.flag（停止に応答）
  - PID ファイル: data/execution.pid（デフォルト。Settings で変更可能）
  - 動作モード:
    - KABUSYS_ENV=paper_trading または development → MockBrokerClient を使用
    - KABUSYS_ENV=live → 現状 NotImplementedError（本番クライアント未実装）

- 監視ループ
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - 監視 DB は settings.sqlite_path を使用（環境にかかわらず本番 sqlite_path を参照）

主要な環境変数（抜粋）
---------------------
以下は validate_config / config_setup に頻出するキー（主要なもの）:

必須（システム起動前に設定してください）
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意（デフォルト有り）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABU_API_BASE_URL — kabuAPI のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1）
- PAPER_FILL_MODE — ペーパートレードの fill 挙動: instant / partial / never / reject

PAPER_FILL_MODE の説明:
- instant: 発注即全約定（テスト用）
- partial: 一部約定（テスト用）
- never: pending（注文番号は発行されるが約定しない）
- reject: 発注拒否をシミュレート

動作の注意点
-------------
- ExecutionEngine は session 周り（発注開始時刻・終了時刻）を持っています（デフォルト: 8:50-9:10 発注フェーズ、9:10-15:30 push ドレイン）。
- kill.flag（デフォルト: data/kill.flag）が存在すると起動を拒否するか動作中に kill_switch を発動します。KILL_FLAG_CLEAR_ON_START=1 にすれば起動時に自動でクリアします（本番では推奨されません）。
- 発注フローはクラッシュ耐性を考慮した2相的永続化を行います（OrderSent 保存→ブローカー呼び出し→broker_order_id 保存→OrderAccepted へ遷移）。
- リコンシリエーション機能（Reconciler）により、再起動時に OrderSent 状態の注文をブローカーと突合して復旧を試みます。
- 本番ブローカー（kabuステーション）接続時は HTTP API の 401/429/5xx をハンドリングします。WebSocket push を使うことで即時の注文状態同期を行えます。
- データベース初期化関数（例: init_orders_db, init_monitoring_db）を起動時に呼ぶことでスキーマを作成できます（冪等実装）。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・Settings 管理（.env 自動ロード含む）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前チェック CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

subpackages / 主要モジュール
- execution/
  - broker_api.py          — Broker API の Protocol / データモデル / ファクトリ
  - kabu_client.py         — kabuステーション REST/WebSocket クライアント
  - mock_client.py         — MockBrokerClient（テスト用）
  - broker_factory.py      — 設定からクライアントを作るファクトリ
  - order_record.py        — Order 状態遷移ロジック（純粋ロジック）
  - order_repository.py    — SQLite 永続化層（orders テーブル）
  - order_manager.py       — 高レベル発注 API（create/send/sync/cancel）
  - execution_engine.py    — ExecutionEngine（セッション制御）
  - reconciler.py          — 起動時の復旧（リコンシリエーション）
  - risk_manager.py        — Gate1/2/3 を実装するリスク管理

- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB 利用）
  - news_collector.py      — RSS ニュース収集・正規化・保存補助

- monitoring/
  - (監視関連モジュール — SystemMonitor / monitoring_db など)

- utils/
  - logging_setup.py       — ロギング初期化
  - process_priority.py    — プロセス優先度設定ユーティリティ

- config/
  - *.yaml                 — システム構成用 YAML（存在する場合は validate_config でパースされる）

追加情報 / 開発者向けメモ
------------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup でも注意書きあり）。
- config/*.yaml は optional ですが、存在する場合は PyYAML によるパースで内容検証が行われます（PyYAML が未インストールだとパースはスキップされる）。
- ライブ環境（KABUSYS_ENV=live）を利用する場合は十分な検証とアラート設定（LINE 等）を行ってください。validate_config は live モードでの危険な設定（例: KILL_FLAG_CLEAR_ON_START=1）や LINE 未設定を警告します。
- テストでは MockBrokerClient が多くのケースをカバーします（fill_mode により各種振る舞いを検証可能）。

ライセンス
---------
（ここにプロジェクトのライセンスを記載してください）

問い合わせ / 貢献
-----------------
不具合報告や機能要求は Issue を作成してください。プルリクエスト歓迎です。

---
以上。必要であれば README にセットアップの具体的なコマンド例（requirements.txt ベースや Dockerfile、systemd サービスの例）を追加できます。どの情報を追記したいか教えてください。