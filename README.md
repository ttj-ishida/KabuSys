KabuSys
=======

プロジェクト概要
----------------
KabuSys は日本株の自動売買を目的とした軽量なフレームワークです。本プロジェクトは以下の機能を備え、ローカル開発・ペーパートレード・将来的な本番接続を想定した設計になっています。

- シグナルに基づく発注フロー（ExecutionEngine）
- 注文の状態管理（OrderRecord / OrderManager）と永続化（SQLite）
- ブローカー API 抽象化（kabu station クライアント + Mock クライアント）
- 起動時のリコンシリエーション（Reconciler）
- 3段階のリスクガード（RiskManager）
- DuckDB を用いたデータ管理（シグナル・ポートフォリオ等）
- 監視用ポーリングループ（SystemMonitor を使った監視）
- .env 対応の設定管理 / 対話式設定ウィザード / 設定検証ツール

主なユースケースは、ローカルでの開発・テスト（mock broker）およびペーパートレード環境での動作確認です。将来的に本番の kabu station クライアント（Live）を接続する設計が取られていますが、現状では Live クライアントは未実装の箇所があります（BrokerClientFactory が NotImplementedError を投げます）。

主な機能一覧
-------------
- 環境設定ウィザード（kabusys.config_setup.run_wizard）で .env を生成・更新
- .env 自動ロード（プロジェクトルート検出に基づき .env / .env.local を読み込み）
- 設定検証 CLI（kabusys.validate_config）で必須環境変数や config/*.yaml を事前チェック
- ExecutionEngine：シグナル取り込み、Gate1〜3 によるリスクチェック、発注・push ドレイン処理
- OrderManager / OrderRecord：注文の状態遷移管理と broker とのやり取り（永続化とクラッシュ耐性考慮）
- BrokerAPI 抽象化：MockBrokerClient（テスト用）、KabuStationClient（REST/WebSocket 実装）
- Reconciler：起動時に OrderSent 状態を照合し自動復旧、ポジション差分検出
- RiskManager：余力・重複・ポジション上限・レート制限・サーキットブレーカー・ドローダウン監視
- Data モジュール：マーケットカレンダー管理、RSS ニュース収集など
- 監視プロセス（run_monitoring.py）：SQLite / DuckDB で監視情報を保存・確認

セットアップ手順
----------------
前提:
- Python 3.9+（コードは型アノテーション等を使用）
- pip/pipenv/poetry 等で依存パッケージをインストール

推奨インストール例（仮想環境を使用）:
- 必要パッケージ（例）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（設定検証で YAML パースを有効にする場合）
  - その他（プロジェクトで別途指定している場合）

例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb httpx websocket-client defusedxml PyYAML

環境変数（.env）:
- プロジェクトルートに .env を配置すると、自動で読み込まれます（.env.local があれば優先して上書き）。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

重要な環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
  - KABU_API_BASE_URL — kabu station API のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用
  - KILL_FLAG_CLEAR_ON_START — 0/1（本番では 0 推奨）

サンプル .env（生成ウィザードでも作成可能）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

使い方
------
1) 対話式ウィザードで .env を作る / 更新する
  python -m kabusys.config_setup
  - 対話に従ってキーを入力します。既存値があれば Enter で再利用できます。
  - 保存後に validate_config を実行することを推奨します。

2) 設定検証（起動前チェック）
  python -m kabusys.validate_config
  - 警告とエラーを表示します。終了コード:
    - 0: OK（エラーなし・警告なし または 警告あり）
    - 1: エラーあり または --strict で警告も FAIL 扱い
  例（厳密モード）:
    python -m kabusys.validate_config --strict

3) 実行エンジンを起動（発注処理）
  python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient を使用して安全に動作します。
  - KABUSYS_ENV=live の Live ブローカーは現状未実装（BrokerClientFactory が NotImplementedError を投げます）。
  - 起動時に data/execution.pid（デフォルト）に PID を書き込み、kill.flag を検出すると起動拒否または停止処理を行います。
  - 停止するにはプロジェクトルートの data/stop_requested.flag を作成しても停止可能。

4) 監視ループを起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 監視用は常に production の sqlite_path を使用します（監視 DB は環境にかかわらず同じファイルを参照）。

5) 開発時の Mock Broker 操作
  - MockBrokerClient は paper_trading/development 向けに発注をシミュレートします。
  - fill_mode（instant/partial/never/reject）で約定挙動を切り替えられます（Settings.paper_fill_mode で指定）。

注意点 / 運用上のポイント
- .env は機密情報を含むため Git にコミットしないでください（config_setup.py でも注意喚起あり）。
- KABUSYS_ENV=live を使う場合は LINE 通知設定等の本番ガードを必ず確認してください（validate_config でも WARN が出ます）。
- 起動時の kill.flag（KILL_FLAG_PATH）により安全停止や起動拒否を行います。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアしますが、本番では 0 を推奨します。
- config/*.yaml のテンプレートはスクリプト scripts/generate_config.py で生成できる想定です（プロジェクトに合わせて確認してください）。PyYAML がインストールされていると config YAML のパース検証が行われます。

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys をルートとした主要モジュールの一覧）

- src/kabusys/
  - __init__.py  — パッケージ定義・バージョン
  - config.py  — 環境変数/.env の読み込みと Settings 抽象化
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（発注処理）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - execution/
    - broker_api.py — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py — Settings に応じたブローカー生成
    - kabu_client.py — kabu station REST/WebSocket 実装
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — 注文状態遷移ロジック（ビジネスロジック）
    - order_repository.py — SQLite 永続化層
    - order_manager.py — 注文作成・送信・同期・取消の上位 API
    - execution_engine.py — Signal Queue 型発注エンジン（本体）
    - reconciler.py — 起動時リコンシリエーション
    - risk_manager.py — 3段階リスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（DefusedXML、DuckDB 保存） 
    - (その他 data 関連モジュール)
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化・記録（SQLite）
    - system_monitor.py — システム指標監視（CPU/MEM/DISK 等）
  - utils/
    - logging_setup.py — ロギング初期化
    - process_priority.py — プロセス優先度設定

ファイル / ディレクトリ（ランタイム生成）
- data/ — DB ファイル・PID・flag 等を格納するディレクトリ（実行時に自動作成されることがある）
  - data/kabusys.duckdb（デフォルト）
  - data/monitoring.db（監視用 SQLite）
  - data/paper_trading.db（ペーパートレード用 SQLite）
  - data/execution.pid（実行時 PID）
  - data/stop_requested.flag（実行停止要求）
  - data/kill.flag（Kill Switch）

依存関係のヒント
----------------
- 標準ライブラリ: os, sys, sqlite3, threading, datetime, pathlib, logging, json, urllib, socket, ipaddress など
- サードパーティ:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（任意：validate_config の YAML 検証に利用）
- 実行環境により追加パッケージが必要になる可能性があります。requirements.txt / pyproject.toml があればそちらを参照してください。

開発上の補足
------------
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env 自動ロードを無効にできます。
- ExecutionEngine は時間帯に基づく処理（シグナル処理時間・マーケット時間）を行います。テストでは _process_signals() や _drain_push_queue() を直接呼び出して単体テストを行う設計です。
- リコンシリエーションや OrderSent の扱いなど、クラッシュ時の整合性を考慮した 2 段階永続化パターンを採用しています。

ライセンス / 貢献
----------------
README に記載なし。プロジェクトポリシー（LICENSE 等）が別途あればそちらを参照してください。

--- 
この README はリポジトリ内の主要なモジュールおよび実行スクリプトから要点を抜粋して作成しています。さらに詳しい使い方や運用手順はプロジェクト内のドキュメント（DataPlatform.md や各モジュールの docstring）を参照してください。