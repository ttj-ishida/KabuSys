# KabuSys

日本株自動売買システムのパッケージ（部分実装）。  
このリポジトリは実行環境設定、モニタリング、発注エンジン、ブローカー抽象、ニュース収集、マーケットカレンダー等の主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したコンポーネント群を提供します。主な責務は次のとおりです。

- 環境変数／YAML 設定の管理・ウィザード・検証
- 発注フロー（ExecutionEngine）と注文状態管理（OrderRecord / OrderRepository）
- ブローカー抽象（KabuStation 実装とモック実装）と発注 API
- リスク管理（3段階のガード: Gate1/2/3）
- 起動時リコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor をポーリングして監視DBに記録）
- データ関連（マーケットカレンダー、ニュース収集、DuckDB を用いた分析基盤の一部）

このコードベースは「本番（live）」「ペーパートレード（paper_trading）」「開発（development）」を想定しており、環境ごとに挙動を切り替えます。

---

## 主な機能一覧

- .env 自動読み込み（プロジェクトルートの .env / .env.local、OS 環境変数優先）
- 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（環境変数と config/*.yaml の存在・パースチェック）
  - --strict モードで警告も失敗扱いに可能
- ExecutionEngine:
  - シグナル読み込み（DuckDB）→ Gate1/2 を通して発注 → push ドレイン（WebSocket）
  - kill_switch（全 active 注文キャンセル）機能
- ブローカー抽象:
  - MockBrokerClient（テスト用 fill_mode）
  - KabuStationClient（kabu station REST / WebSocket 実装）
- OrderState の State Machine（OrderRecord）と SQLite 永続化（OrderRepository）
- リスク管理（チェック & サーキットブレーカー・レート制限）
- リコンシリエーション（再起動時に OrderSent 状態を復旧しポジション差分を検知）
- 監視プロセス（run_monitoring）: SQLite / DuckDB を用いた常時監視ループ

---

## 動作環境・依存

- Python 3.10+
  - 型ヒント（X | Y 形式）を用いているため Python 3.10 以上を推奨します。
- 推奨パッケージ（環境に応じてインストールしてください）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（設定検証で YAML の中身をチェックする場合）
  - defusedxml
- 標準ライブラリ: sqlite3, logging, threading, pathlib 等

依存をまとめた requirements ファイルは本リポジトリには含まれていない想定です。venv を作成して手動でインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb httpx websocket-client defusedxml pyyaml
   ```

4. .env を作成
   - 対話式ウィザードを利用するのが簡単です（.env は絶対にリポジトリにコミットしないでください）。
   ```
   python -m kabusys.config_setup
   ```
   - または手動でプロジェクトルートに `.env` を作成し、必要な環境変数を設定します（下記参照）。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／推奨:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu station API ベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番での通知設定
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア(1) するか(0=しない)

推奨ワークフロー:
- .env を作成 → validate_config で検証 → 実行

注意:
- .env.example を参考に .env を作成してください（リポジトリに .env をコミットしないこと）。
- KABUSYS_ENV=live を設定すると本番動作となるため、LINE 通知等の設定や kill フラグの取り扱いを慎重に確認してください。

---

## 使い方（実行コマンド）

- 環境設定ウィザード（対話式 .env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動（SystemMonitor ポーリングループ）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（デフォルト 60）
  ```
  python -m kabusys.run_monitoring
  ```

- 発注（ExecutionEngine）起動
  - KABUSYS_ENV に応じて MockBrokerClient を使う（development / paper_trading）か、本番実装（live、未実装）になります。
  ```
  python -m kabusys.run_execution
  ```

- 注意点
  - run_monitoring は監視用 SQLite（settings.sqlite_path）を使用します。監視は環境にかかわらず本番 sqlite_path を使う設計です。
  - run_execution は paper_trading の場合、paper 用 sqlite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離します。
  - stop リクエストはプロジェクトルート `data/stop_requested.flag` ファイルの存在によって検知される実装になっています（既定の停止フラグパス）。

---

## 主要コマンドの例

- デフォルト検証（警告は出力されるが exit コードは 0）
  ```
  python -m kabusys.validate_config
  ```

- 厳格モード（警告も FAIL）
  ```
  python -m kabusys.validate_config --strict
  ```

- .env を特定パスに保存してウィザード実行
  ```
  python -m kabusys.config_setup --env-file /path/to/.env
  ```

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
  - パッケージ初期化・バージョン情報
- config.py
  - 環境変数の自動読み込み、Settings クラス（アプリ設定）
- config_setup.py
  - 対話式 .env 作成ウィザード
- validate_config.py
  - 起動前の環境設定検証 CLI
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト

subパッケージ: execution/
- broker_api.py
  - ブローカー API のデータモデル、Protocol、ファクトリ
- kabu_client.py
  - kabu station REST/WebSocket クライアント実装
- mock_client.py
  - テスト用モックブローカー（fill_mode 等の制御あり）
- broker_factory.py
  - Settings に基づき適切なブローカークライアントを生成
- order_record.py
  - Order の状態遷移（State Machine）
- order_repository.py
  - SQLite を用いた永続化（orders テーブル初期化含む）
- order_manager.py
  - 発注フロー（create/send/sync/cancel）を統括
- execution_engine.py
  - シグナル処理、push ドレイン、セッション管理
- reconciler.py
  - 起動時リコンシリエーション（OrderSent の突合・ポジション差分検査）
- risk_manager.py
  - 3段階リスクガード（Gate1/2/3）

subパッケージ: data/
- calendar_management.py
  - マーケットカレンダー管理（DuckDB 利用、次営業日計算等）
- news_collector.py
  - RSS からニュースを収集・正規化して保存するロジック（セキュリティ考慮あり）

その他ユーティリティ群:
- utils/logging_setup.py（ログ設定）
- utils/process_priority.py（プロセス優先度設定）
- monitoring/*（監視関連 DB 初期化・SystemMonitor 実装） — run_monitoring で使用

（注）上記は主要ファイルの抜粋です。実際のツリーは src/kabusys 以下に多くのモジュールが存在します。

---

## 実装上の注意 / 運用メモ

- .env は決してリポジトリにコミットしないでください（README 内の .env 設定や config_setup が警告を出します）。
- KABUSYS_ENV を `live` にする場合は特に注意（本番発注）。validate_config は live 時に追加ガードを行います（LINE 通知設定などのチェック）。
- 発注フローはクラッシュ耐性を考慮した二相的永続化の設計になっています（OrderSent 状態など）。
- Reconciler による起動時復旧は重要です。Automatic reconciliation を有効にしてからセッションを開始してください。
- テスト・開発は paper_trading / development 環境で MockBrokerClient を使うことを推奨します。

---

## 参考：よく使うファイル・関数

- Settings クラス（kabusys.config.Settings） — 環境依存の各種パス／フラグを取得
- BrokerClientFactory.create(settings) — 実行環境に応じたブローカークライアントを取得
- ExecutionEngine.run_session() — 発注セッションの実行メソッド
- OrderManager.create_order / send_order / sync_order / cancel_order — 注文操作の外向き API
- Reconciler.run() — 起動時の注文・ポジション突合処理

---

必要であれば README に実際の .env のテンプレート例や、主要な API（OrderRequest/OrderResponse 等）の説明、ユニットテストの実行方法、デプロイ手順（systemd ユニットなど）を追記できます。どの追加情報が必要か教えてください。