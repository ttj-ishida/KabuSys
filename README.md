KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買フレームワークの一部実装です。本リポジトリは以下の責務を持つモジュール群を含みます。

- 環境設定管理（.env の読み込み・対話式ウィザード）
- 設定検証 CLI（.env と config/*.yaml の事前チェック）
- 発注エンジン（ExecutionEngine、OrderManager、RiskManager 等）
- ブローカークライアント（Mock / kabu-station 用クライアント）
- 監視ループ（SystemMonitor 起動スクリプト）
- データ処理ユーティリティ（カレンダー管理、ニュース収集など）

この README は開発者・運用者向けの最小限の導入手順と使い方をまとめたものです。

機能一覧
--------
主な機能は以下のとおりです。

- .env 自動ロード（プロジェクトルートの .env / .env.local）
- 対話式環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの存在確認
  - config/*.yaml の存在と（PyYAML があれば）パース検証
  - --strict による警告を FAIL 扱いにするモード
- 発注エンジン（ExecutionEngine）
  - シグナル処理（指定時間帯）、WebSocket push ドレイン
  - 3段階リスクガード（Gate1: シグナル、Gate2: 実行、Gate3: メトリクス）
  - Reconciler（OrderSent の自動照合、ポジション差分検出）
- ブローカークライアント
  - MockBrokerClient（テスト用、fill_mode により挙動を切替）
  - KabuStationClient（kabu-station REST/WebSocket 経由、本番用）
- 監視ループ（run_monitoring）
  - 定期ポーリングでシステムメトリクス等を収集し SQLite に保存
- データユーティリティ
  - JPX カレンダー管理（DuckDB ベース）
  - ニュース収集（RSS、SSRF 対策、正規化、前処理）

前提・依存
----------
主な Python ライブラリ（プロジェクトによって変化します）:

- duckdb
- PyYAML（config YAML 検証に使用）
- httpx
- websocket-client
- defusedxml

必要に応じて仮想環境作成後にインストールしてください（requirements.txt は本リポジトリに含まれていないため、上記パッケージを個別にインストールします）。

例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb pyyaml httpx websocket-client defusedxml

セットアップ手順
--------------
1. リポジトリをクローンしてワークディレクトリに入る。

2. 仮想環境を作成し、必要なパッケージをインストールする（上記参照）。

3. .env の準備
   - 対話式ウィザードで作成する（推奨）:
       python -m kabusys.config_setup
     ウィザードは既存 .env を読み込み、対話的に項目を入力して .env を生成します。
   - 手動で作成する場合は .env.example（存在する場合）を参照し、少なくとも以下の必須変数を設定してください:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     さらにオプション変数:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト data/monitoring.db)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト INFO)
     - KABU_API_BASE_URL (kabu station API ベース URL)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート用)
     - その他ウィザードで案内される項目

4. 設定検証
   - .env を作成したら検証を実行します:
       python -m kabusys.validate_config
     警告も失敗扱いにしたい場合:
       python -m kabusys.validate_config --strict
   - validate_config は config/*.yaml の存在と（PyYAML が入っていれば）パース検証も行います。

5. データベース初期化
   - Execution や Monitoring 起動時に必要なテーブルは各起動プロセス内で初期化されます（init_orders_db や init_monitoring_db が呼ばれます）。手動で初期化する必要は通常ありません。

使い方（実行方法）
-----------------
主要なエントリポイントはモジュール実行形式で提供されています。

- 環境設定ウィザード（.env 生成/更新）
    python -m kabusys.config_setup
    --env-file オプションで .env のパスを指定可能。

- 設定検証（起動前チェック）
    python -m kabusys.validate_config
    --strict を付けると警告も exit(1) の失敗扱いになります。

- 発注エンジン（Execution）
    python -m kabusys.run_execution
    挙動:
      - KABUSYS_ENV=paper_trading または development の場合、MockBrokerClient を使用します（paper_trading は paper 用 SQLite を使用）。
      - KABUSYS_ENV=live の本番用ブローカーは未実装で NotImplementedError を投げます（現状は paper_trading / development での動作が想定）。
    停止:
      - プロジェクトルート/data/stop_requested.flag が存在すると安全に停止します。
      - PID ファイルを data/execution.pid に書き出します（設定で変更可能）。

- 監視ループ（Monitoring）
    python -m kabusys.run_monitoring
    挙動:
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
      - Monitoring は実行環境に関わらず本番 sqlite_path を使用します（監視データは常に共通 DB を想定）。

主要な環境変数（要点）
-------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意 / 推奨:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
    - live は本番として特別な警告や追加チェックが入ります（LINE 通知設定など）。
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - KABU_API_BASE_URL: kabu station のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番で 1 を設定すると起動時に kill.flag を自動クリア — 危険）

運用メモ / トラブルシュート
-------------------------
- validate_config 実行で PyYAML が無い場合、YAML 内容検証はスキップされます（警告が出ます）。YAML 検証を有効にするには PyYAML をインストールしてください。
- stop / kill フラグ:
  - data/stop_requested.flag: 実行中ループの安全停止トリガー（監視・実行スクリプト共通）
  - data/kill.flag: ExecutionEngine の kill switch。存在すると起動を拒否する（KILL_FLAG_CLEAR_ON_START=1 の場合のみ自動クリアされます）
- PID ファイル:
  - 実行中は data/execution.pid や data/execution.pid（設定により変化）に PID を書き込みます。正常終了時に削除されますが、異常終了時は手動で削除してください。
- ログレベルやログ設定は utils/logging_setup を通じて行われます。必要に応じて LOG_LEVEL を設定してください。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・.env 自動ロード / Settings クラス
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- broker_api.py            — BrokerAPI Protocol / データモデル / ファクトリ
- broker_factory.py        — Settings に基づくブローカー生成
- kabu_client.py           — kabu-station REST/WebSocket クライアント
- mock_client.py           — MockBrokerClient（テスト用）
- order_record.py          — OrderRecord（状態遷移・ビジネスロジック）
- order_repository.py      — SQLite 永続化層（orders テーブル）
- order_manager.py         — 発注フローおよび Order 管理 API
- execution_engine.py      — ExecutionEngine（シグナル処理・push ドレイン）
- reconciler.py            — 起動時リコンシリエーション
- risk_manager.py          — 3段階リスクガード

src/kabusys/data/
- calendar_management.py   — マーケットカレンダー管理
- news_collector.py        — RSS ニュース収集（前処理・SSRF 対策 等）
- (その他 jquants_client 等の補助モジュール想定)

src/kabusys/monitoring/
- monitoring_db.py         — 監視用 SQLite テーブル初期化 / ログ記録
- system_monitor.py        — システムメトリクス収集ロジック

src/kabusys/utils/
- logging_setup.py         — ログ設定ユーティリティ
- process_priority.py      — プロセス優先度設定ユーティリティ

開発・拡張のヒント
------------------
- ブローカー実装:
  - 現状、paper_trading/development は MockBrokerClient を利用します。live 用の KabuStationClient の運用は実装済みですが、BrokerClientFactory では未実装として扱われるため注意してください。
- テスト:
  - MockBrokerClient を使うことで外部依存を排して発注フローの単体テストが可能です。
- リコンシリエーションや OrderState の設計は冪等性・クラッシュ耐性を重視しています。OrderSent の永続化タイミングなど設計ノートを参照の上拡張してください。

最後に
-----
この README はコードベースから読み取れる主要な使い方・設計方針をまとめたものです。実際の運用前には .env の適切な設定、監視・バックアップ体制、テスト環境での十分な検証を行ってください。必要があれば README を拡張して運用手順や運用チェックリスト（デプロイ手順、モニタリング設定、アラート条件等）を追加してください。