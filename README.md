README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買を想定したミニマルなフレームワークです。  
主に以下の機能を備え、実運用・テストの双方を考慮した設計になっています。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API 抽象化（実ブローカー／モックの切り替え）
- 注文状態管理（OrderRecord / OrderManager）
- 起動時リコンシリエーション（Reconciler）
- 3 段階のリスクガード（RiskManager）
- 監視プロセス（SystemMonitor を使う run_monitoring）
- データ処理モジュール（マーケットカレンダー、RSS ニュース収集など）
- .env 対話式セットアップ & 起動前の設定検証ツール

主要な設計方針として、ビジネスロジックと永続化（SQLite）を分離し、クラッシュ時にも整合性を回復できるような二相的永続化や照合（Reconciliation）を取り入れています。

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup により .env を対話的に作成
- 設定検証 CLI: python -m kabusys.validate_config（--strict で警告を失敗扱い）
- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading / development では MockBrokerClient を使用
  - KABUSYS_ENV=live は未実装（将来的に実ブローカー接続を想定）
- 監視プロセス起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
- 注文の状態遷移管理（OrderRecord）と永続化（SQLite）
- 起動時のリコンシリエーション（OrderSent の照合・ポジション差分検出）
- RiskManager による Gate1/2/3 のリスクガード（余力、重複、レート制限、ドローダウン等）
- データモジュール: JPX カレンダー管理（calendar_management）、ニュース収集（news_collector）等

セットアップ手順
--------------
1. システム要件
   - Python 3.10+（typing や新しい型注釈を使用）
   - OS 上に kabu ステーションを使う場合はそのセットアップ（本番接続）
   - 必要ライブラリ（代表例）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - pyyaml（YAML 検証を有効にする場合）
   - 実プロジェクトでは requirements.txt を用意して pip install -r でインストールしてください。

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係のインストール（例）
   - pip install duckdb httpx websocket-client defusedxml pyyaml

4. プロジェクトルート配置
   - このリポジトリを手元にクローンし、プロジェクトルート直下に .env を作成します（後述のウィザードを推奨）。

5. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
     - 対話式に設定を入力して .env を生成します。
     - 生成後、python -m kabusys.validate_config で検証してください。

6. 起動前チェック
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション（代表）:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番での通知）
   - 設定検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告がある場合も exit(1) で失敗扱いになります。

7. データディレクトリ
   - data ディレクトリ（デフォルト DB や PID/flag ファイル格納先）を作成するか、.env でパスを指定してください。
   - run_execution/run_monitoring は起動時に親ディレクトリを自動作成する箇所もありますが、権限等を確認してください。

使い方
------
基本的なコマンド例:

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（セッション実行）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient を使い、本番 DB と分離された paper_trading 用 SQLite に記録されます。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を作成すると安全に停止処理を行います。
  - PID ファイル: data/execution.pid（デフォルト、.env で pid を上書き可能）

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視用 SQLite は settings.sqlite_path を使用（監視は環境にかかわらず本番 sqlite_path を参照）

設定と運用上のポイント
- .env 自動読み込み
  - プロジェクトルートを .git または pyproject.toml から検出して .env（および .env.local）を自動読み込みします。
  - OS 環境変数 > .env.local > .env の優先順位で読み込みされます。
  - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 本番環境の注意
  - KABUSYS_ENV=live の場合は警告や追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認等）が行われます。
  - 現状、BrokerClientFactory は live を NotImplementedError にしており、実ブローカー接続は未実装です（将来的な実装を想定）。

- Kill Switch / 停止フラグ
  - kill.flag（デフォルト data/kill.flag）で即時 kill_switch が動き、全 active 注文をキャンセルして停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を自動でクリアするため、注意して使用してください（本番では 0 を推奨）。

- DB の分離
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用して、本番の監視 DB と完全に分離します。
  - orders 用のテーブルは init_orders_db(sqlite_conn) で冪等的に作成されます。監視 DB も init_monitoring_db を通して初期化されます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと役割です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込みと Settings クラス
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前設定検証ツール
  - run_execution.py               — ExecutionEngine 起動スクリプト（セッション実行）
  - run_monitoring.py              — 監視ループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py                — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py            — Settings に基づく Broker クライアント生成
    - kabu_client.py               — kabu ステーション API 実装（HTTP + WebSocket）
    - mock_client.py               — テスト用 MockBrokerClient
    - order_record.py              — OrderRecord（状態遷移ロジック）
    - order_repository.py          — SQLite 永続化レイヤ
    - order_manager.py             — 発注・同期・取消の高レベル API
    - execution_engine.py          — Signal Queue ベースの発注エンジン本体
    - reconciler.py                — 起動時のリコンシリエーション
    - risk_manager.py              — Gate1/2/3 のリスク管理
  - monitoring/
    - monitoring_db.py             — 監視 DB 初期化・ログ機能（参照: run_monitoring）
    - system_monitor.py            — システム監視ロジック（run_monitoring で使用）
  - data/
    - calendar_management.py       — JPX カレンダー管理（DuckDB）
    - news_collector.py            — RSS ニュース収集（SSRF 対策・正規化等）
  - utils/
    - logging_setup.py             — ロギング初期化ヘルパー
    - process_priority.py          — プロセス優先度設定ユーティリティ
  - scripts/（参照用）
    - generate_config.py           — config/*.yaml のテンプレ生成（validate_config で参照）

- config/
  - system_config.yaml             — システム設定テンプレ（プロジェクトに応じて）
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- data/
  - monitoring/duckdb / sqlite 等の DB を配置（デフォルトパスは .env で指定）

補助情報
--------
- YAML の内容検証は PyYAML がインストールされている場合に行われます。validate_config は PyYAML が無ければ YAML 内容検証をスキップします。
- news_collector では SSRF や XML 攻撃対策（defusedxml、リダイレクト先検査、受信サイズ制限など）を実装しています。
- ExecutionEngine はセッション（8:50〜15:30 想定）の流れでシグナル処理→push ドレインを行い、PID ファイル / kill.flag / stop flag の仕組みでプロセス管理します。
- MockBrokerClient はペーパートレードでのテストを容易にするため、instant/partial/never/reject の挙動モードを提供します。

ライセンス / 貢献
----------------
この README はコードベースの理解を助けるためのドキュメントです。実際に配布する際はライセンスやコントリビューションガイドラインをリポジトリに追加してください。

以上。セットアップや運用に関してさらに詳しい手順やサンプル .env、運用チェックリストが必要なら教えてください。