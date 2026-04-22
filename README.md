KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を目的とした軽量なフレームワークです。本リポジトリは以下の主要コンポーネントを含みます。

- 環境設定管理（.env 読込・対話式ウィザード）
- 設定検証 CLI（.env と config/*.yaml の検証）
- ExecutionEngine（シグナルに基づく発注エンジン）
- Broker クライアント（Mock および kabu station 用の実装）
- リスク管理（Gate1/2/3 の多段防御）
- 再起動時リコンシリエーション（OrderSent の突合）
- 監視ループ（SystemMonitor）
- データユーティリティ（市場カレンダー、RSS ニュース収集等）

主な機能一覧
--------------
- .env 対話式ウィザード（python -m kabusys.config_setup）
  - 初回セットアップや既存 .env の更新を支援
- 設定検証（python -m kabusys.validate_config [--strict]）
  - 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パースをチェック
- ExecutionEngine
  - シグナル読み込み（DuckDB）→ Gate1/2 を経て発注 → WebSocket push ドレイン
  - paper_trading では MockBrokerClient を使い production DB と分離
- RiskManager（3 段階ガード）
  - Gate1: 余力・重複・ポジション上限
  - Gate2: レート制限・サーキットブレーカー
  - Gate3: ドローダウン監視（kill_switch 発動）
- Broker クライアント群
  - MockBrokerClient（テスト用、fill_mode を制御可能）
  - KabuStationClient（kabu station REST API 経由。将来的に本番接続）
- Reconciler
  - 再起動時に OrderSent の注文をブローカーと照合し状態を復元
- 監視（run_monitoring）
  - 定期ポーリングでシステムリソース・監視イベントを記録

前提・依存
-----------
- Python 3.10+
  - モジュール内で PEP 604（| 型）等を利用しています
- 推奨パッケージ（requirements.txt があればそれを使用してください）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（validate_config で YAML 検証を行う場合に必要）
  - その他（logging 等は標準ライブラリ）

セットアップ手順
----------------
1. リポジトリをクローンする
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt が無い場合は最低限:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

4. 環境変数の初期化（推奨）
   - 対話式ウィザードを使って .env を生成:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成
   - 自動的に .env がロードされます（OS 環境変数 > .env.local > .env）
     - 自動ロードを無効にする場合:
       - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定を検証
   - python -m kabusys.validate_config
   - 必須項目が足りないと exit code 1 で失敗します
   - 警告も FAIL にしたい場合は --strict を付与

環境変数（主要）
-----------------
必須（起動前に設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意（デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN（任意）
- LINE_USER_ID（任意）
- PAPER_FILL_MODE（paper_trading 用）: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用）: data/paper_trading.db
- PID_FILE_PATH（PID ファイルのパス）
- KILL_FLAG_PATH（kill.flag のパス）
- KILL_FLAG_CLEAR_ON_START: 0|1（1 の場合、起動時に kill.flag を自動クリア）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒。デフォルト 60）

主要な動作・注意点
------------------
- KABUSYS_ENV
  - development / paper_trading → MockBrokerClient を使用（本番 API 非依存）
  - live → 本番接続想定だが一部実装は例外を投げる（現状は未実装箇所あり）
- Paper trading（KABUSYS_ENV=paper_trading）
  - 実 DB（sqlite）を分離し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録
  - PAPER_FILL_MODE によりモックの約定挙動を制御
- kill.flag / stop_requested.flag
  - 起動時の kill.flag の存在は起動拒否（KILL_FLAG_CLEAR_ON_START=1 なら自動クリアして起動可能）
  - data/stop_requested.flag を置くと実行中のループ（Execution/Monitoring）は検知して正常停止する
- 設定検証の exit code
  - 0: OK（エラーなし、警告なしまたは警告あり）
  - 1: エラーあり、あるいは --strict で警告あり

使い方（主要コマンド）
---------------------
- 環境作成ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告も FAIL とする）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（本番/ペーパー）
  - python -m kabusys.run_execution
  - ExecutionEngine は config の設定や PID/KILL フラグを使って動作します

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: export MONITOR_POLL_INTERVAL=10

- 設定取得（プログラムから）
  - from kabusys.config import settings
  - settings.jquants_refresh_token などでアクセス

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- __init__.py
  - パッケージメタデータ（__version__ 等）

- config.py
  - .env 読込ロジック（自動ロード）、Settings クラス（環境変数ラッパ）
  - 自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に行います

- config_setup.py
  - .env の対話式ウィザード

- validate_config.py
  - 起動前チェック CLI（必須 env, config/*.yaml の存在・YAML パース等）

- run_execution.py
  - ExecutionEngine 起動スクリプト（シグナル読み取り → 発注 → push ドレイン）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - broker_api.py: BrokerProtocol, データモデル, 例外, create_broker_api()
  - kabu_client.py: kabu station 用 REST クライアント（HTTP + WebSocket）
  - mock_client.py: テスト用 MockBrokerClient（fill_mode 制御）
  - broker_factory.py: Settings に応じた BrokerClient 生成
  - execution_engine.py: ExecutionEngine（発注フロー、WebSocket、kill_switch 等）
  - order_record.py: OrderRecord と状態遷移ロジック（純粋ビジネスロジック）
  - order_repository.py: SQLite 永続化レイヤ（orders テーブル）
  - order_manager.py: OrderManager（OrderRecord + Repository + Broker の統合）
  - reconciler.py: 再起動時のリコンシリエーション
  - risk_manager.py: RiskManager（Gate1/2/3）

- data/
  - calendar_management.py: マーケットカレンダー管理（JPX カレンダー）
  - news_collector.py: RSS ニュース収集（前処理・SSRF 対策等）
  - （jquants_client 等、外部 API 周りの実装がここに置かれる想定）

- monitoring/
  - monitoring_db.py, system_monitor.py 等（監視 DB 初期化／監視ロジック）

運用上のヒント
----------------
- .env は決してリポジトリにコミットしないでください（config_setup.py 内にもその旨の注意書きあり）。
- 本番（live）運用時は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の取り扱いに十分注意してください。validate_config は live 設定時に追加チェックを行います。
- 再起動時の整合性を重視する設計のため、OrderSent の途中クラッシュや broker_order_id の永続化などを考慮した実装になっています。実運用では Reconciler のログや position_discrepancies を必ず確認してください。

その他
----
- config/*.yaml のサンプルや自動生成スクリプトがある場合はそれを使って下さい（validate_config は存在しない場合に警告を出します）。
- 必要に応じて requirements.txt を整備し、CI で validate_config を実行して設定漏れを検出することを推奨します。

問題・改善提案・開発
-------------------
- live 用の実ブローカークライアント（KabuStationClient）の運用確認・追加実装
- 監視・アラートの強化（LINE 以外の通知チャネル追加）
- テストカバレッジの拡充（リコンシリエーション、Kill Switch の統合テスト等）

---

必要に応じて README に記載するコマンド例や .env のテンプレート（.env.example）を追加できます。希望があればサンプル .env や起動手順のより詳細な例（systemd / Docker / Docker Compose 用の説明）を作成します。