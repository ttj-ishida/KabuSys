# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
本ドキュメントではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。  
主な責務は次のとおりです。

- シグナルに基づく発注フローの実装（ExecutionEngine）
- ブローカークライアント抽象化（kabu station 実装 / モック）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- リスクガード（Gate1/2/3 を実装した RiskManager）
- 起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor を使った監視プロセス）
- データ処理（マーケットカレンダー、ニュース収集など）
- .env ベースの設定管理・ウィザード・検証ツール

このリポジトリは、実運用（live）だけでなくペーパートレード（paper_trading）や開発（development）に対応する設計になっています。

---

## 機能一覧

- 環境変数 / .env 自動読み込み（Settings）
- .env 対話式ウィザード（config_setup.py）
- 起動前設定検証 CLI（validate_config.py）
  - 必須変数検出、YAML 設定ファイルの存在・パース検査（PyYAML があれば）
  - `--strict` で警告も失敗扱い
- 発注エンジン（run_execution.py / ExecutionEngine）
  - Signal Queue からシグナル読み込み → Gate1/2 を経て発注
  - WebSocket push ドレイン（kabu push）
  - PID / kill.flag 管理、停止フラグ対応
- ブローカー抽象化
  - MockBrokerClient（テスト / ペーパートレード用）
  - KabuStationClient（kabu station REST API 実装）
  - create_broker_api ファクトリ
- 注文管理
  - OrderRecord（状態遷移の検証）
  - OrderRepository（SQLite 永続化）
  - OrderManager（作成・送信・同期・キャンセル）
  - Reconciler（再起動時の OrderSent 照合とポジション差分検出）
- リスク管理（RiskManager）
  - Gate1: 余力・重複・ポジション上限
  - Gate2: レート制限・サーキットブレーカー
  - Gate3: ドローダウン監視（キルスイッチ）
- 監視プロセス（run_monitoring.py）
  - SystemMonitor のポーリング
  - MONITOR_POLL_INTERVAL による間隔変更
- データ処理
  - マーケットカレンダー管理（calendar_update_job / next_trading_day 等）
  - ニュース収集（RSS → raw_news）

---

## 前提（依存ライブラリ）

主な依存（実行に必要／推奨されるもの）:

- Python 3.9+
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config/*.yaml のパース検査に使用、未インストールでも動作する）

（プロジェクトに requirements.txt がある場合はそちらを使ってください）

例（仮）:
```
pip install duckdb httpx websocket-client defusedxml pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして環境を準備します。

2. 仮想環境を作成して依存をインストールします（任意）:
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS/Linux
   .venv\Scripts\activate       # Windows
   pip install -r requirements.txt   # あれば
   ```

3. .env を作成します（推奨: 対話式ウィザードを使用）:
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは既存の `.env` を読み込み、対話形式で値を更新して保存します。保存後は `.env` を Git にコミットしないでください（機密情報を含むため）。

4. 設定の検証を行います:
   ```
   python -m kabusys.validate_config
   ```
   問題があれば警告/エラーが出ます。警告をエラー扱いにしたい場合は `--strict` を付けます。

5. 実行前に必要な DB ディレクトリ等は自動作成されることが多いですが、権限等に注意してください。デフォルト DB パス:
   - DuckDB: data/kabusys.duckdb
   - SQLite (監視): data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db

---

## 環境変数（重要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意／設定可能な環境変数:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB (default: data/paper_trading.db)
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABU_API_BASE_URL — kabu station ベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用
- KILL_FLAG_CLEAR_ON_START — 本番での kill.flag 自動クリア (0/1)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）

Settings モジュールは自動でプロジェクトルートの `.env` および `.env.local` を読み込みます（OS 環境変数を優先）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

サンプル（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

注意: ウィザードで生成される `.env` は秘密情報を含むため絶対に Git にコミットしないでください。

---

## 使い方（主要 CLI / スクリプト）

- 設定ウィザード（.env 作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も失敗扱い
  ```

- 実行エンジン起動（本番 / ペーパートレードに応じて動作）
  ```
  python -m kabusys.run_execution
  ```
  - ペーパートレード / 開発環境では MockBrokerClient を使用して `data/paper_trading.db` に記録されます。
  - 起動時に `data/execution.pid` が書かれ、`data/stop_requested.flag` により停止可能です。
  - `kill.flag` を検出すると起動を拒否（設定によっては自動クリア）します。

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 短い間隔に変更したい場合は `MONITOR_POLL_INTERVAL` を設定します（秒）。
  - 監視は `SQLITE_PATH` を使って監視 DB に接続します（環境にかかわらず sqlite_path を使用）。

- 開発用: モックブローカー作成 / ブローカーファクトリは Settings に基づいて自動で選択されます。

---

## 運用上の注意

- KABUSYS_ENV=live の場合は本番環境です。LINE 通知等の設定（LINE_TOKEN, LINE_USER_ID）を必ず確認してください。validate_config は live 設定時に追加チェックを行います。
- kill.flag（デフォルト: data/kill.flag）および stop_requested.flag（data/stop_requested.flag）はプロセスの安全停止や起動拒否に用いられます。取り扱いに注意してください。
- Order の耐障害性設計: OrderSent の永続化や broker_order_id の先保存など、リコンシリエーションで回復可能な設計になっています。
- DB マイグレーションや初期テーブル作成は各 run_* スクリプト内で init 系関数を呼んで保証します（例: init_monitoring_db, init_orders_db）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/.env の読み込みと Settings
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py            — Broker API Protocol / データモデル / ファクトリ
    - broker_factory.py        — Settings に基づくクライアント生成
    - kabu_client.py           — kabu station REST API 実装（HTTP + WebSocket）
    - mock_client.py           — MockBrokerClient（テスト / paper_trading）
    - order_record.py          — Order 状態遷移ロジック（純粋ビジネスロジック）
    - order_repository.py      — SQLite 永続化層（orders テーブル）
    - order_manager.py         — Order のライフサイクル管理
    - execution_engine.py      — 発注エンジン（Signal 処理 + push ドレイン）
    - reconciler.py            — 起動時のリコンシリエーション
    - risk_manager.py          — Gate1/2/3 のリスクガード
  - data/
    - calendar_management.py   — マーケットカレンダー関連
    - news_collector.py        — RSS ニュース収集
    - jquants_client.py        — J-Quants API クライアント（参照）
  - monitoring/
    - monitoring_db.py         — 監視 DB 初期化 / ログ書き込み（参照）
    - system_monitor.py        — システム監視ロジック（参照）
  - utils/
    - logging_setup.py         — ロギング設定ユーティリティ（参照）
    - process_priority.py      — プロセス優先度設定ユーティリティ（参照）

（上に示したファイル群が主要なコンポーネントです。一部ファイルはこの抜粋に含まれていませんが、同様の役割を持つ補助モジュールがあります。）

---

## 開発 / テストのヒント

- MockBrokerClient を使えば kabu station を立ち上げずに発注フローやリコンシリエーションの単体テストが可能です。
- OrderRecord は DB に依存しない純粋な状態遷移ロジックを提供するため、ユニットテストが容易です。
- calendar_management の関数（next_trading_day 等）はデータの有無で処理が変わるため、DuckDB に少量のカレンダーを投入してテストすることを推奨します。
- validate_config は PyYAML が無い場合 YAML の中身チェックをスキップします。CI では PyYAML を入れておくと良いです。

---

もし README に追加したい項目（運用チェックリスト、CI/CD の手順、具体的な設定例、より詳細なアーキテクチャ図など）があれば教えてください。必要に応じて追記します。