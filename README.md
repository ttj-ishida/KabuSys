# KabuSys

日本株自動売買システムの一部（設定管理・実行エンジン・監視・データ基盤ユーティリティ）を含む Python パッケージです。

## プロジェクト概要

KabuSys は次のような目的で設計されたモジュール群を提供します。

- 設定管理 (.env 読み込み・ウィザード・検証)
- 発注実行エンジン（ExecutionEngine）
- ブローカークライアント抽象化（kabu station 実装 / モック実装）
- 注文状態管理（OrderRecord / OrderRepository / OrderManager）
- 起動時リコンシリエーション（Reconciler）
- 3段階リスクガード（RiskManager）
- 監視ループ（SystemMonitor 起動スクリプト）
- データユーティリティ（マーケットカレンダー、ニュース収集など）

このリポジトリに含まれるコードは、実際の証券会社 API と接続するための層（kabu station）と、テスト・開発用のモック（MockBrokerClient）を併せ持つ構成です。

---

## 機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup で対話的に .env を作成/更新
- 設定検証 CLI: python -m kabusys.validate_config（--strict オプションで警告も失敗扱い）
- 実行エンジン: python -m kabusys.run_execution（ExecutionEngine を起動）
  - シグナルループ（発注時間帯）と WebSocket ドレインループのサポート
  - Kill Switch（kill.flag）検出と全注文キャンセル機能
  - Paper trading モード用に本番 DB と分離された SQLite を使用
- 監視プロセス: python -m kabusys.run_monitoring（SystemMonitor のポーリングループ）
- ブローカークライアント抽象化:
  - create_broker_api(mock=True/False) を介して MockBrokerClient / KabuStationClient を生成
- 注文状態管理:
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（発注フローの高レベル API）
- リスク管理:
  - Gate 1: シグナルレベル（余力・重複・ポジション上限）
  - Gate 2: エグゼキューションレベル（レート制限・サーキットブレーカー）
  - Gate 3: メトリクス（ドローダウン）監視
- リコンシリエーション: 起動時に OrderSent の注文を突合して状態を復元し、ポジション差分を検出

---

## セットアップ手順

以下はローカルで実行するための簡易手順例です。

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（最低限の例）
   - pip install httpx websocket-client duckdb defusedxml pyyaml
   - （本プロジェクト内に requirements.txt がある場合は pip install -r requirements.txt を使用）

   推奨される依存:
   - httpx: REST API 呼び出し
   - websocket-client: WebSocket push
   - duckdb: 信号・カレンダーデータ等の分析
   - pyyaml: validate_config が YAML のパース検証を行う場合
   - defusedxml: RSS パースの安全対策

3. .env の準備
   - python -m kabusys.config_setup を実行して対話式に .env を生成するのが簡単です。
   - 生成した .env は Git 管理下にコミットしないでください（README にもその旨注記されます）。

4. 設定の検証
   - python -m kabusys.validate_config
   - 重要: --strict を付けると警告も失敗（exit 1）として扱います。

注意:
- 自動 .env 読み込みはデフォルトで有効です（プロジェクトルートに .env があると読み込みます）。
- 自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - live 設定は本番動作であり、validate_config で警告が出ます
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード時の SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL（kabu station の base URL、デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）

その他:
- KILL_FLAG_CLEAR_ON_START（0/1、起動時に kill.flag を自動クリアするか）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒、デフォルト 60）

.env の例（機密情報は空白やプレースホルダにしてください）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト: 60）

- テスト用モック・API
  - create_broker_api(mock=True, fill_mode="instant" | "partial" | "never" | "reject")
  - MockBrokerClient は単体テストでの発注・約定振る舞いを模擬できます

---

## 注意事項 / 運用上のヒント

- .env を絶対に Git にコミットしないでください
- KABUSYS_ENV=live の場合は特に LINE 通知設定や KILL_FLAG の扱い等を慎重に確認してください
- 起動時 kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=0（デフォルト）では起動を拒否します
- ExecutionEngine は PID ファイルを data/execution.pid 等に書きます（pid ファイルパスは PID_FILE_PATH で上書き可能）
- DB パスの親ディレクトリが存在しない場合は起動時に自動作成されることがありますが、事前に作成して権限等を確認してください

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数読み込み・Settings
    - config_setup.py        — 対話式 .env ウィザード
    - validate_config.py     — 起動前設定検証 CLI
    - run_execution.py       — 実行エンジン起動スクリプト
    - run_monitoring.py      — 監視プロセス起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py        — BrokerAPIProtocol / データモデル / ファクトリ
      - broker_factory.py    — Settings に基づくブローカー生成
      - kabu_client.py       — kabu station REST クライアント実装
      - mock_client.py       — テスト用モック実装
      - order_record.py      — 注文状態モデル・遷移
      - order_repository.py  — SQLite 永続化層
      - order_manager.py     — 発注フロー (create/send/sync/cancel)
      - execution_engine.py  — ExecutionEngine（セッション管理）
      - reconciler.py        — 起動時のリコンシリエーション
      - risk_manager.py      — 3段階リスクガード
      - ...（その他補助モジュール）
    - data/
      - calendar_management.py — マーケットカレンダー管理（DuckDB）
      - news_collector.py      — RSS ニュース収集
      - ...（J-Quants クライアント等）
    - monitoring/
      - monitoring_db.py      — 監視 DB 初期化 / ログ保存
      - system_monitor.py     — システム監視ロジック
    - utils/
      - logging_setup.py      — ロギング設定ユーティリティ
      - process_priority.py   — プロセス優先度設定ユーティリティ

上記は主なファイルの一覧です。各モジュールに細かい責務分離がなされており、単体テストしやすい設計になっています。

---

## 参考: 開発時のワークフロー例

1. 仮想環境を作成して依存をインストール
2. python -m kabusys.config_setup で .env を生成
3. python -m kabusys.validate_config で設定を確認
4. ローカル検証は KABUSYS_ENV=development または paper_trading にして実行
   - python -m kabusys.run_execution
   - python -m kabusys.run_monitoring

---

問題や追加のドキュメントが必要であれば、どの部分（例: ExecutionEngine の詳細、OrderManager のフロー、テスト方法など）を深掘りしたいか教えてください。