# KabuSys

日本株自動売買システム（KabuSys）の軽量実装サンプルリポジトリ。

この README ではプロジェクト概要、主要機能、セットアップ方法、基本的な使い方、ソースのディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買エンジンのコアコンポーネントを提供するライブラリ兼実行スクリプト群です。  
主な目的は以下の通りです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API の抽象化（実運用向けの kabuステーション とテスト用の Mock 実装）
- 注文ライフサイクル管理（OrderRecord / OrderManager / OrderRepository）
- リスクガード（3 段階：Gate1〜Gate3）
- 起動時リコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor を使ったポーリングループ）
- 環境設定ウィザード / 設定検証 CLI

設計方針として、ビジネスロジック（注文状態遷移等）と永続化（SQLite）／API 呼び出し（kabu station）を明確に分離しています。またテスト用に MockBrokerClient を用意しており、実際の接続無しでロジックの検証ができます。

---

## 主な機能（抜粋）

- 環境設定ウィザード（.env 生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml を起動前検査）: python -m kabusys.validate_config
- ExecutionEngine（シグナル pull → 発注 → push drain）
- Order 管理:
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（発注・同期・キャンセルフロー）
- ブローカー抽象:
  - KabuStationClient（kabuステーション REST 実装）
  - MockBrokerClient（テスト用）
  - create_broker_api ファクトリ
- RiskManager（Gate1: シグナル、Gate2: 実行、Gate3: ドローダウン）
- Reconciler（起動時の OrderSent 照合とポジション差分検出）
- Data モジュール:
  - マーケットカレンダー管理（DuckDB ベース）
  - ニュース収集（RSS → 前処理 → raw_news 保存）
- 監視処理（run_monitoring.py）: SQLite / DuckDB を用いて定期的に監視情報を収集

---

## 要件

- Python 3.10 以上（型アノテーションの union 型（|）などを使用しているため）
- 推奨パッケージ（例）
  - duckdb
  - httpx
  - websocket-client
  - pyyaml
  - defusedxml
- 標準で利用される組み込みモジュール: sqlite3, logging, threading, datetime など

（実際にはプロジェクトの requirements.txt を用意している前提で pip install -r requirements.txt を推奨します。無ければ上記パッケージを個別インストールしてください。）

---

## 初期セットアップ

1. リポジトリをクローンし、仮想環境を作成して有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールします（例）。
   - pip install duckdb httpx websocket-client pyyaml defusedxml

3. .env の準備（推奨フロー）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（下に最小例あり）

4. 設定検証（起動前に必ず実行）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱い（exit 1）

.env の最低サンプル（.env.example を参照して作成してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

注意:
- 自動ロード順序: OS 環境変数 > .env.local > .env（config.py の実装）
- 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（簡易ガイド）

- 設定ウィザード（.env 生成／更新）
  - python -m kabusys.config_setup
  - 完了後、python -m kabusys.validate_config で検証

- 設定検証
  - python -m kabusys.validate_config
  - 警告を失敗扱いにする: python -m kabusys.validate_config --strict

- 実行エンジン（本番またはペーパートレード）
  - python -m kabusys.run_execution
  - 動作:
    - Settings から環境を読み取り、paper_trading または development では MockBrokerClient を使用
    - SQLite / DuckDB に接続し ExecutionEngine を起動
    - stop フラグ: data/stop_requested.flag を置くことで停止を促せます
    - PID 表示: data/execution.pid に PID を書き出します
    - kill.flag の扱い: 起動時の KILL_FLAG_CLEAR_ON_START 設定で挙動が変わります

- 監視プロセス
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔変更（デフォルト 60 秒）
  - 監視も data/stop_requested.flag により終了

- テスト／開発向け
  - MockBrokerClient を用いて発注フローやリコンシリエーション、RiskManager の挙動を単体でテスト可能

---

## 設定・運用に関する注意点

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 重要な環境変数（抜粋）:
  - KABUSYS_ENV: development | paper_trading | live
    - live の場合は本番注意（validate_config で警告）
  - DUCKDB_PATH / SQLITE_PATH: データベースファイルのパス（デフォルトは data/ 以下）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番での通知に必要
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

- 停止・kill フラグ:
  - 停止要求: data/stop_requested.flag を作成すると監視・実行ループが検知して終了します
  - kill flag（強制停止用）: settings.kill_flag_path（デフォルト data/kill.flag）によりエンジンが全注文をキャンセルして停止します

- リスク管理:
  - RiskManager は 3 段階のガードを持ち、安全性を高める設計になっています（重複注文防止、レート制限、ドローダウン監視、サーキットブレーカー等）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — .env 自動読み込み、Settings クラス（環境変数ラッパ）
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine の起動スクリプト（メイン実行）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - broker_api.py — Broker API のデータモデル / Protocol / ファクトリ
  - kabu_client.py — kabu ステーション REST クライアント（HTTP/WebSocket 実装）
  - mock_client.py — MockBrokerClient（fill_mode 等のテスト用）
  - broker_factory.py — Settings に基づいてクライアントを生成するファクトリ
  - order_record.py — 注文状態と遷移ロジック（純粋なビジネスロジック）
  - order_repository.py — SQLite を用いた永続化層（orders テーブル）
  - order_manager.py — 注文フローの外向き API（create/send/sync/cancel）
  - execution_engine.py — セッション制御（シグナル処理・push drain 等）
  - reconciler.py — 起動時のリコンシリエーション（OrderSent 照合、ポジション差分）
  - risk_manager.py — 3 段階のリスクガード（設定クラス、実行ロジック）

- src/kabusys/data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB と J-Quants）
  - news_collector.py — RSS ベースのニュース収集と前処理（DefusedXML 等を使用）
  - （その他 jquants_client などを想定）

- src/kabusys/monitoring/
  - monitoring_db.py — 監視用 SQLite テーブル初期化・ログ機能（run_monitoring/run_execution と連携）
  - system_monitor.py — 監視ロジック（SystemMonitor）

- src/kabusys/utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度設定ユーティリティ

（上記のうち一部ファイルは README に抜粋で登場します。実装の詳細は各ファイルを参照してください。）

---

## 開発・運用上のヒント

- テスト環境では KABUSYS_ENV=paper_trading を使い MockBrokerClient により実データと分離された DB（PAPER_TRADING_SQLITE_PATH）が使われます。
- 起動前に validate_config を実行することで、.env の欠落や config/*.yaml の不備を早期に検出できます。PyYAML が無い場合は YAML の中身検証はスキップされます（警告）。
- ExecutionEngine は PID ファイルと stop/kill フラグを使って外部制御を行います。運用時はこれらのファイル管理に注意してください。
- Reconciler によりクラッシュ復旧時の注文状態同期とポジション差分検出を実行できます。運用時は起動ログを確認し、差分が検出された場合は手動確認も考慮してください。

---

以上が本リポジトリの README 相当の概要です。実装の詳細や追加ユーティリティ（generate_config.py など）が別途ある場合はそれらのドキュメントも併せて参照してください。必要であれば README をプロジェクトの実際の依存ファイル（requirements.txt、.env.example、運用手順書）に合わせてカスタマイズできます。