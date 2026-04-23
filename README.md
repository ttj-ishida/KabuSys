# KabuSys

日本株自動売買システム (KabuSys) の簡易ドキュメントです。本リポジトリは発注エンジン、監視ループ、リスク管理、カレンダー／ニュース収集などを含む自動売買プラットフォームのコア実装を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API 抽象化（kabuステーション実装およびモック実装）
- 注文状態管理（OrderRecord / OrderManager）と SQLite 永続化（OrderRepository）
- 起動時リコンシリエーション（Reconciler）
- 3 段階のリスクガード（RiskManager: Gate1/Gate2/Gate3）
- 監視ループ（SystemMonitor）と監視 DB（SQLite）
- マーケットカレンダー管理（DuckDB を利用）
- ニュース収集モジュール（RSS 取得）
- 環境設定ウィザード（`.env` の作成補助）と設定検証 CLI

設計上、DB 操作と API クライアントを明確に分離しており、テスト用途に MockBrokerClient を用意しています。

---

## 主な機能一覧

- .env 自動読み込み（プロジェクトルートにある `.env` / `.env.local`）
- 対話式 `.env` ウィザード（kabuys.config_setup）
- 起動前の設定検証ツール（kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、YAML ファイル存在チェック（PyYAML があればパースも）
- ExecutionEngine：シグナルプル型発注 + WebSocket push ドレイン
- Order 管理：状態遷移検証、DB 永続化、send/取消/sync ロジック（クラッシュ安全性を考慮）
- RiskManager：Gate1（余力・重複・ポジション上限）、Gate2（レート制限・サーキットブレーカー）、Gate3（ドローダウン監視）
- Reconciler：クラッシュ・再起動時の OrderSent 照合、ポジション差分検出
- Broker クライアント層：
  - KabuStationClient（HTTP + WebSocket）
  - MockBrokerClient（fill_mode による振る舞い制御）
- データ処理：DuckDB を用いたシグナル/カレンダー操作、ニュース収集モジュール

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `|` や `list[str]` を使用しているため）
- Git 等でリポジトリをクローン済み

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 基本的に以下をインストールしてください（プロジェクトに requirements.txt がない場合の例）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - pyyaml（YAML のパース検証を使う場合）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml pyyaml

3. プロジェクトのルートに移動（pyproject.toml や .git がルートにあることが期待されます）。

4. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
   - 任意のパスに保存する場合:
     - python -m kabusys.config_setup --env-file path/to/.env

5. .env の検証（起動前の確認）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

注意:
- PyYAML がインストールされていない場合、config/*.yaml のパース検証はスキップされます（存在チェックのみ）。
- データベース（DuckDB / SQLite）は起動時に自動的に初期化する箇所があります（例: run_execution、run_monitoring から init_monitoring_db、init_orders_db を呼ぶ）。

---

## 環境変数（主要）

必須（validate_config でもチェックされる）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要な任意項目（デフォルトあり）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API ベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番でのアラート用

その他：
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=クリア）
- PAPER_FILL_MODE — paper_trading 時のモックの約定挙動（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 専用 SQLite パス

簡単な .env の最小例（参考）
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO

---

## 使い方（主な実行コマンド）

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も FAIL 扱い: python -m kabusys.validate_config --strict

- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって振る舞いが変わります:
    - development / paper_trading: MockBrokerClient を使用（paper_trading は paper_trading 用 SQLite に記録）
    - live: 現時点では Live ブローカークライアントは未実装（NotImplementedError）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更可: MONITOR_POLL_INTERVAL（秒、デフォルト60）
  - 監視は環境にかかわらず「本番 sqlite_path」を使用します

停止方法
- 実行中のプロセスはプロジェクトルート下の data/stop_requested.flag を作成すると安全に停止処理されます（run_execution, run_monitoring がこのファイルを監視しているため）。
- kill.flag（settings.kill_flag_path、デフォルト data/kill.flag）を触ると ExecutionEngine 内の kill_switch が発動し、全 active 注文をキャンセルして停止します。KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に kill.flag を自動クリアします（注意: 本番では 0 を推奨）。

ログ・PID
- PID ファイルは settings.pid_file_path（デフォルト: data/execution.pid）に書き出されます。複数プロセスの管理に利用できます。

---

## 実装上のメモ / 注意点

- ExecutionEngine のシグナル処理は「8:50 〜 9:10」の処理と「WebSocket ドレイン（9:10 〜 15:30）」を分けて設計しています（時間は EngineConfig で変更可能）。
- OrderManager はクラッシュ耐性（OrderSent の永続化タイミング）を考慮した 2 段階永続化を行います。Reconciler はその不整合を修正するために重要です。
- RiskManager は 3 層のガード設計（Signal / Execution / Metrics）を採用しており、サーキットブレーカーやトークンバケツによるレート制御を持ちます。
- KabuStationClient は HTTP (httpx) と WebSocket (websocket-client) を用いて kabuステーション API と接続します。API の認証トークンを内部で管理します。
- MockBrokerClient はテスト・開発用途に有用で、fill_mode によって即時約定/部分約定/拒否/保留を再現できます。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージ定義、バージョン情報

- config.py
  - 環境変数の自動ロード（.env / .env.local）と Settings クラス（アプリの設定取得）

- config_setup.py
  - 対話式 .env 作成ウィザード

- validate_config.py
  - 起動前の設定検証 CLI（必須環境変数、KABUSYS_ENV、YAML ファイル等）

- run_execution.py
  - ExecutionEngine 起動スクリプト（発注エントリーポイント）

- run_monitoring.py
  - SystemMonitor（監視ループ）起動スクリプト

- execution/ (発注関連)
  - broker_api.py — Broker API のデータモデル・Protocol・ファクトリ関数
  - broker_factory.py — Settings に基づいてブローカークライアントを生成
  - kabu_client.py — kabu station REST/WebSocket クライアント実装
  - mock_client.py — MockBrokerClient（テスト用）
  - order_record.py — Order の状態遷移ロジック（純粋なビジネスロジック）
  - order_repository.py — SQLite を使った Order 永続化
  - order_manager.py — OrderStateMachine の外向け API（作成・送信・同期・取消）
  - execution_engine.py — ExecutionEngine（シグナル処理・WS ドレイン・kill_switch 等）
  - reconciler.py — 起動時リコンシリエーション
  - risk_manager.py — 3 段階リスクガード

- data/ (データ関連)
  - calendar_management.py — マーケットカレンダー管理（DuckDB）
  - news_collector.py — RSS ニュース収集（defusedxml を利用）

- monitoring/ (監視関連)
  - monitoring_db.py — 監視用 SQLite テーブル初期化・ログ機能（run_monitoring で使用）
  - system_monitor.py — システムリソース監視ロジック（run_monitoring の中核）

- utils/
  - logging_setup.py — ロガー初期化
  - process_priority.py — プロセス優先度変更補助（run_*.py で使用）

その他
- config/*.yaml — システム設定 YAML（存在する場合、validate_config が検査します）
- .env, .env.local — 環境変数ファイル（config_setup で生成）

（注）一部のスクリプトや補助モジュール（例えば generate_config.py の参照）は README のコメントに出ますが、本リポジトリに含まれていない可能性があります。validate_config は config/*.yaml ファイルが見つからない場合に警告します。

---

必要であれば以下を含めて追記できます：
- より詳細な .env の項目説明（各キーの意味とサンプル）
- デプロイ手順（systemd ユニットの例など）
- テストの実行方法（ユニットテスト／統合テストのガイド）
- API 仕様（kabu station とのやり取りの詳細）

何を優先して追加しましょうか？