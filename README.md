README
=====

概要
----
KabuSys は日本株自動売買のための軽量なフレームワークです。  
主にローカル開発・ペーパートレード・将来的な実運用（live）を想定し、以下の設計方針を持ちます:

- 設定は .env（/ .env.local）または環境変数で管理
- 発注処理は Signal Queue を取り込み ExecutionEngine が行う
- Broker クライアントは環境に応じて Mock / 実装を切り替え可能
- 再起動時のリコンシリエーションや複数段階のリスクガードを実装
- DuckDB / SQLite を分析・監視用に利用

主な機能
--------
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的生成
- 設定検証 CLI（python -m kabusys.validate_config）で .env / config/*.yaml の不備検出
- ExecutionEngine：シグナル読み込み → 発注 → push ドレインまでのフロー
- Broker クライアント抽象化（MockBrokerClient / KabuStationClient）
- 注文状態管理（OrderRecord 状態遷移ロジック）
- リスク管理（Gate1/2/3：余力、重複、レート制限、サーキットブレーカー、ドローダウン）
- 起動時リコンシリエーション（Reconciler）で OrderSent の整合性回復
- 監視プロセス（run_monitoring）でシステムメトリクスや発注イベントを記録
- Data モジュール（マーケットカレンダー、ニュース収集など）

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
     （本リポジトリに requirements.txt がない場合、最低限以下を入れてください）
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML (YAML 内容検証を行いたい場合)
     - その他 開発用: pytest 等

4. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 手動で .env を作成する場合は .env.example を参考にしてください（プロジェクトにあれば）。
   - 自動読み込み: 起動時にプロジェクトルート（.git または pyproject.toml）を検出できれば .env / .env.local を自動で読み込みます。
     - 自動ロードを無効化する場合:
       - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合:
     - python -m kabusys.validate_config --strict

必須 / 推奨の環境変数
--------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/設定項目:
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH : 分析用 DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL : kabu station API のベース URL（例: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : 本番での通知用（任意）

その他の注意:
- KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアします（開発用。live では 0 推奨）。
- stop フラグ: data/stop_requested.flag が存在すると run_* スクリプトはループを終了します。
- PID ファイル: 実行時に data/execution.pid 等へ PID を書きます（Settings.pid_file_path）。

使い方
------
1. 設定ウィザード（.env の生成）
   - python -m kabusys.config_setup
     - 対話形式で必要な環境変数を入力し .env を保存します。

2. 設定検証
   - python -m kabusys.validate_config
     - --strict を付けると警告もエラーとして扱い exit code 1 を返します。

3. 実行エンジン（発注）
   - python -m kabusys.run_execution
     - KABUSYS_ENV が paper_trading または development の場合、MockBrokerClient が使用されます（settings.paper_fill_mode に依存）。
     - 実行開始時に kill.flag を検査し、存在する場合は起動を拒否（KILL_FLAG_CLEAR_ON_START によりクリア可）。

4. 監視ループ
   - python -m kabusys.run_monitoring
     - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60）。
     - 監視は常に本番用 sqlite_path（settings.sqlite_path）を使用します。

5. 開発・テスト向け
   - MockBrokerClient を使うことで kabu station を立てずに発注フローの単体テストが可能です。
   - ExecutionEngine, OrderManager, OrderRepository などはユニットテスト向けに分離されています。

主なコマンドまとめ:
- python -m kabusys.config_setup        # .env 対話ウィザード
- python -m kabusys.validate_config    # 設定検証
- python -m kabusys.run_execution      # ExecutionEngine 起動（発注）
- python -m kabusys.run_monitoring     # 監視ループ起動

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py                   — パッケージ定義
- config.py                     — 環境変数読み込み・Settings クラス（自動 .env 読み込み）
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 起動前設定検証 CLI
- run_execution.py              — ExecutionEngine を起動するスクリプト
- run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト

subpackages / 主要モジュール:
- execution/
  - broker_api.py               — Broker API の Protocol、データモデル、例外、ファクトリ
  - kabu_client.py              — kabu station 実装（HTTP/WebSocket）
  - mock_client.py              — テスト用 MockBrokerClient
  - broker_factory.py           — Settings に基づく Broker クライアント生成
  - order_record.py             — 注文状態モデル（状態遷移ロジック）
  - order_repository.py         — SQLite による永続化層
  - order_manager.py            — 発注フロー / send / sync / cancel の外向き API
  - execution_engine.py         — Session 全体のフロー（シグナル処理・push drain・kill）
  - reconciler.py               — 起動時リコンシリエーション
  - risk_manager.py             — Gate1/2/3 のリスク制御
- data/
  - calendar_management.py      — マーケットカレンダー管理（J-Quants 統合）
  - news_collector.py           — RSS 収集・前処理ロジック
  - jquants_client.py           — （参照される想定の J-Quants クライアント）
- monitoring/
  - monitoring_db.py            — 監視用 SQLite テーブル初期化 / ログ書き込み
  - system_monitor.py           — システム監視ロジック
- utils/
  - logging_setup.py            — ロギング初期化ヘルパ
  - process_priority.py         — プロセス優先度設定ユーティリティ
- scripts/
  - generate_config.py          — config/*.yaml を生成するスクリプト（validate_config の警告参照）

実装上のポイント / 注意点
------------------------
- Settings は .env/.env.local を自動読み込みします（ただし OS 環境変数を保護）。
- 設定検証(validate_config) は PyYAML が無ければ YAML 内容チェックをスキップします（警告）。
- Execution フローはクラッシュ安全性を意識しており、OrderSent の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted の順に段階的にコミットします。これにより Reconciler が状態復旧可能です。
- MockBrokerClient は fill_mode（instant/partial/never/reject）を切り替えて挙動テストが可能。
- データベース:
  - DuckDB: 分析 / シグナルソース（data/kabusys.duckdb）
  - SQLite: 監視 / 発注履歴（data/monitoring.db / data/paper_trading.db）
- stop フラグ（data/stop_requested.flag）や PID ファイルにより外部からの停止・監視が可能です。

開発・運用時のチェックリスト
----------------------------
- .env を作成し、必要な必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）を設定
- python -m kabusys.validate_config を実行してエラー・警告を確認
- KABUSYS_ENV を正しく設定（development / paper_trading / live）
- 本番で LINE 通知を期待する場合は LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を設定
- run_execution / run_monitoring を systemd 等で適切に管理する（ログ・PID・停止フラグ）

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

フィードバック / 貢献
--------------------
バグ報告や機能改善の提案は Issue または Pull Request で歓迎します。テスト追加・ドキュメント改善に貢献していただけると助かります。

以上。必要であれば README にサンプル .env テンプレートや起動用 systemd ユニット例も追加します。