# KabuSys

日本株向け自動売買システム（骨組み）  
このリポジトリはシグナル駆動の発注エンジン、ブローカークライアント抽象、リスクガード、監視・リコンシリエーション機能などを含むモジュール群を提供します。テスト／開発用途の Mock ブローカ、kabuステーション向けクライアント（同期 HTTP + WebSocket）、および設定管理・検証の CLI を備えています。

---

## 概要（Project overview）

- シグナルを読み取り発注を行う ExecutionEngine（Signal Queue Pull 型）。
- OrderRecord による状態遷移ロジックと SQLite 永続化（OrderRepository）。
- ブローカ API 抽象（BrokerAPIProtocol）と、テスト用 MockBrokerClient / KabuStationClient 実装。
- 3 段階のリスクガード（Gate1: シグナルレベル、Gate2: 実行レベル、Gate3: メトリクス/ドローダウン）。
- 起動前に .env と config/*.yaml を検証する CLI（validate_config）と、.env を対話作成するウィザード（config_setup）。
- 監視用ポーリングループ（run_monitoring）と発注プロセス起動スクリプト（run_execution）。
- DuckDB を分析・シグナル保存に、SQLite を監視・注文履歴に使用。

---

## 主な機能（Feature list）

- 環境設定ウィザード（.env を対話的に生成 / 更新）
- 起動前設定検証ツール（必須環境変数のチェック、YAML 構文チェック、パスの存在確認）
- ExecutionEngine：シグナルの読み取り、Gate1〜3 による安全チェック、注文作成・送信、push drain（WebSocket）
- Order 状態遷移の厳密な管理（OrderRecord）
- SQLite による注文永続化（OrderRepository）とリコンシリエーション（Reconciler）
- RiskManager：レート制限（トークンバケツ）、サーキットブレーカー、ドローダウン監視
- MockBrokerClient によるローカルでの発注テスト（複数の fill_mode をサポート）
- KabuStationClient：kabuステーション REST / WebSocket クライアント（同期 httpx + websocket-client）
- データ系ユーティリティ：市場カレンダー管理（DuckDB）、RSS ニュース収集（安全対策付き）

---

## 要件（Requirements）

- Python 3.9+
- 推奨パッケージ（実行に必要／推奨）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（config YAML 検証用）
  - defusedxml（RSS パースの安全化）
- SQLite（標準ライブラリ sqlite3 を使用）
- （任意）kabuステーションを接続する場合は kabuステーションアプリがローカルで起動していること

※ 実際のプロジェクトでは requirements.txt を用意してください。上記はコードから推測される依存です。

---

## セットアップ手順（Setup）

1. リポジトリをクローンし、仮想環境を作成：
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）:
   - pip install duckdb httpx websocket-client pyyaml defusedxml

3. .env の準備（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   - ウィザードは .env を生成または既存ファイルを更新します。

4. 設定の検証:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. DB 初期化など（実行前に必要な初期化スクリプトがあれば実行）。orders テーブル等は起動時に init 関数で作成されます（例: init_orders_db）。

---

## 環境変数（主な一覧）

必須（validate_config / Settings でチェック）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意・推奨:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient（paper DB を使用）
  - live: 本番挙動（注意喚起あり）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード時の専用 SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（0/1、デフォルト:0）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番での通知用）

監視・停止ファイル:
- data/stop_requested.flag — 任意に作成すると run_monitoring / run_execution が検知して停止します
- kill.flag（path は KILL_FLAG_PATH 環境変数で変更可） — 実行中の kill switch 判定用

---

## 使い方（Usage）

1. .env の作成（推奨）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告でも exit(1)

3. 監視プロセスの起動（SystemMonitor ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を調整可能（デフォルト 60）

4. 発注エンジンの起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - KABUSYS_ENV が development / paper_trading の場合は MockBrokerClient を使う（paper_trading では paper DB に記録）
   - 停止は data/stop_requested.flag を作成するか、実行中の kill.flag を適切にセット

5. 開発用：Mock ブローカ操作
   - BrokerClientFactory により development / paper_trading では create_broker_api(mock=True, fill_mode=...) が使われます
   - Mock の挙動（instant / partial / never / reject）でテスト可能

---

## 重要な挙動と注意点

- KABUSYS_ENV=live の場合は本番注文本番 DB を使うため、LINE 通知や kill flag の設定など慎重に。
- ExecutionEngine はセッションスケジュールに従い動作します（デフォルトでシグナル処理 8:50〜9:10、プッシュドレイン 9:10〜15:30）。
- Order の状態遷移は厳密に管理され、不正遷移は例外で防止されます。
- OrderSent（送信済みだが確定していない）状態はクラッシュ耐性を考慮した二相永続化を踏襲しており、リコンシリエーションで復旧可能です。
- run_monitoring と run_execution は stop flag（data/stop_requested.flag）を検知して安全に終了します。

---

## ディレクトリ構成（Directory structure）

下記は src/kabusys 以下の主なファイル／モジュール一覧（今回提供されたコードに基づく）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 起動前設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py               — BrokerAPIProtocol / データモデル / ファクトリ
    - broker_factory.py           — Settings に基づくブローカ生成
    - kabu_client.py              — kabuステーション REST/WebSocket クライアント
    - mock_client.py              — MockBrokerClient（開発・テスト用）
    - order_record.py             — OrderRecord と状態遷移ロジック
    - order_repository.py         — SQLite 永続化レイヤ
    - order_manager.py            — 発注制御と broker 呼び出しのオーケストレーション
    - execution_engine.py         — ExecutionEngine（シグナル処理 + push drain）
    - reconciler.py               — 起動時リコンシリエーション
    - risk_manager.py             — Gate1/2/3 のリスク管理
  - data/
    - calendar_management.py      — 市場カレンダー（DuckDB）およびユーティリティ
    - news_collector.py           — RSS ニュース収集（安全対策）
  - monitoring/                    — 監視用モジュール（今回の抜粋では参照元のみ）
  - utils/
    - logging_setup.py            — ログ初期化（参照あり）
    - process_priority.py         — プロセス優先度設定（参照あり）

プロジェクトルートに:
- .env（環境変数ファイル / .git 管理しないこと）
- data/（DB ファイル・PID・フラグを格納するデフォルトディレクトリ）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/stop_requested.flag, data/kill.flag

---

## 開発のヒント

- ローカルでの挙動確認は KABUSYS_ENV=development または paper_trading を使用し、MockBrokerClient の fill_mode を切り替えて各ケースをテストしてください。
- .env は絶対に Git にコミットしないでください（config_setup.py 内でも注意喚起あり）。
- YAML の検証には PyYAML が必要です（validate_config は未インストール時に YAML の検証をスキップします）。
- ExecutionEngine のセッションタイミングやポーリング間隔は EngineConfig / MONITOR_POLL_INTERVAL / Environment で調整可能です。

---

以上。必要であれば README に「インストール用 requirements.txt」やサンプル .env.example を追加するテンプレートや、コマンド例（systemd ユニットや supervisord 設定例）も作成します。どの情報を追加したいか教えてください。