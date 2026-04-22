# KabuSys — 日本株自動売買システム (README)

簡潔な説明と使い方をまとめた README です。プロジェクトはローカル開発・ペーパートレード・本番（live）運用を想定した自動売買基盤の一部（クライアント、エンジン、リスク管理、監視、データ処理等）を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステムのコードベースです。主な責務は以下の通りです。

- シグナルに基づく発注（ExecutionEngine）
- ブローカークライアント群（実ブローカ／モック）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- リスクガード（3段階の Gate）
- 起動時のリコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor 起動スクリプト）
- 環境設定ウィザード (.env 作成) と設定検証 CLI
- データ処理（マーケットカレンダー、RSS ニュース収集 など）

設計上、DB 操作とビジネスロジックを分離し、クラッシュ耐性やリコンシリエーションを考慮した永続化フロー（SQLite / DuckDB）になっています。

---

## 主な機能一覧

- .env 対話式ウィザード（kabusys.config_setup）
  - 初期 .env の作成・更新を支援
- 設定検証（kabusys.validate_config）
  - 必須環境変数・config/*.yaml の有無・フォーマット等を起動前にチェック
  - --strict オプションで警告も失敗扱いに
- ExecutionEngine（kabusys.execution.execution_engine）
  - シグナル読み込み、Gate1/Gate2 チェック、発注、push ドレイン
- Order 管理
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（作成・送信・同期・キャンセル）
- ブローカークライアント
  - KabuStationClient（kabuステーション REST API 実装）
  - MockBrokerClient（テスト用）
  - create_broker_api() ファクトリ
- RiskManager（3段階ガード: check_signal / check_execution / check_metrics）
- Reconciler（OrderSent の突合とポジション差分検出）
- データモジュール
  - calendar_management（営業日判定、カレンダー更新ジョブ）
  - news_collector（RSS 収集・正規化）
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - SQLite/duckdb への接続、SystemMonitor の定期実行

---

## セットアップ手順

※ 以下は一般的なセットアップ手順です。実行環境やポリシーに応じて適宜調整してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   （requirements.txt が無い場合は下記を目安にインストールしてください）
   ```
   pip install duckdb httpx websocket-client defusedxml
   # 任意: YAML 検証を有効にする場合
   pip install pyyaml
   ```
   - SQLite は Python 標準で同梱されています（sqlite3）。
   - 他に logging や typing 等は標準ライブラリでまかなえます。

4. .env を作成
   - 対話式ウィザードを使うのが簡単です（次節参照）。
   - 自分で作る場合はプロジェクトルートに `.env` を置きます。
   - 自動ロード: デフォルトでプロジェクトルートの `.env`、続いて `.env.local`（上書き）を読み込みます。
     - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. データディレクトリ
   - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）は `data/` 以下に置かれます。実行時に親ディレクトリが無ければ自動作成されることがありますが、事前に `mkdir -p data` などで準備しておくと安心です。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）パス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL — kabu station base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用 LINE 設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

詳細な項目は `kabusys/config_setup.py` の `_ITEMS` を参照してください。

サンプル（.env の抜粋）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方

1. .env を対話式で作成
   ```
   python -m kabusys.config_setup
   ```

2. 設定検証（起動前チェック）
   - 警告はデフォルトでは失敗にしないが、--strict で警告も FAIL 扱いに
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

3. ExecutionEngine（発注エンジン）を起動
   - 通常はサービスや systemd などで起動する想定
   ```
   python -m kabusys.run_execution
   ```
   - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の SQLite に記録します（本番 DB と分離）。

4. 監視ループを起動
   ```
   python -m kabusys.run_monitoring
   ```
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
   - 監視は常に本番用の sqlite_path を使用します（環境に依らず）。

5. 開発・テスト用のモック
   - ブローカーの実装はファクトリ `create_broker_api(mock=True, ...)` で差し替え可能。
   - MockBrokerClient は `fill_mode`（instant/partial/never/reject）で挙動を制御できます。

停止フラグ:
- プロジェクトルートの `data/stop_requested.flag` を作成すると監視/実行プロセスが検知して終了します。
- Kill Switch: `data/kill.flag` による即時停止＆キャンセル挙動が実装されています。`KILL_FLAG_CLEAR_ON_START=1` をセットすると起動時に自動クリアされます（本番では非推奨）。

ログ・PID:
- PID ファイルやログ設定は `Settings` 経由で取得します（`PID_FILE_PATH` 等）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings クラス（.env 自動ロードロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine を起動するスクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - execution/ (注文・ブローカ層)
    - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
    - kabu_client.py — kabuステーション HTTP クライアント
    - mock_client.py — テスト用 MockBrokerClient
    - broker_factory.py — Settings に基づくクライアント生成
    - order_record.py — OrderRecord（状態遷移ロジック）
    - order_repository.py — SQLite による永続化層
    - order_manager.py — 注文作成/送信/同期/キャンセル API
    - execution_engine.py — ExecutionEngine 本体（シグナル処理・push ドレイン）
    - reconciler.py — 起動時のリコンシリエーション（OrderSent 照合）
    - risk_manager.py — 3 段階のリスクガード

  - data/ (データ処理)
    - calendar_management.py — マーケットカレンダー管理（営業日判定、更新ジョブ）
    - news_collector.py — RSS ニュース収集・前処理（SSRF/サイズ制限等の対策を含む）
    - jquants_client.py — （参照される J-Quants クライアント、実装は別ファイル想定）

  - monitoring/ (監視)
    - monitoring_db.py — 監視用 DB 初期化 / ログ操作（参照される）
    - system_monitor.py — SystemMonitor 実装（参照される）

  - utils/
    - logging_setup.py — ログ初期化ユーティリティ（参照される）
    - process_priority.py — プロセス優先度設定ユーティリティ（参照される）

（注意）上記のうち一部ファイルは今回提示されたコード一覧に含まれない参照先（monitoring_db.py、system_monitor.py、jquants_client.py、utils/* 等）があります。実際のリポジトリではそれらも実装されている想定です。

---

## 運用上の注意点

- KABUSYS_ENV の取り扱い
  - 有効値: `development`, `paper_trading`, `live`
  - `live` は本番扱いのため、LINE 等の通知設定と kill_flag の設定を慎重に確認してください。
- validate_config を必ず実行して設定ミスを検出すること（--strict で警告も失敗扱いにできます）。
- ExecutionEngine の発注は複数段階で永続化され、クラッシュ時の復旧（リコンシリエーション）を念頭に設計されています。DB スキーマや UNIQUE 制約（signal_id のアクティブ制約）に注意してください。
- 実ブローカを使う場合は kabuステーション® アプリがローカルで起動している必要があります（KabuStationClient の前提）。

---

## 補足情報 / トラブルシューティング

- YAML 検証
  - validate_config は PyYAML が無い場合、YAML のパース検証をスキップします。YAML 検証を行うには `pyyaml` をインストールしてください。
- DB ファイルの場所
  - デフォルト: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db`。環境変数で上書き可能。
- テスト実行
  - MockBrokerClient を使えば kabuステーション不要で発注ロジックのテストが可能です（`create_broker_api(mock=True, fill_mode=...)`）。

---

必要であれば、README に「開発者向けの詳細（DB スキーマ、API モックの使い方、ユニットテスト手順）」やサンプル .env.example、systemd ユニット例、CI 設定などの付録を追加できます。どの情報を補足したいか教えてください。