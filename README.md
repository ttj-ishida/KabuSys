# KabuSys

日本株向け自動売買システムのコアライブラリ（プロトタイプ）。  
このリポジトリには、環境設定、監視、発注エンジン、ブローカークライアント（モック含む）、データ処理ユーティリティが含まれます。

---

## プロジェクト概要

KabuSys は、ローカル環境（開発 / ペーパートレード）向けに設計された自動売買システムのコア実装です。  
主要な機能は次の通りです。

- 環境変数 / .env ベースの設定管理とウィザード（対話式）
- 起動前の設定検証ツール（YAML / 環境変数チェック）
- 発注エンジン（ExecutionEngine）：シグナル読み取り → リスクガード → 発注フロー
- ブローカークライアント層：MockBrokerClient（テスト用） / KabuStationClient（kabuステーション向け）
- 注文永続化（SQLite）および注文状態モデル（状態遷移検証）
- 起動時のリコンシリエーション（OrderSent 状態の復旧）
- システム監視ループ（SystemMonitor 起動用スクリプト）
- データ系ユーティリティ（マーケットカレンダー / ニュース収集 など）

本リポジトリは本番向けの完成品ではなく、設計と運用フローの実証を目的とした実装を提供します。KABUSYS_ENV によって動作モードを切り替えます。

---

## 主な機能一覧

- 環境設定関連
  - 対話式 .env 作成・更新: python -m kabusys.config_setup
  - 起動前の設定検証: python -m kabusys.validate_config [--strict]

- Execution（発注）
  - ExecutionEngine: シグナル処理（指定時間帯） + WebSocket push ドレイン
  - OrderManager: 注文作成、送信、照合（sync）、キャンセル
  - OrderRepository: SQLite による注文永続化とインデックス、ユニーク制約
  - RiskManager: Gate1/2/3 の三段階リスクガード（余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン）
  - Reconciler: 再起動時の自動同期・ポジション差分検出
  - BrokerFactory: 設定に応じて Mock / 実ブローカーを生成

- Broker クライアント
  - MockBrokerClient: テスト用モック（fill_mode: instant/partial/never/reject）
  - KabuStationClient: kabuステーション REST API クライアント（httpx + websocket-client）

- データ / ユーティリティ
  - calendar_management: JPX カレンダー管理・営業日判定・バッチ取得ジョブ
  - news_collector: RSS 収集・正規化・保存（安全対策済み）
  - 設定読み込み（.env 自動ロード）と Settings ラッパー

- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可）
  - 監視用 SQLite / DuckDB への接続と初期化

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール  
   （リポジトリに requirements.txt がない場合は下記の主要依存をインストールしてください）
   ```
   pip install duckdb httpx websocket-client PyYAML defusedxml
   ```

   - 任意／推奨パッケージ
     - PyYAML: validate_config の YAML パース検査に使用（未インストールでも動作するが内容検証はスキップされます）
     - duckdb: DuckDB を使う機能群に必要
     - httpx, websocket-client: KabuStationClient を使う場合に必要
     - defusedxml: RSS パーサのセキュリティ用

3. プロジェクトルートで .env を用意
   - 対話的に作る（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成（例は下記参照）

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意／設定可能:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

自動ロード:
- パッケージ import 時にプロジェクトルート（.git or pyproject.toml を含むパス）から .env と .env.local を自動ロードします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意:
- .env は機密情報を含むため Git にコミットしないでください。

サンプル (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=paper_trading
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict    # 警告も失敗扱い
  ```

- 実行エンジン（Execution）
  - 実際にセッションを走らせる:
    ```
    python -m kabusys.run_execution
    ```
  - 動作モードに応じて、KABUSYS_ENV=paper_trading は MockBrokerClient を利用し paper_trading 用 DB に記録します。
  - 強制停止・Kill スイッチ:
    - 監視される停止フラグ: data/stop_requested.flag（作成するとループが順次停止）
    - kill.flag（デフォルト data/kill.flag）: 存在すると起動拒否あるいは実行中に kill switch が発動します（KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリア可能）

- 監視ループ（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境にかかわらず本番 sqlite_path を使用します（MONITOR_POLL_INTERVAL でポーリング間隔を調整）

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込みと Settings クラス（.env 自動ロード）
  - config_setup.py               — 対話式 .env ウィザード
  - validate_config.py            — 起動前チェック CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py               — Broker API インターフェース・データモデル・ファクトリ
    - broker_factory.py           — Settings に基づくクライアント生成
    - kabu_client.py              — KabuStationClient（httpx + websocket）
    - mock_client.py              — MockBrokerClient（テスト用）
    - execution_engine.py         — ExecutionEngine（シグナル処理／push ドレイン）
    - order_record.py             — 注文状態モデルと遷移ロジック
    - order_repository.py         — SQLite 永続化層
    - order_manager.py            — 外向け注文 API（create/send/sync/cancel）
    - reconciler.py               — 起動時リコンシリエーション
    - risk_manager.py             — Gate1/2/3 リスク制御
  - data/
    - calendar_management.py      — マーケットカレンダー管理
    - news_collector.py           — ニュース RSS 収集（セキュア）
    - jquants_client.py           — （データ取得用クライアント。コードベースで参照）
  - monitoring/
    - monitoring_db.py            — 監視用 DB 初期化・ロギング（参照して使用）
  - utils/
    - logging_setup.py            — ロギング設定ユーティリティ
    - process_priority.py         — プロセス優先度設定ユーティリティ

- config/
  - （YAML 設定ファイル群を想定: system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）
  - validate_config はこれらの存在と YAML パースをチェックします（PyYAML が必要）。

---

## 運用上の注意 / 補足

- KABUSYS_ENV:
  - development / paper_trading / live のいずれかを指定します。live は本番動作を意味し、警告や追加チェックが入ります。
  - paper_trading は MockBrokerClient を使って発注をシミュレートし、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。

- Kill / Stop の仕組み:
  - run_execution / run_monitoring はそれぞれプロセス内で stop flag（data/stop_requested.flag）や kill.flag を監視します。外部から停止を要求する際はこれらのフラグファイルを作成してください。
  - 起動時に kill.flag が存在すると、KILL_FLAG_CLEAR_ON_START の設定に応じて起動を拒否するか自動クリアして起動します（本番では自動クリアは推奨されません）。

- DB 初期化:
  - Execution / Monitoring は起動時に必要なテーブルの存在チェックと初期化を行います（init_monitoring_db / init_orders_db など）。ただし、DuckDB や SQLite ファイルの親ディレクトリは存在する必要がある場合があります（validate_config が親ディレクトリの存在を警告します）。

- 設定検証:
  - validate_config は .env の環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、データベースパス、config/*.yaml の存在と YAML パース（PyYAML がある場合）をチェックします。--strict を使うと警告も失敗扱いになります。

---

## 開発・拡張のヒント

- 実ブローカークライアント（KabuStationClient）を本番用に使う場合は、HTTP/WS の通信とエラーハンドリングに注意してください。create_broker_api の mock=False を使うと KabuStationClient が生成されます（パラメータとして api_password / base_url を渡してください）。
- Reconciler は起動時に未確定注文（OrderSent）をブローカーと突合して回復するため、send の途中でクラッシュしても整合性を保つ設計になっています。
- RiskManager のパラメータ（rate limit, circuit breaker, drawdown 等）は RiskConfig を通して調整できます。ExecutionEngine 組立時に注入してください。

---

この README はコードベースの主要機能と操作手順をまとめたものです。詳細な API や追加の設定方法は該当モジュールの docstring（ソース内コメント）を参照してください。必要であれば README に追記・整備します。