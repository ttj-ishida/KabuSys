KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。本リポジトリは以下の主要機能を提供します。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API 抽象化（kabu station 実装＋テスト用モック）
- 発注状態管理（OrderRecord / OrderManager / OrderRepository）
- 起動時のリコンシリエーション（Reconciler）
- 3段階のリスクガード（RiskManager）
- マーケットカレンダー管理 / ニュース収集等のデータ処理ユーティリティ
- 設定ウィザード（.env 生成）と設定検証 CLI
- 監視用ポーリングプロセス（SystemMonitor 起動スクリプト）

特徴
----
- 発注フローはクラッシュ耐性を考慮した永続化シーケンスで実装（OrderSent の扱い等）
- 本番（live）・ペーパートレード（paper_trading）・開発（development）に対応
- MockBrokerClient により kabu station がなくてもローカルで挙動確認が可能
- 起動時の自動リコンシリエーションでクラッシュ後の復旧を支援
- 簡易 CLI（.env ウィザード / 設定検証）を同梱

前提条件
--------
- Python 3.10+
- SQLite3（標準ライブラリ）
- 推奨／実行時依存（用途により）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml の内容検証を行う場合）
- ネットワークアクセス：kabu station（実機）を利用する場合はローカルの kabu station が必要

インストール（例）
-----------------
仮想環境を作成して依存を入れる例：

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml pyyaml

（requirements.txt がある場合はそれを使ってください。）

設定（.env）
-----------
- 本プロジェクトは環境変数で設定を管理します。主な環境変数：

  必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

  重要（任意）:
  - KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL: kabu station API のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START: 起動時の kill.flag 自動クリア（0/1）

- 自動読み込み:
  - 起動時にプロジェクトルートの .env と .env.local を自動で読み込みます（OS 環境変数が優先）。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env を作る（対話式ウィザード）
------------------------------
対話式で .env を作成／更新するスクリプトが用意されています。

- 実行:
  - python -m kabusys.config_setup

  ウィザードは既存の .env を読み込み、シークレット値はマスクして表示します。最後に確認してファイルへ保存します。

設定検証
--------
起動前に設定不備（未設定の必須変数、プレースホルダ値、config/*.yaml の存在と YAML パースエラー など）を検出できます。

- 実行:
  - python -m kabusys.validate_config
  - 警告を FAIL 扱いにするには: python -m kabusys.validate_config --strict

  PyYAML がない場合は YAML 内容検証はスキップされます（警告表示）。

使い方（プロセス起動）
---------------------

- 実際の発注セッション（Execution Engine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、本番 DB と分離して data/paper_trading.db に記録されます。
  - 実行中に data/stop_requested.flag を作成すると安全に停止処理を開始します。
  - PID ファイルは data/execution.pid（設定により変更可）に書き込まれます。
  - 起動前に data/kill.flag が存在すると、KILL_FLAG_CLEAR_ON_START によって自動クリアするか起動を拒否します。

- 監視ループ（SystemMonitor）を起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視プロセスは常に本番用の sqlite_path を使用します（環境にかかわらず）。

主要な動作ポイント
-----------------
- ExecutionEngine
  - 8:50 〜 9:10 にシグナルの一括処理（発注ループ）
  - 9:10 〜 15:30 に WebSocket push をドレインして状態同期
  - 発注は OrderManager を介して行われ、OrderRecord を SQLite に永続化する
  - リスク管理は RiskManager（Gate 1/2/3）で検査する
  - kill_switch() によって全 active 注文をキャンセルしループを停止する仕組み

- Broker クライアント
  - create_broker_api(mock=True/False) で MockBrokerClient / KabuStationClient を切替可能
  - MockBrokerClient は fill_mode により instant/partial/never/reject の動作を模擬できる

ディレクトリ構成（抜粋）
---------------------
（プロジェクトルート以下の src/kabusys を想定）

- src/kabusys/
  - __init__.py                      — パッケージ定義（__version__ など）
  - config.py                        — 環境変数読み込み / Settings クラス（アプリ設定）
  - config_setup.py                  — .env 対話式ウィザード CLI
  - validate_config.py               — 起動前設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py                  — Broker API の Protocol / データモデル / 例外 / ファクトリ
    - kabu_client.py                 — kabu station REST API クライアント（httpx + websocket）
    - mock_client.py                 — テスト用モックブローカ
    - broker_factory.py              — Settings に基づくクライアント生成
    - order_record.py                — OrderRecord と状態遷移ロジック（純粋ビジネスロジック）
    - order_repository.py            — SQLite 永続化（orders テーブル）
    - order_manager.py               — 外向きの注文 API（作成・送信・同期・キャンセル）
    - execution_engine.py            — 発注セッション（Signal Pull / push ドレイン）
    - reconciler.py                  — 起動時リコンシリエーション
    - risk_manager.py                — Gate 1/2/3 リスクガード
    - ...（その他、order_manager から参照されるコンポーネント等）
  - data/
    - calendar_management.py         — マーケットカレンダー管理
    - news_collector.py              — RSS ニュース収集
    - ...（J-Quants クライアント等）
  - monitoring/
    - monitoring_db.py               — 監視用 SQLite テーブル初期化 / ログ書き込み（参照される）
    - system_monitor.py              — 実際のモニタリングロジック（run_monitoring で使用）
  - utils/
    - logging_setup.py               — ロギング設定ユーティリティ
    - process_priority.py            — プロセス優先度設定ユーティリティ
    - ...（その他ユーティリティ）

注意事項 / トラブルシューティング
---------------------------------
- .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- validate_config による検証で必須環境変数が未設定の場合は FAIL（exit code 1）になります。--strict を付けると警告も FAIL 扱いになります。
- PyYAML をインストールしていない場合、config/*.yaml のパースチェックはスキップされます（warning）。
- KabuStationClient を使う場合はローカルマシンに kabuステーション® アプリが必要です。ローカルでの開発・テストには paper_trading（mock）を推奨します。
- Python バージョンは 3.10 以上を推奨します（型記法や構文の依存のため）。

開発メモ / 拡張ポイント
----------------------
- 本番用の Live broker 実装は未実装の箇所があるため、実運用前に必ずコードレビューと十分なテストを行ってください（BrokerClientFactory は live で NotImplementedError を投げる設計）。
- Reconciliation（起動時の同期）は重要な安全機構です。発注フローの変更時はこの挙動を確認してください。
- news_collector、calendar_update_job などのバッチジョブは外部 API（J-Quants 等）に依存します。API レート制限やレスポンス形式の変更に注意してください。

ライセンス / バージョン
------------------------
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- ライセンス情報等は別途 LICENSE ファイルやプロジェクト管理ドキュメントに従ってください。

お問い合わせ
------------
実装や使い方の不明点があれば、どのスクリプトを実行しようとしているか・発生しているエラー出力を添えて質問してください。必要であれば、主要な設定値（環境変数名のみ）やログ抜粋の共有をお願いします。