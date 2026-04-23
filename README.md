# KabuSys

日本株自動売買システムのミニマム実装（ライブラリ群）。  
このリポジトリは、設定管理、監視ループ、発注エンジン、ブローカークライアントのモック/実装、データ操作ユーティリティなどを含みます。

> 注意: 本 README は提供されたコードベース（src/kabusys 以下）に基づく概要と使い方をまとめたものです。実運用での本番接続（kabuステーション等）は慎重に扱ってください。KABUSYS_ENV=live の完全サポートは未実装箇所があります（コード内に NotImplementedError）。

---

## 概要

- .env ファイル／環境変数に定義された設定値を読み込み、各コンポーネント（ExecutionEngine、Monitoring、DB 接続など）を起動するためのユーティリティと実装を提供します。
- 発注エンジンは Signal Queue Pull 型のフローを持ち、Order レコードの状態機械、永続化（SQLite）、再同期（Reconciliation）や 3 段階のリスクガード（Gate1/2/3）を実装しています。
- ブローカー接続は mock と実際の kabu station クライアントを切り替え可能。テスト / 開発では MockBrokerClient が使えます（paper_trading / development）。
- データ関連ユーティリティ（マーケットカレンダー管理、ニュース収集など）と監視ループ実装を含みます。

---

## 主な機能一覧

