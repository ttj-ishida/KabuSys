# KabuSys

日本株自動売買システムのコアライブラリ（README）

このリポジトリは、発注エンジン、リスク管理、ブローカークライアント、監視コンポーネント、データ処理ユーティリティ等を含む自動売買システムのコア実装です。本 README はコードベースに含まれる主要な機能と、開発 / 実行のための手順をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアコンポーネント群を提供します。主な責務は次のとおりです。

- シグナルに基づく発注（ExecutionEngine）
- 注文の状態管理（OrderRecord / OrderManager）
- 発注の永続化（SQLite を利用する OrderRepository）
- ブローカー API 抽象化（KabuStationClient / MockBrokerClient）
- リスク管理（3 段階の Gate: check_signal / check_execution / check_metrics）
- 起動時のリコンシリエーション（Reconciler）
- カレンダー管理やニュース収集などのデータユーティリティ
- .env を対話式に作成するウィザードと起動前の設定検証 CLI
- 監視ループ（SystemMonitor をポーリングする run_monitoring スクリプト）

設計上、DB 操作とビジネスロジックの分離、クラッシュ/リコネシリエーション耐性、テスト容易性（モッククライアント）を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - 自動で .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - Settings クラス経由でアプリケーション設定を一元化
- 設定ツール
  - python -m kabusys.config_setup : 対話式に .env を生成 / 更新
  - python -m kabusys.validate_config : 起動前に .env と config/*.yaml を検証
- 発注エンジン / 実行
  - ExecutionEngine: シグナル読み取り → Gate チェック → 発注 → WebSocket push 処理
  - Execution 用エントリスクリプト: python -m kabusys.run_execution
- ブローカー API 層
  - BrokerAPIProtocol（Protocol）でインターフェースを規定
  - KabuStationClient: kabuステーション REST API 実装
  - MockBrokerClient: テスト / ペーパートレード用のモック（PAPER_FILL_MODE を尊重）
  - create_broker_api ファクトリで mock / live を切替
- 注文管理
  - OrderRecord: 状態遷移ロジック（状態機械）
  - OrderRepository: SQLite による永続化（orders テーブル、インデックス、ユニーク制約）
  - OrderManager: 発注ワークフロー（送信の永続化戦略、拒否・pending の扱い）
  - Reconciler: 起動時に OrderSent 状態をブローカーと突合して復旧
- リスク管理
  - RiskManager: Gate 1/2/3（余力・重複・ポジション上限 / レート制限・CB / ドローダウン）
- データユーティリティ
  - calendar_management: 営業日判定とカレンダー更新ジョブ
  - news_collector: RSS 収集（正規化・SSRF 対策・DefusedXML など）
- 監視
  - run_monitoring: SystemMonitor のポーリングループ（監視 DB は常に sqlite_path を使用）
- 開発フレンドリー
  - MockBrokerClient により kabuステーション を起動せずにローカルで動作確認可能

---

## セットアップ手順

前提
- Python 3.9+ を想定（typing 記法や一部ライブラリ互換のため）
- 必要な外部コマンドは特に無いが、実際の本番接続にはローカルの kabuステーション が必要

推奨パッケージ（主要な依存）
- httpx
- websocket-client
- duckdb
- pyyaml (設定検証で YAML パースを行う場合)
- defusedxml
- (標準ライブラリ以外の依存は requirements.txt を用意している場合はそちらを使用してください)

インストール例（仮に仮想環境を作成する場合）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows は .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install httpx websocket-client duckdb pyyaml defusedxml

（プロジェクトに requirements.txt がある場合はそれを使用）

環境変数の準備
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意/推奨:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — デフォルト data/monitoring.db
  - LOG_LEVEL — デフォルト INFO
  - KABU_API_BASE_URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID

.env の作成
- 対話式ウィザード:
  - python -m kabusys.config_setup
  - これによりプロンプトに沿って .env を生成できます
- 手動編集:
  - リポジトリルートに .env を置き、必要なキーを設定してください
- 自動ロード:
  - デフォルトでプロジェクトルートの .env と .env.local を自動読み込みします
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

検証
- python -m kabusys.validate_config
- 警告もエラーとして扱いたい場合は --strict を付ける

---

## 使い方（基本コマンド）

設定の作成・検証
- .env を対話式に作る / 更新する
  - python -m kabusys.config_setup
- 起動前チェック（.env / config/*.yaml）
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

実行（本番／ペーパートレード）
- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて MockBrokerClient を使用（development / paper_trading）、
    live は未実装で NotImplementedError が上がります
- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）

停止 / 制御
- stop_requested.flag:
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を監視し、ファイルが存在すると安全に停止します
- kill flag:
  - settings.kill_flag_path（デフォルト data/kill.flag）を用いる kill switch 機構があります
  - 起動時に kill.flag が存在すると設定により起動拒否または自動クリア（KILL_FLAG_CLEAR_ON_START=1 の場合）されます
- PID ファイル:
  - 実行時に pid ファイルを生成（デフォルト data/execution.pid）し、終了時に削除します

ログ
- setup_logging によりアプリケーション固有のログが設定されます
- LOG_LEVEL 環境変数でログレベルを指定（DEBUG / INFO / WARNING / ERROR / CRITICAL）

ペーパートレード動作
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
- PAPER_FILL_MODE によりモックの約定挙動を制御（instant / partial / never / reject）

---

## 設定項目（主な環境変数）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要な任意項目
- KABUSYS_ENV — execution の実行モード: development / paper_trading / live
- DUCKDB_PATH — DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（本番では必須に近い）

自動 .env 読込について
- 起動時に OS 環境変数 > .env.local > .env の優先順位で読み込みます
- テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

---

## ディレクトリ構成

リポジトリの主要構成（src/kabusys 配下の主要ファイル群を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込みと Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py           — BrokerAPIProtocol, データモデル, ファクトリ
    - kabu_client.py          — KabuStationClient（実装）
    - mock_client.py          — MockBrokerClient（テスト用）
    - broker_factory.py       — Settings に基づくクライアント生成
    - order_record.py         — Order の状態遷移ロジック（純粋モデル）
    - order_repository.py     — SQLite を用いた永続化層
    - order_manager.py        — 外向きの注文 API（create/send/sync/cancel）
    - execution_engine.py     — 発注エンジンのメインロジック
    - reconciler.py           — 起動時リコンシリエーション
    - risk_manager.py         — 3 段階リスクガード
    - ...（その他 execution 関連モジュール）
  - data/
    - calendar_management.py  — マーケットカレンダー管理
    - news_collector.py       — RSS ニュース収集
    - jquants_client.py       — （参照される想定の J-Quants クライアント）
    - ...（その他データ処理モジュール）
  - monitoring/
    - monitoring_db.py       — 監視用 DB 初期化と記録 API（参照される）
    - system_monitor.py      — SystemMonitor（参照される）
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

注: 上記はコードベースに含まれる主要なファイルの抜粋です。詳細は各ファイルのドキュメントストリングを参照してください。

---

## 開発上の注意点 / 動作上の注意

- live モードは安全性に注意して扱ってください。validate_config は KABUSYS_ENV=live の場合に警告（LINE 設定等）を出します。
- 起動前に必ず python -m kabusys.validate_config で設定検証を行ってください。
- ExecutionEngine は PID ファイルと kill_flag を用いた安全な起動 / 停止制御を行います。既存の kill.flag がある場合、KILL_FLAG_CLEAR_ON_START に応じて起動を拒否します。
- ブローカー API との相互作用では二相永続化等、クラッシュ後の整合性を考慮した設計がなされています（OrderSent の取り扱いなど）。
- テストやローカルデバッグでは MockBrokerClient を活用してください。PAPER_FILL_MODE によって即時約定 / 部分約定 / 保留 / 拒否の挙動を切り替えられます。

---

もし README に追加したい具体的なセクション（例: API ドキュメント、DB スキーマ、運用手順、デプロイ手順、CI 設定など）があればお知らせください。必要に応じて追記・整備します。