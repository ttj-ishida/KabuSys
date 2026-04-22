# KabuSys

日本株自動売買システムの一部を切り出したモジュール群。  
このリポジトリには環境設定・検証ツール、監視ループ、発注エンジンおよび関連ライブラリ（ブローカークライアント、リスクガード、永続化層、カレンダー管理、ニュース収集など）が含まれます。

---

## 概要

KabuSys は、kabuステーション（ローカルのブローカープロキシ）や外部 API（例: J-Quants）と連携して日本株の自動発注を行うためのライブラリ／ランタイムです。本コードベースには以下のような責務が含まれます。

- 環境設定読み込み・ウィザード（.env 作成支援）
- 起動前設定の静的検証（必須環境変数や config/*.yaml のチェック）
- ExecutionEngine（シグナルに基づく発注ループ）
- Broker クライアント（kabu station 実装 + モック）
- 注文状態管理・永続化（SQLite）
- リスク管理（Gate1〜3：余力・レート制限・ドローダウン等）
- 起動時リコンシリエーション（OrderSent 状態の突合）
- 監視ループ（SystemMonitor）
- データユーティリティ（マーケットカレンダー、ニュース収集など）

---

## 主な機能一覧

- .env ウィザード（対話式）: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
- 発注エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV に応じて MockBrokerClient を利用（paper_trading / development）
  - 発注処理は Signal Queue → OrderManager → Broker API のフロー
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
- Broker API レイヤ
  - KabuStationClient: kabuステーション REST / WebSocket 対応
  - MockBrokerClient: テスト用の振る舞い（fill_mode 切替可能）
- 注文永続化（SQLite）と OrderRecord の状態遷移検証
- リスク管理（position limit / utilization / rate limit / circuit breaker / drawdown）
- カレンダー管理（DuckDB ベース）と翌営業日計算
- ニュース収集（RSS → raw_news 保存、URL 正規化、SSRF 対策等）

---

## 要件（推奨）

- Python 3.9+
- パッケージ例（実行に必要な最低限、環境によって差分あり）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML (config YAML のパース検証用)
  - defusedxml (RSS パーシングの安全化)
  - その他（sqlite3 は標準搭載）
- 開発ツール:
  - git
  - （オプション）venv / virtualenv

依存はプロジェクトに requirements.txt があればそれを使うか、上記パッケージを pip でインストールしてください。

例:
pip install duckdb httpx websocket-client pyyaml defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install -r requirements.txt
   または（requirements.txt がない場合の例）
   pip install duckdb httpx websocket-client pyyaml defusedxml

4. 初期 .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
     → 対話に答えるとプロジェクトルートの .env（デフォルト）に保存されます
   - 手動で .env を作る場合は .env.example（存在するなら）を参考にしてください

5. 設定検証
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります

備考:
- 自動的に .env を読み込む挙動は、プロジェクトルート（.git または pyproject.toml を検出）を基準に行われます。  
- 自動ロードを無効化する場合は環境変数を設定:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）

任意／推奨（代表例）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知設定（本番では必須推奨）
- KILL_FLAG_CLEAR_ON_START — 起動時に既存の kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE — paper_trading 時の挙動（instant / partial / never / reject）

validate_config や Settings クラスが上記の妥当性チェックを行います。

.env の読み込み優先順:
OS 環境変数 > .env.local > .env
（._load_env_file の挙動により .env.local は上書きされます）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（対話式 .env 作成）
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 発注エンジン起動（Execution）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録
  - 起動時に data/stop_requested.flag があれば起動しません
  - 起動中に data/stop_requested.flag を作成すると安全に停止します
  - 発注は ExecutionEngine により 8:50〜9:10 のシグナル処理、9:10〜15:30 の push ドレインのフローで実行

- 監視ループ起動（SystemMonitor）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します

- ローカルテスト / モック
  - create_broker_api(mock=True, fill_mode=...) で MockBrokerClient を利用可能
  - PAPER_FILL_MODE や settings.paper_sqlite_path を使い paper_trading を構成

停止方法:
- 実行中にプロジェクトルートの data/stop_requested.flag を作成すると実行ループは検知して停止します。
- kill.flag（設定で指定）を置くと ExecutionEngine は起動を拒否または即座に kill_switch を発動します。KILL_FLAG_CLEAR_ON_START=1 の場合、起動時に自動クリアされます。

ログ:
- ログレベルは LOG_LEVEL 環境変数で制御します。デフォルト INFO。

---

## データベース初期化

- orders テーブル（SQLite）を作成するユーティリティ:
  - init_orders_db(conn: sqlite3.Connection)
  - init_monitoring_db(...) など監視テーブル初期化用関数が monitoring モジュールにあります
- Execution / Monitoring の起動スクリプト内では起動時に DB スキーマの存在を保証する処理が入っています（冪等にテーブル作成）。

---

## 開発者向けメモ

- プロジェクトルート検出: config モジュールは .git または pyproject.toml を親ディレクトリから探索してプロジェクトルートを特定し、その場所の .env / .env.local を読み込みます。これにより CWD に依存しない動作が可能です。
- .env 読み込みの上書きルール:
  - 最初に .env を読み込む（既存 OS 環境変数を上書きしない）
  - 次に .env.local を読み込み、override=True により既存値を上書き（ただし OS 環境変数は protected）
- validate_config は PyYAML がインストールされている場合に config/*.yaml のパース検証を行います。インストールされていない場合は警告を出してスキップします。
- ExecutionEngine の重要な概念:
  - Gate 1: check_signal（余力・重複・ポジション上限）
  - Gate 2: check_execution（レート制限・サーキットブレーカー）
  - Gate 3: check_metrics（ドローダウン・キルスイッチ）
  - Reconciler は起動時に OrderSent 状態の注文をブローカーと照合して整合性を回復します
- Broker の WebSocket push は KabuStationClient.stream_push で blocking 呼び出し（stop_event を受け取り再接続ループあり）。WebSocket がないモックではスキップされます。

---

## ディレクトリ構成（抜粋）

プロジェクトルートの src/kabusys 以下の主なファイル／パッケージ:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py           — Broker API の Protocol / データモデル / ファクトリ
    - kabu_client.py          — kabu station HTTP/WebSocket 実装
    - mock_client.py          — テスト用モック
    - broker_factory.py       — Settings に応じたブローカークライアント生成
    - order_record.py         — Order 状態遷移（純粋ロジック）
    - order_repository.py     — SQLite ベースの永続化層
    - order_manager.py        — 発注フロー（作成・送信・同期・キャンセル）
    - execution_engine.py     — セッション管理・シグナル処理・push ドレイン
    - reconciler.py           — 起動時リコンシリエーション
    - risk_manager.py         — Gate1〜3 のリスク制御ロジック
  - data/
    - calendar_management.py  — マーケットカレンダー管理（DuckDB）
    - news_collector.py       — RSS ニュース収集・正規化
    - jquants_client.py       — （J-Quants 連携用クライアント：参照あり）
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化/ロギング（参照あり）
    - system_monitor.py      — システム監視ロジック（参照あり）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（参照あり）
    - process_priority.py    — プロセス優先度設定ユーティリティ（参照あり）

（実際のリポジトリではさらに細分化されたファイル群が存在します。上は主要ファイルの抜粋です。）

---

## よくある Q&A / トラブルシューティング

- validate_config で必須環境変数エラーが出る:
  - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD を .env または OS 環境に設定してください。ウィザードで生成できます。
- 発注したが broker_order_id が DB に残っている・状態が OrderSent のまま:
  - ネットワーク障害や broker 側のタイムアウトで OrderSent のまま残ることがあります。Reconciler（起動時）や sync_order による突合で回復を試みます。
- 本番での注意:
  - KABUSYS_ENV=live を使う場合、LINE 通知設定や KILL_FLAG の設定などを慎重にしてください。validate_config は live 環境で追加チェックを行います。

---

必要があれば、README に記載する具体的な .env.example のテンプレートや、requirements.txt の推奨内容、開発用のテスト手順（ユニットテスト・統合テストの実行例）を追加で作成します。どの部分を深掘りすればよいか教えてください。