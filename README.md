# KabuSys

日本株向け自動売買システム（ミニマル実装）

このリポジトリは、シグナルに基づいて注文を発行・管理し、監視・リコンシリエーション機能を備えた自動売買基盤の一部です。kabuステーション（またはモック）を通じて発注を行い、DuckDB / SQLite を使ったデータ管理・監視を行います。

---

## 主な特徴

- 発注エンジン（ExecutionEngine）
  - シグナル取得 → Gate1/2（リスクガード） → 発注 → WebSocket プッシュ処理による同期
  - ペーパートレード用モッククライアントをサポート
- ブローカー API 層
  - KabuStationClient（httpx ベース、WebSocket push 対応）
  - MockBrokerClient（テスト／開発用）
  - 共通 Protocol / データモデル / 例外定義
- 注文永続化（SQLite）
  - OrderRepository: orders テーブル定義・CRUD
  - OrderRecord: ステートマシン（遷移検証）
- リコンシリエーション（Reconciler）
  - 起動時に OrderSent 状態を照合、ポジション差分を検出
- 監視（SystemMonitor 起動スクリプト）
  - 定期ポーリングでシステムメトリクス・API レイテンシ等を監視
- データ処理
  - DuckDB ベースのマーケットカレンダー管理、RSS ニュース収集（セキュリティ対策付き）
- 設定管理
  - .env ベースの設定読み込み（.env / .env.local、自動読み込み）
  - 対話式ウィザードで .env を作成・更新
  - 起動前に設定検証を行う CLI

---

## 機能一覧（抜粋）

- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
  - .env と config/*.yaml の存在 / YAML パースを検査（PyYAML がある場合）
  - --strict で警告も失敗扱い
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV により paper_trading / development は MockBroker、live は未実装（注意）
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御（デフォルト: 60 秒）
- 注文状態管理（OrderRecord / OrderManager）
  - 二相永続化やクラッシュ耐性を考慮した設計
- リスク管理（RiskManager）
  - Gate1: 余力・重複・ポジション上限
  - Gate2: レート制限・サーキットブレーカー
  - Gate3: ドローダウン監視（kill switch 発動）

---

## 必要要件（依存ライブラリの例）

プロジェクトの一部機能は以下のパッケージに依存します（抜粋）:

- Python 3.9+
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config/*.yaml の内容検証に任意で使用）
- その他: sqlite3 は標準ライブラリ

（実際の requirements.txt / lockfile がある場合はそちらを利用してください）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml PyYAML
```

---

## セットアップ手順

1. リポジトリを取得する（省略）

2. 仮想環境を作成・有効化し依存をインストール

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # もしあれば
   # または個別インストール:
   pip install duckdb httpx websocket-client defusedxml PyYAML
   ```

3. .env を作成する（対話式ウィザード推奨）

   ```bash
   python -m kabusys.config_setup
   ```

   ウィザードは .env（デフォルト）を生成します。.env は絶対に Git にコミットしないでください。

4. 設定の検証

   ```bash
   python -m kabusys.validate_config
   ```

   問題があればエラー / 警告が表示されます。厳密モード:

   ```bash
   python -m kabusys.validate_config --strict
   ```

5. DB 初期化:
   - run_execution / run_monitoring 起動時に自動的に必要テーブルの作成（init_monitoring_db / init_orders_db）が呼ばれます。必要に応じてデータディレクトリを作成してください。

---

## 環境変数（主要）

validate_config と Settings モジュールで参照される主な環境変数を挙げます。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトあり / 推奨設定あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
- KABU_API_BASE_URL: kabu station の base URL（例: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN: 本番でのアラート用
- LINE_USER_ID: 本番通知先
- KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）
- PAPER_FILL_MODE: instant | partial | never | reject
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / 各種監視閾値（CPU/MEM/DISK）

注意点:
- .env / .env.local は自動でロードされます（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config/*.yaml の検証は PyYAML がインストールされている場合のみ行います。

---

## 使い方（CLI / 起動例）

- 環境設定ウィザード（.env を生成／更新）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）

  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
  ```

- 実行エンジン（発注）起動

  ```bash
  python -m kabusys.run_execution
  ```

  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い paper_trading 用 SQLite に記録します。
  - 起動時に data/execution.pid（PID ファイル）を書き、kill.flag や停止フラグを監視します。

- 監視ループ起動

  ```bash
  python -m kabusys.run_monitoring
  ```

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  - 監視は sqlite（settings.sqlite_path）と duckdb（settings.duckdb_path）に接続します。

- 注意: 本番環境（KABUSYS_ENV=live）ではさらに注意が必要です。validate_config は live 設定時に追加警告を出します（LINE 通知設定や KILL_FLAG_CLEAR_ON_START 等）。

---

## 主要なファイル / ディレクトリ構成

（プロジェクトルートの src/kabusys を基準に抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/.env 読み込みロジック、Settings クラス
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/ — 発注関連コンポーネント
    - broker_api.py — Broker API の Protocol / データモデル / 例外 / ファクトリ
    - kabu_client.py — KabuStation REST/WebSocket クライアント実装
    - mock_client.py — 開発用モッククライアント
    - broker_factory.py — Settings に基づくクライアント生成
    - order_record.py — 注文状態モデルと遷移ロジック
    - order_repository.py — SQLite 永続化（orders テーブル）
    - order_manager.py — 注文管理（作成・送信・同期・取消）
    - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py — 起動時リコンシリエーション
    - risk_manager.py — Gate1/2/3 のリスク管理
  - data/ — データ取得・変換系（DuckDB 関連）
    - calendar_management.py — マーケットカレンダー管理 / 営業日判定
    - news_collector.py — RSS ニュース収集（SSRF 対策、正規化）
  - monitoring/ — 監視関連（DB 初期化 / SystemMonitor 等） ※実装ファイルがある想定
  - utils/ — ロギング設定やプロセス優先度制御等ユーティリティ（logging_setup, process_priority 等）

（実際のリポジトリに合わせて差分がある場合があります）

---

## 運用メモ / 注意点

- .env は機密情報を含むため絶対に Git にコミットしないでください。
- KABUSYS_ENV=live を設定すると本番での注文発行が有効になるため、LINE 通知や kill switch の設定を十分確認してください。
- ExecutionEngine は PID ファイルと kill.flag を使って外部停止制御を行います（data ディレクトリにファイルを置く設計）。
- Paper trading 環境ではデータベースが本番用と分離されます（PAPER_TRADING_SQLITE_PATH）。
- KabuStationClient はローカルの kabuステーション® アプリの起動を前提としています。開発／CI では MockBrokerClient を使用してください。

---

この README はコードベース（src/kabusys 以下）の主要な設計と使い方の概要をまとめたものです。詳細な実装や追加のユーティリティ、運用ガイドはソースコード内のドキュメントコメントを参照してください。必要があれば README に追記します。