- 設定ウィザード（対話式）：.env を生成・更新する CLI (`kabusys.config_setup`)
- 設定検証 CLI：.env と config/*.yaml の存在・妥当性を起動前に検査 (`kabusys.validate_config`)
- ExecutionEngine：シグナル読み取り → Gate 検査 → 発注 → push ドレインの実行フロー
- Order 管理
  - OrderRecord: 注文状態遷移のビジネスロジック
  - OrderRepository: SQLite による永続化
  - OrderManager: 発注フロー（create/send/sync/cancel）とクラッシュ耐性のための永続化手順
  - Reconciler: 再起動時に OrderSent を照合し状態回復、ポジション差分検出
- RiskManager：Gate1（シグナル検査）、Gate2（レート制限・サーキット）、Gate3（ドローダウン監視）
- Broker クライアント
  - MockBrokerClient：テスト用の完全モック（fill_mode 等を設定可能）
  - KabuStationClient：kabu station REST/WebSocket 経由の実装（httpx / websocket-client ベース）
- Data ユーティリティ
  - カレンダー管理（DuckDB を利用して JPX カレンダー管理）
  - ニュース収集（RSS → DB）
- 監視プロセス（SystemMonitor のポーリングループ）

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を準備する（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 代表的な依存パッケージ（環境によって差があります）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（config YAML をパースして検証する場合に必要）
   - 例:
     ```
     pip install duckdb httpx websocket-client defusedxml PyYAML
     ```
   - （requirements.txt がある場合は `pip install -r requirements.txt`）

3. プロジェクトルートに `.env` を用意する
   - 対話式ウィザードを使うと便利です（下記参照）
   - 重要: .env を Git にコミットしないでください（README・コード内でも警告あり）。

4. データディレクトリの作成（必要に応じて）
   - デフォルトで使用するパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - ペーパートレード用 SQLite: data/paper_trading.db
   - これらの親ディレクトリは起動時に自動作成されることがありますが、手動で作成しておくと安心です。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨（デフォルトあり）:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用

制御用:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 : 自動 .env ロードを無効化（テスト等で使用）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill flag を自動クリア（1 にするとクリア）
- KILL_FLAG_PATH : kill.flag のパス（デフォルト: data/kill.flag）
- PID_FILE_PATH : PID ファイルのパス（デフォルト: data/execution.pid）
- MONITOR_POLL_INTERVAL : 監視ループのポーリング間隔（秒、デフォルト 60）

.env の自動ロード挙動:
- OS 環境変数 > .env.local > .env の優先順位でロードされます。
- プロジェクトルートはこのモジュール内の _find_project_root() で `.git` または `pyproject.toml` を起点に探索します。
- 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要 CLI / スクリプト）

- 設定ウィザード（対話式 .env 生成）
  ```
  python -m kabusys.config_setup
  ```
  - 既存 .env があれば読み込んで Enter で再利用できます。
  - 実行後、.env を保存するか確認されます。

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
  ```
  - 必須環境変数の未設定、プレースホルダ値、KABUSYS_ENV の不正値、
    DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パース確認（PyYAML 必須）を行います。

- 監視ループ起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず production の sqlite_path を使用します（デフォルト: data/monitoring.db）。
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します。

- 発注エンジン（ExecutionEngine）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading / development の場合は MockBrokerClient が使用されます（paper_trading では paper DB に分離して記録）。
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - 実行中に stop を要求するには data/stop_requested.flag を作成するか、kill flag（data/kill.flag）を使って kill_switch を発動できます。
  - 実行時に PID ファイル（デフォルト data/execution.pid）を書き出します。

備考:
- 本番環境（KABUSYS_ENV=live）では追加の安全チェックが走り、LINE 通知設定などが未設定だと警告が出ます。live 向けの完全実装はコード中に未実装の箇所があるため注意してください。

---

## よく使うワークフロー（例）

1. 対話式で .env を作成:
   ```
   python -m kabusys.config_setup
   ```

2. 設定検証:
   ```
   python -m kabusys.validate_config
   ```

3. （モニタリング用）監視プロセスを起動:
   ```
   python -m kabusys.run_monitoring
   ```

4. 発注エンジン（テスト / ペーパートレード）を起動:
   ```
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```

5. 停止:
   - 監視・実行プロセスを安全に停止するにはプロジェクトルートの data/stop_requested.flag を作成します。
   - kill.flag（デフォルト: data/kill.flag）を作成すると ExecutionEngine 内で kill_switch を発動して全 active 注文をキャンセルします。

---

## ディレクトリ構成（src/kabusys の主要ファイルと説明）

- src/kabusys/
  - __init__.py
    - パッケージ定義。バージョンなど。
  - config.py
    - 環境変数/.env の読み込みロジックと Settings クラス（アプリ共通設定の取得）。
    - 自動 .env ロードの挙動、必須 env チェック関数 _require を提供。
  - config_setup.py
    - .env を対話的に生成・更新するウィザード CLI。
  - validate_config.py
    - 起動前に環境設定を検証する CLI。strict オプションあり。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
  - run_execution.py
    - ExecutionEngine を初期化してセッションを実行する起動スクリプト。
  - execution/  (発注・注文管理関連)
    - broker_api.py
      - BrokerAPIProtocol（Protocol）、データモデル（OrderRequest/OrderStatus/Position 等）、例外、create_broker_api ファクトリ。
    - kabu_client.py
      - kabu station REST/WebSocket 実装（httpx / websocket-client ベース）。
    - mock_client.py
      - テスト用 MockBrokerClient（fill_mode: instant/partial/never/reject）。
    - broker_factory.py
      - Settings に応じてモック/本番クライアントを生成するファクトリ。
    - order_record.py
      - 注文状態遷移を表す OrderRecord と状態遷移ロジック。
    - order_repository.py
      - SQLite を使った orders テーブルの初期化・読み書き（永続化層）。
    - order_manager.py
      - Order の外向き API（create/send/sync/cancel）と発注フローのクラッシュ耐性処理。
    - execution_engine.py
      - ExecutionEngine 本体（シグナル処理、push ドレイン、kill switch）。
    - reconciler.py
      - 起動時の OrderSent 照合とポジション差分検査（Reconciliation）。
    - risk_manager.py
      - Gate1/2/3 を実装するリスク管理ロジック（トークンバケツ、サーキットブレーカー等）。
  - data/
    - calendar_management.py
      - JPX 営業日判定、next/prev_trading_day、カレンダー更新ジョブ（J-Quants API を利用する想定）。
    - news_collector.py
      - RSS 取得と前処理、raw_news 保存ロジック（SSRF/サイズ制限対策等）。
    - jquants_client.py (参照されるが本 README のコード抜粋には含まれていません)
  - monitoring/
    - monitoring_db.py (参照されるが抜粋未表示)
    - system_monitor.py (参照されるが抜粋未表示)
  - utils/
    - logging_setup.py (参照されるが抜粋未表示)
    - process_priority.py (参照されるが抜粋未表示)

---

## 実装上の注意点 / 安全性

- .env を絶対にリポジトリにコミットしないでください（秘密情報が含まれます）。
- KABUSYS_ENV=live のときは本番用の挙動や安全チェックが走りますが、コードの一部（Broker の Live 実装など）が未実装または注意喚起あり。実運用前にコードレビューと十分なテストを行ってください。
- ExecutionEngine の停止や kill switch は適切に全注文のキャンセルを試みますが、外部ブローカー API の失敗は考慮してログ・監視を行ってください。
- config/*.yaml の検証は PyYAML が必要です。インストールされていない場合は検証がスキップされます（警告出力）。

---

## 追加情報 / 拡張案

- production 用の Broker クライアント（KabuStationClient）の堅牢化と live 環境での検証
- CI での validate_config の実行（--strict モード）による設定検査
- requirements.txt / Dockerfile の追加（デプロイ用）
- 単体テスト、統合テスト、フェイルオーバー試験、監視アラートの実装強化

---

この README はコード内コメント・関数説明に基づいて作成しました。必要があれば、実際の環境でのセットアップ手順（具体的なパッケージバージョン、Docker 化、CI 設定など）を追記します。