# KabuSys

日本株自動売買システムの軽量コアライブラリ（実行・監視・設定管理）。  
このリポジトリは、発注エンジン、リスク管理、監視ループ、ブローカークライアント（モック含む）、データ処理ユーティリティなどを含むコンポーネント群を提供します。

---

## 概要

KabuSys は次を目的としたモジュール群です。

- シグナルに基づく発注（ExecutionEngine）
- 発注の状態管理と永続化（OrderRecord / OrderRepository / OrderManager）
- ブローカー API 抽象化（KabuStationClient / MockBrokerClient）
- 起動時の自動復旧（Reconciler）
- 3段階のリスクガード（RiskManager）
- 監視ループ（SystemMonitor を起動する run_monitoring）
- .env の対話的生成ウィザードと設定検証 CLI

注意: KABUSYS_ENV=live の Live ブローカー実装は未実装（Factory は NotImplementedError を投げます）。開発／テスト用途は `development` / `paper_trading` を使用してください。

---

## 主な機能一覧

- .env 対話式ウィザード（python -m kabusys.config_setup）
- 起動前設定検証（python -m kabusys.validate_config）:
  - 必須環境変数チェック
  - config/*.yaml 存在・YAML パースチェック（PyYAML があれば内容検証）
  - KABUSYS_ENV / LOG_LEVEL 等の妥当性検査
  - DB パス（DUCKDB / SQLITE）の親ディレクトリ確認
  - 本番（live）時の追加ガード（LINE 通知確認等）
- 発注エンジン（ExecutionEngine）:
  - Signal の読み込み → Gate1/2（前置リスク） → 発注 → push ドレイン処理
  - kill flag による安全停止と全注文キャンセル
- Order 管理:
  - 状態遷移（OrderRecord）、SQLite 永続化（OrderRepository）
  - Reconciler による起動時の同期・差分検出
- Broker 抽象化:
  - MockBrokerClient（テスト用、複数 fill_mode サポート）
  - KabuStationClient（実REST、トークン管理。要 kabuステーションの稼働）
- データユーティリティ:
  - マーケットカレンダー管理（DuckDB 上での営業日判定）
  - ニュース収集（RSS → raw_news、SSRF 対策等）

---

## 前提条件 / 推奨環境

- Python 3.9+
- 推奨ライブラリ（用途に応じてインストール）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - pyyaml（validate_config の YAML 検証用）
- 標準ライブラリ: sqlite3, logging など

依存はプロジェクトに requirements.txt があればそれを使うか、上記を pip で個別に追加してください。

例:
```
pip install duckdb httpx websocket-client defusedxml pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン、またはソースを配置
2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # on Unix
   .venv\Scripts\activate      # on Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb httpx websocket-client defusedxml pyyaml
   ```
4. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは既存の .env を読み込み、Enter で既存値を再利用できます。

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

任意/推奨:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu station ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用
- KILL_FLAG_CLEAR_ON_START: 起動時 kill.flag を自動クリア（0/1、デフォルト: 0）
- PAPER_FILL_MODE: paper_trading 時のモック挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

.env の自動読み込み:
- OS 環境変数 > .env.local > .env の順で読み込まれます。  
- テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

最低限の .env（例）
```
JQUANTS_REFRESH_TOKEN=your_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方

- 環境設定ウィザード（.env 作成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（SystemMonitor をポーリング）
  ```
  python -m kabusys.run_monitoring
  # MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 発注エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録します。
  - `KILL_FLAG` 機構: data/kill.flag の存在で起動拒否またはキル動作（KILL_FLAG_CLEAR_ON_START による振る舞い）。

- 開発／テスト:
  - MockBrokerClient は `paper_trading` / `development` で自動選択されます（fill_mode は PAPER_FILL_MODE）。
  - ExecutionEngine の各ループ（_process_signals / _drain_push_queue）はテスト用に直接呼び出せます。

---

## 注意事項 / 運用上のポイント

- Live 環境は未実装: BrokerFactory は `settings.is_live` の場合 NotImplementedError を投げます。実稼働での利用には実ブローカークライアントの実装が必要です。
- kill.flag の取り扱い:
  - 起動時に kill.flag が存在するとデフォルトで起動を拒否します。KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動します（本番では 0 を推奨）。
- DB ファイル: デフォルトは `data/` 下に作成されます。親ディレクトリが存在しない場合は警告が出ますが、起動時に自動作成される場合があります。
- YAML 設定ファイル: config/*.yaml を使用する設計。validate_config は PyYAML があればパース検証を行います。未インストールならパース検証はスキップされ、警告のみ表示されます。
- ログ: utils.logging_setup を経由してログ出力を設定します。LOG_LEVEL で制御してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み / Settings
- config_setup.py          — .env 対話式ウィザード CLI
- validate_config.py       — 起動前の設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- broker_api.py            — Broker API の Protocol / データモデル / ファクトリ
- broker_factory.py        — Settings に基づくクライアント生成
- kabu_client.py           — kabuステーション REST クライアント
- mock_client.py           — テスト用 MockBrokerClient
- order_record.py          — Order の状態機械モデル
- order_repository.py      — SQLite 永続化層
- order_manager.py         — 外向け API（発注ワークフロー）
- execution_engine.py      — ExecutionEngine（セッション全体）
- reconciler.py            — 起動時リコンシリエーション
- risk_manager.py          — 3段階リスクガード

src/kabusys/data/
- calendar_management.py   — マーケットカレンダー管理
- news_collector.py        — RSS ニュース収集（前処理・SSRF 対策等）
- (その他データ関連モジュール)

src/kabusys/monitoring/
- monitoring_db.py         — 監視 DB 初期化 / ログ機能
- system_monitor.py        — 監視ロジック（SystemMonitor）

src/kabusys/utils/
- logging_setup.py         — ロギング初期化
- process_priority.py      — プロセス優先度設定ユーティリティ

（上記は主要ファイルのみ抜粋しています。詳細はソースツリーを参照してください。）

---

## 開発メモ / 拡張ポイント

- Live ブローカー実装の追加（KabuStationClient を用いる実運用モード）  
- config/*.yaml のスキーマ検証を追加すると、より堅牢な起動前チェックが可能
- テスト用のユーティリティ（モックのシナリオ、ユニットテスト）を整備することで CI に組み込みやすくなる
- execution/reconciler のポジション差分修復の運用手順ドキュメント化

---

この README はコードベースの要点をまとめたものです。詳細は各モジュールの docstring（ソース内コメント）や実装を参照してください。必要であれば、デプロイ手順や運用手順のテンプレートも作成します。