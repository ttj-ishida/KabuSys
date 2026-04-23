README
======

概要
----
KabuSys は日本株向けの自動売買基盤の一部を構成するライブラリ兼実行スクリプト群です。本リポジトリには設定管理、発注エンジン（ExecutionEngine）、ブローカークライアントの抽象化、リスクガード、リコンシリエーション、監視ループ、ニュース収集・マーケットカレンダー処理などの主要コンポーネントが含まれます。

主な目的は「ローカル環境で安全に発注ロジックを開発・検証できること」であり、paper_trading（ペーパートレード）/development（開発）モードでは Mock ブローカーを使って本番環境と分離して動作します。KABUSYS_ENV=live（本番）時の Live ブローカークライアントは未実装の箇所があります（RuntimeError / NotImplementedError を投げます）。

機能一覧
--------
- .env による設定管理・自動読み込み（.env、.env.local）
- 対話式設定ウィザード（python -m kabusys.config_setup）で .env を生成/更新
- 設定検証 CLI（python -m kabusys.validate_config）で環境変数および config/*.yaml の整合性チェック
- ExecutionEngine（シグナル読み取り→Gate1/2→発注→push ドレイン→Gate3）による発注ワークフロー
- OrderRecord（状態遷移を厳密に管理する FSM）＋ OrderRepository（SQLite 永続化）
- OrderManager：発注フロー（送信、同期、キャンセル）とクラッシュ安全な永続化手順
- Broker API 抽象 Protocol（MockBrokerClient 実装を同梱、kabu station クライアント実装有）
- RiskManager：3段階リスクガード（シグナルレベル、実行レベル、メトリクスレベル）
- Reconciler：起動時に OrderSent の不確定注文をブローカーと突合して同期・復旧
- 監視ループ（run_monitoring）によるシステムメトリクス・ログ収集
- data 側モジュール：マーケットカレンダー管理、ニュース収集等
- DuckDB（分析データ）と SQLite（監視・注文永続化）を併用

前提・依存関係
---------------
- Python 3.10 以上を推奨（typing の表記などに依存）
- 標準ライブラリ：sqlite3, logging, threading, pathlib 等
- 推奨外部パッケージ（用途別）:
  - duckdb — DuckDB 接続
  - httpx — KabuStation の REST 呼び出し（KabuStationClient）
  - websocket-client — WebSocket push の受信
  - defusedxml — RSS パースの安全対策
  - PyYAML — config/*.yaml のパース（validate_config の一部を有効化）
- その他ツール（任意）: git（プロジェクトルート検出に使用）

セットアップ手順
----------------
1. Python 環境を準備
   - 推奨: virtualenv / venv を用いた仮想環境
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS/Linux
     .venv\Scripts\activate      # Windows
     ```

2. 必要パッケージをインストール
   - requirements.txt は同梱されていない想定のため、手動で必要パッケージを入れる例:
     ```
     pip install duckdb httpx websocket-client defusedxml PyYAML
     ```
   - PyYAML は任意（validate_config で YAML の中身チェックを行う場合に必要）。

3. プロジェクトルートの検出
   - 自動で .env を読み込む仕組みは、パッケージファイルから上向きに .git または pyproject.toml を探して「プロジェクトルート」を特定します。配布パッケージ化の際は pyproject.toml を含めることを推奨します。

4. .env の作成（対話式ウィザード推奨）
   - 対話式に .env を作る:
     ```
     python -m kabusys.config_setup
     ```
   - これにより .env を生成/更新できます（デフォルトはプロジェクトルートの .env）。ウィザードは .env が既にある場合は現在値を読み込み、Enter で再利用できます。

環境変数 — 必須 / 任意
-----------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意（または推奨）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
- LINE_USER_ID — LINE 通知先ユーザーID（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag 自動クリア（0/1、デフォルト: 0）
- その他: PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, MONITOR_POLL_INTERVAL など（config.py を参照）

簡単な .env の例
-----------------
（config_setup ウィザードを使うことを推奨しますが、手動例を示します）
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

設定検証
--------
起動前に設定の簡易チェックを行うには:
```
python -m kabusys.validate_config
```
--strict を付けると警告も FAIL 扱いで exit(1) になります:
```
python -m kabusys.validate_config --strict
```
validate_config は必須環境変数の未設定、プレースホルダ値の検出、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・YAML パース（PyYAML がインストールされていれば）などをチェックします。

実行方法（主要スクリプト）
---------------------------
- 発注エンジンを起動（本番フロー）
  ```
  python -m kabusys.run_execution
  ```
  動作ポイント:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH で上書き可能）へ記録して本番 DB と分離します。
  - PID ファイルや stop flag（data/stop_requested.flag）を監視して graceful shutdown を行います。
  - 起動時に Reconciler による同期処理を実行（OrderSent の復旧など）。

- 監視ループを起動（システム監視）
  ```
  python -m kabusys.run_monitoring
  ```
  動作ポイント:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト: 60 秒）。
  - 監視用は常に（環境にかかわらず）本番 sqlite_path を使用します（config の仕様）。

- 対話式 .env ウィザード
  ```
  python -m kabusys.config_setup
  ```

注意: live（本番）動作
--------------------
- settings.is_live (= KABUSYS_ENV=live) の場合は、特に通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の確認や kill flag の取り扱いなどを慎重に行ってください。
- BrokerClientFactory は現状 development/paper_trading で MockBrokerClient を返す設計で、live 用の実装は未実装 / 非推奨です（NotImplementedError）。

アーキテクチャ上の注意点
----------------------
- 発注フローはクラッシュ安全性を考慮して設計されています。OrderSent の永続化 → ブローカー呼び出し → broker_order_id 永続化 → OrderAccepted 永続化、という 2 相的処理により、途中クラッシュ時も Reconciler で回復可能です。
- OrderRepository の DB スキーマには「同一 signal_id の active 注文を 1 件に制限する」ユニークインデックスが設定されています（レース対策）。
- RiskManager は Gate1（信号レベル）、Gate2（レート制限・サーキットブレーカー）、Gate3（ドローダウン監視）からなる多段防御を備えています。
- ExecutionEngine はシグナルのバルク処理（8:50-9:10）と WebSocket push のドレイン（9:10-15:30）を想定したセッションモデルです。

ディレクトリ構成（抜粋）
---------------------
以下はソースツリーの主要ファイル／モジュールの一覧（src/kabusys 以下）。実際のファイル数は多いため主要部分のみ抜粋しています。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込みと Settings クラス
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - data/
    - calendar_management.py  — マーケットカレンダー管理（DuckDB）
    - news_collector.py       — RSS ニュース収集
    - jquants_client.py       — J-Quants API クライアント（別ファイル）
  - execution/
    - broker_api.py           — Broker API の Protocol / データモデル / factory
    - kabu_client.py          — KabuStation の REST/WebSocket クライアント
    - mock_client.py          — Mock ブローカ実装（テスト用）
    - broker_factory.py       — Settings に基づくクライアント生成
    - order_record.py         — 注文状態遷移ロジック（FSM）
    - order_repository.py     — SQLite 永続化層
    - order_manager.py        — 外向け発注 API（create/send/sync/cancel）
    - execution_engine.py     — ExecutionEngine（セッション管理）
    - reconciler.py           — リコンシリエーション（復旧）
    - risk_manager.py         — リスクガード（Gate1-3）
  - monitoring/                — 監視関連（monitoring_db, system_monitor 等）
  - utils/
    - logging_setup.py        — ロギング初期化
    - process_priority.py     — プロセス優先度設定ユーティリティ

運用上のファイル
----------------
- data/stop_requested.flag — このファイルが存在するとホストプロセスは停止処理を行います（外部から停止指示を出すために使用）。
- data/kill.flag           — kill switch（実行中の起動拒否や即時停止に使用）。KILL_FLAG_CLEAR_ON_START により起動時に自動クリア可。
- data/execution.pid       — ExecutionEngine が書き出す PID ファイル（設定で変更可）。

追加情報 / 開発メモ
-------------------
- 自動 .env 読み込みは OS 環境変数 > .env.local > .env の優先順位で行われ、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます（テスト時に便利）。
- config/*.yaml の存在チェックとパースは validate_config で行います（PyYAML がないと中身検証はスキップされます）。
- 本リポジトリは本番発注を直接行う危険性があるため、本番運用時は必ず設定検証・監視・通知設定を確認してください。

貢献・ライセンス
----------------
（この README にライセンス情報やコントリビューション手順は含めていません。必要に応じて pyproject.toml / LICENSE を追加してください。）

補足
----
不明点や追加で README に記載したい項目（例: deployment 手順、CI 設定、詳細な DB スキーマ、API レートやメトリクス設計など）があれば指示してください。README をそれらに合わせて拡張します。