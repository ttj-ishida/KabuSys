# KabuSys

日本株自動売買システム（軽量実装） — 簡易 README

概要
----
KabuSys は日本株の自動売買に関するコンポーネント群を提供するサンプル／開発向けシステムです。  
主に以下の機能を備えます。

- 環境設定ウィザード（.env の作成 / 更新）
- 起動前の設定検証 CLI（必須環境変数／config/*.yaml の確認）
- ExecutionEngine：シグナルに基づく発注フロー（Signal Pull 型）
- Broker クライアント（Mock / kabu station 用実装）
- 注文永続化（SQLite）と状態管理（OrderState マシン）
- リスク管理（3 段階ガード：Gate1/2/3、レート制限、サーキットブレーカー、ドローダウン監視）
- 再起動時のリコンシリエーション（OrderSent の突合・ポジション差分検出）
- 監視プロセス（SystemMonitor のポーリングループ）
- 一部データ処理モジュール（マーケットカレンダー管理、ニュース収集等）

主要機能一覧
--------------
- config_setup ウィザード
  - 対話式に .env を生成・更新
  - シークレット入力や選択肢をサポート
- validate_config
  - .env と config/*.yaml の基本チェック（必須変数やパス、YAML パース等）
  - --strict オプションで警告も失敗扱いにできる
- run_execution
  - ExecutionEngine を起動するエントリポイント
  - KABUSYS_ENV により paper_trading（MockBroker）/development（Mock）/live（未実装）を切替
  - kill.flag / pid 管理、WebSocket push ドレイン、シグナル処理と発注フローを実行
- run_monitoring
  - SystemMonitor を定期ポーリングして監視イベントを記録
- Broker クライアント群
  - MockBrokerClient（テスト用・fill_mode 制御）
  - KabuStationClient（httpx + websocket を利用した実装）
- 注文永続化 / OrderState 管理
  - SQLite に orders テーブルを保存・更新
  - OrderRepository / OrderManager / OrderRecord により安全に状態遷移を管理
- RiskManager
  - check_signal(), check_execution(), check_metrics() による 3 段階ガード
- Reconciler
  - 再起動時に OrderSent の注文を照合し同期、ポジション差分を検出

要件（推奨）
------------
- Python 3.10+
- ランタイム依存パッケージ（主なもの）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（YAML 内容検証を有効にする場合、任意）
- 標準ライブラリ：sqlite3, logging, threading, json など

簡易インストール例
------------------
仮想環境作成・有効化、パッケージインストール例:

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb httpx websocket-client defusedxml PyYAML
```

セットアップ手順
----------------
1. リポジトリルートに移動（README と同じ階層に .env を置く設計）
2. 仮想環境を用意し、上記依存をインストール
3. 環境変数ファイルの作成（対話式推奨）

対話式に .env を作る（推奨）:

```bash
python -m kabusys.config_setup
```

- ウィザードは .env を生成／更新します（デフォルト：プロジェクトルート/.env）。
- シークレット項目はマスク表示されます。
- 最後に保存確認があり、`y` を入力すると .env が書き込まれます。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

その他の重要な環境変数（代表）
- KABUSYS_ENV  (development | paper_trading | live)
- DUCKDB_PATH  (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH  (デフォルト: data/monitoring.db)
- LOG_LEVEL    (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABU_API_BASE_URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）

例: .env のサンプル（ウィザードで生成される形式）

```
JQUANTS_REFRESH_TOKEN=your_value_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

設定検証
--------
起動前に設定をチェックすることを推奨します:

```bash
python -m kabusys.validate_config
# 警告を厳密に扱う場合
python -m kabusys.validate_config --strict
```

- PyYAML がインストールされていれば config/*.yaml のパース検証も行います。
- 必須変数未設定や不正値は ERROR、プレースホルダ値や存在しない親ディレクトリは WARNING として報告されます。

使い方（起動）
---------------
- 実行エンジン（注文処理）を起動:

```bash
python -m kabusys.run_execution
```

- 監視プロセスを起動:

```bash
python -m kabusys.run_monitoring
```

- 監視ポーリング間隔の上書き:

```bash
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

KABUSYS_ENV の挙動
- development / paper_trading: MockBrokerClient（実際の kabu station 不要）
- paper_trading: paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離
- live: 本番ブローカークライアントは未実装（現状 NotImplementedError）

停止・制御
- プロジェクトルート/data/stop_requested.flag を作成すると run_execution/run_monitoring は次のポーリングで停止します。
- kill.flag（KILL_FLAG_PATH、デフォルト data/kill.flag）が存在すると ExecutionEngine は起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 で起動時に自動クリアする設定あり）。
- PID ファイル: default data/execution.pid（起動時に書き込み、終了時に削除）

主要ディレクトリ構成
--------------------
（ソースは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py           — Broker API の Protocol / データモデル / factory
    - broker_factory.py       — Settings に基づくブローカーファクトリ
    - kabu_client.py          — KabuStation REST/WebSocket 実装
    - mock_client.py          — テスト用モックブローカー
    - order_record.py         — OrderState / OrderRecord（状態遷移ロジック）
    - order_repository.py     — SQLite 永続化層（orders テーブル）
    - order_manager.py        — 発注フロー (create/send/sync/cancel)
    - execution_engine.py     — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py           — リコンシリエーション（OrderSent 突合）
    - risk_manager.py         — RiskManager（Gate1/2/3）
  - data/
    - calendar_management.py  — マーケットカレンダー管理（DuckDB）
    - news_collector.py       — RSS ニュース収集
    - jquants_client.py       — （参照される想定モジュール）
  - monitoring/
    - monitoring_db.py        — 監視用 DB 初期化／記録（SQLite）
    - system_monitor.py       — SystemMonitor（想定）
  - utils/
    - logging_setup.py        — ロギング初期化ユーティリティ
    - process_priority.py     — プロセス優先度設定ユーティリティ
  - config/                   — YAML 設定ファイル群（system_config.yaml 等）
  - data/                     — 実行時に使用する DB / フラグファイルを置く（生成される）

補足・運用上の注意
-----------------
- .env は絶対に Git 等へコミットしないでください。config_setup.py のヘッダにも注意書きがあります。
- 本番（live）稼働前は validate_config を実行し、特に LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を確認してください。
- ExecutionEngine は外部からの push（WebSocket）とシグナル読み込み（DuckDB）を組み合わせて動作します。実運用では kabu station の稼働とネットワーク設定が必要です。
- Reconciler はクラッシュや再起動時の安全性を高めるために設計されていますが、ブローカー側の API 仕様や稼働状況に応じて運用ルールを整備してください。

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

おわりに
--------
この README はコードベースの主要点をまとめた概要です。実際の運用や拡張を行う際は各モジュールの docstring とソースコードを参照し、テスト環境で十分に動作確認を行ってください。必要であれば README の補足（デプロイ例、systemd ユニット、Dockerfile、CI 流れなど）を追加できます。