KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのサンプル実装です。  
モジュール設計は「設定管理 / ブローカークライアント / 発注エンジン / リスクガード / 監視 / データ収集（カレンダー・ニュース等）」で分離されており、実運用向けの安全装置（Kill Switch、Reconciliation、3段階リスクガード、サーキットブレーカー、レート制限など）が組み込まれています。

主な機能
--------
- 環境設定ウィザード（.env の対話式作成・更新）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の存在／整合性チェック）: kabusys.validate_config
- 実行エンジン（ExecutionEngine）: シグナル読込→Gate1/2を経て発注、WebSocket プッシュのドレイン処理、kill switch 発動
- ブローカー抽象化（BrokerAPIProtocol）: 実ブローカー（kabu station）と MockBrokerClient の両方をサポート
- 注文ライフサイクル管理（OrderRecord / OrderManager / OrderRepository）
- 起動時リコンシリエーション（Reconciler）: OrderSent の突合作業・ポジション差分検出
- 監視ループ（SystemMonitor）: 定期的にメトリクスを収集・保存（run_monitoring）
- データモジュール: マーケットカレンダー管理（JPX カレンダー）、RSS ニュース収集（安全対策付き）
- 安全設定: kill.flag / stop_requested.flag / PID ファイル・KILL_FLAG_CLEAR_ON_START 等

セットアップ
----------
前提:
- Python 3.9+（コード中の型注釈に合わせて適切なバージョンを使用してください）
- SQLite は標準ライブラリで可。外部依存は下記参照。

推奨パッケージ（最低限、機能をフルに使う場合）:
- duckdb
- httpx
- websocket-client
- PyYAML（config/*.yaml のパースを有効にする場合）
- defusedxml

例: 仮想環境での準備
- Python 仮想環境を作成・有効化
- パッケージをインストール:
  pip install duckdb httpx websocket-client pyyaml defusedxml

環境変数 / .env
- .env および .env.local をプロジェクトルートに置けます。自動ロード順は:
  OS 環境変数 > .env > .env.local（.env.local は .env の上書き）
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主な任意/設定項目:
  - KABUSYS_ENV: execution 環境（development / paper_trading / live）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL: kabu station API ベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START: 起動時 kill.flag 自動クリア（0 推奨 / 1 開発用）
- 重要ファイル/フラグ:
  - PID ファイル: default data/execution.pid（設定可能）
  - kill.flag: 発注系の強制停止トリガー（settings.kill_flag_path）
  - stop_requested.flag: monitoring / execution の外部停止トリガー（data/stop_requested.flag）

使い方（主要コマンド）
--------------------

1) .env 作成（対話式ウィザード）
- 実行:
  python -m kabusys.config_setup
- .env を対話式に生成・更新します。シークレット値は入力時にマスクされます。
- ウィザード実行後、validate_config で検証することを推奨します。

2) 設定検証
- 実行:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
- .env（および config/*.yaml）を事前検証します。--strict を指定すると警告も失敗（exit 1）として扱います。
- PyYAML 未インストール時は YAML の中身検証はスキップされます（警告）。

3) 実行エンジン起動（発注）
- 実行:
  python -m kabusys.run_execution
- 概要:
  - Settings を読み込み、DB（SQLite / DuckDB）に接続
  - BrokerClientFactory でブローカークライアントを生成（dev/paper_trading は MockBrokerClient）
  - ExecutionEngine.run_session() をスレッドで起動
  - シグナル処理時間: デフォルト 8:50〜9:10（EngineConfig で変更可）
  - 市場終了まで push のドレイン処理を継続（デフォルト 15:30）
  - stop_requested.flag を検知すると安全に停止

4) 監視ループ起動
- 実行:
  python -m kabusys.run_monitoring
- 概要:
  - SystemMonitor をポーリングして監視データを SQLite / DuckDB に記録
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可、デフォルト 60 秒
  - 監視は KABUSYS_ENV に依存せず本番 sqlite_path を使用

開発時メモ / 安全対策
--------------------
- BrokerClientFactory:
  - development / paper_trading → MockBrokerClient（設定 paper_fill_mode に依存）
  - live → 実ブローカークライアントは未実装（NotImplementedError）
- Kill Switch:
  - settings.kill_flag_path（デフォルト data/kill.flag）によるローカル kill スイッチを実装
  - KILL_FLAG_CLEAR_ON_START=1 を本番で有効にしないこと（自動クリアは危険）
- Reconciliation:
  - 起動時に OrderSent の不整合を突合して回復処理を行います（Reconciler）
- テスト時:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを抑制できます
  - MockBrokerClient を利用して発注フローの単体テストが可能

ディレクトリ構成（主なファイル）
------------------------------
（src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py                -- パッケージ定義（__version__ 等）
  - config.py                  -- 環境変数・.env 読み込みと Settings クラス
  - config_setup.py            -- .env 対話式ウィザード
  - validate_config.py         -- 設定検証 CLI
  - run_execution.py           -- ExecutionEngine の起動スクリプト
  - run_monitoring.py          -- SystemMonitor の起動スクリプト

  - execution/                 -- 発注関連
    - __init__.py
    - broker_api.py            -- Protocol / データモデル / 例外 / ファクトリ
    - kabu_client.py           -- kabu station 実装（httpx）
    - mock_client.py           -- テスト用 MockBrokerClient
    - broker_factory.py        -- Settings に基づくクライアント生成
    - order_record.py          -- OrderRecord（状態遷移ロジック）
    - order_repository.py      -- SQLite 永続化層（orders テーブル）
    - order_manager.py         -- 発注フロー・状態管理
    - reconciler.py            -- 起動時リコンシリエーション
    - execution_engine.py      -- 実行エンジン本体（シグナル処理 / push drain）
    - risk_manager.py          -- Gate1/2/3 のリスク制御
    - (その他: order_manager で参照する補助モジュール等)

  - data/                      -- データ関連
    - calendar_management.py   -- マーケットカレンダー管理（next_trading_day 等）
    - news_collector.py        -- RSS ニュース収集・前処理
    - jquants_client.py        -- J-Quants API クライアント（参照される想定）

  - monitoring/                -- 監視関連
    - monitoring_db.py         -- 監視用 SQLite テーブル初期化・ログ保存
    - system_monitor.py        -- SystemMonitor 実装

  - utils/
    - logging_setup.py         -- ロギング設定ユーティリティ
    - process_priority.py      -- プロセス優先度操作ユーティリティ
    - その他ユーティリティ

補足
----
- config/ ディレクトリ（config/*.yaml）にある設定ファイルは任意の構成設定に使われます。validate_config は PyYAML があれば YAML のパース検証を行います。
- 本リポジトリは学習 / プロトタイプ用途を想定した実装です。実運用する場合は、認証情報の管理、権限・ネットワーク・テスト、法令遵守、エラー監視、DR（ディザスタリカバリ） など追加の安全設計が必要です。
- バージョン: __version__ は src/kabusys/__init__.py で定義されています（例: 0.1.0）。

ライセンス / 連絡先
-----------------
README に特にライセンス情報を含めていない場合はリポジトリルートに LICENSE を追加してください。質問や改善提案はリポジトリの issue を利用してください。

以上。必要であれば「環境変数一覧の詳細説明」「Docker Compose での起動例」「requirements.txt の候補」を別途追加します。どれを優先して出力しますか？