KabuSys — 日本株自動売買システム (ドキュメント)
=====================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。シグナルに基づく発注エンジン（ExecutionEngine）、監視ループ（SystemMonitor）、ブローカークライアント抽象化、リスク管理、リコンシリエーション、マーケットカレンダー管理やニュース収集などのコンポーネントで構成されています。設計上、環境（development / paper_trading / live）に応じて実行挙動を切り替えられ、テスト用の Mock ブローカーも提供します。

主な機能
--------
- 環境設定ウィザード (.env の対話式作成 / 更新) (kabusys.config_setup)
- 起動前の設定検証ツール（必須環境変数・config/*.yaml の存在/パース等）(kabusys.validate_config)
- ExecutionEngine: Signal Queue を基にした発注エンジン（発注フェーズ・WebSocket ドレイン）
- Broker API 抽象化（KabuStationClient / MockBrokerClient）
- Order 状態管理（OrderRecord）と SQLite による永続化（OrderRepository）
- Order 管理（OrderManager）: 送信 / 同期 / キャンセル / Duplicate チェック
- リスク管理（RiskManager）: Gate1/Gate2/Gate3（余力・重複・レート制限・サーキットブレーカー・ドローダウン）
- リコンシリエーション（Reconciler）：起動時の OrderSent 照合とポジション差分チェック
- 監視プロセス（run_monitoring）: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔設定可能）
- データ関連ユーティリティ: DuckDB を利用したマーケットカレンダー管理、ニュース収集など
- 設定自動読み込み: プロジェクトルートの .env / .env.local を自動読み込み（無効化可能）

セットアップ手順
----------------
前提
- Python 3.9+（typing の挙動・一部 API で型ヒントを利用）
- system の sqlite3（標準ライブラリ）、DuckDB（パッケージ）が必要

推奨インストール（開発用）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（本リポジトリには requirements.txt が無い想定のため主要依存を例示）
   - pip install duckdb httpx websocket-client PyYAML defusedxml

3. プロジェクトルートで .env を作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または手動で .env を作成（下記「環境変数」参照）

4. 設定検証
   - python -m kabusys.validate_config
   - すべて OK にする。警告も失敗にしたい場合は --strict を付ける。

環境変数（重要）
- 必須（最低限設定必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意（推奨設定）
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
  - KABU_API_BASE_URL — kabu station API の URL（デフォルト http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用

- その他
  - KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など（paper_trading 用挙動）

注記:
- 自動 .env ロードはデフォルトで有効。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要コマンド）
--------------------

1) 環境設定ウィザード（.env の作成/更新）
   - python -m kabusys.config_setup
   - 対話式で値を入力し .env を生成します。シークレット値はマスク表示されます。

2) 設定検証
   - python -m kabusys.validate_config
   - 出力例:
     - INFO / WARNING / ERROR を表示し、エラーがあると exit code 1。
     - --strict を付けると警告も失敗扱い（exit code 1）。

3) 実行エンジン起動（発注プロセス）
   - python -m kabusys.run_execution
   - KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient が選ばれます。
   - 実行中は data/execution.pid（PID）や data/stop_requested.flag の存在を監視します。
   - stop したい場合は data/stop_requested.flag を作成することで安全停止をトリガーできます（run_monitoring/run_execution 共通の仕組み）。

4) 監視プロセス起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
   - 監視は settings.sqlite_path（本番用 SQLite）を使用します（paper_trading 環境でも本番 sqlite_path を使用する設計あり）。

ファイル / ディレクトリ構成
------------------------
（プロジェクトルート想定。src パッケージ配置ベース）

- src/kabusys/
  - __init__.py                  — パッケージ定義 (バージョン等)
  - config.py                    — 環境変数 / Settings クラス、自動 .env 読み込み
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py              — Broker API のデータモデル・Protocol・ファクトリ
    - broker_factory.py          — Settings に基づくクライアント生成
    - kabu_client.py             — kabu station REST API 実装（httpx）
    - mock_client.py             — テスト用 Mock ブローカー
    - order_record.py            — Order 状態遷移ロジック（ビジネスロジック）
    - order_repository.py        — SQLite 永続化層（orders テーブル）
    - order_manager.py           — 発注ワークフロー / send/sync/cancel
    - execution_engine.py        — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py              — 起動時リコンシリエーション
    - risk_manager.py            — Gate1/2/3 リスクガード
  - data/
    - calendar_management.py     — マーケットカレンダー管理（DuckDB）
    - news_collector.py          — RSS ニュース収集
    - (jquants_client 等 他の data モジュール)
  - monitoring/
    - monitoring_db.py           — 監視 DB 初期化・ログ記録（SQLite）
    - system_monitor.py          — 実際の監視ロジック（参照）
  - utils/
    - logging_setup.py           — ロギング設定ユーティリティ（参照）
    - process_priority.py        — プロセス優先度設定（参照）
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （上記 YAML ファイルは設定テンプレートとして利用。validate_config は存在と YAML パースの検証を行う）
- data/
  - *.db, *.flag 等（実行時に生成されるローカルデータファイル群）

設計上のポイント / 実行上の注意
------------------------------
- 環境切替:
  - KABUSYS_ENV が paper_trading / development のときは MockBrokerClient を使い、実際の発注は行いません（paper_trading 用 DB は分離されます）。
  - live モードは最終的に実ブローカーとの接続を想定していますが、KabuStationClient の live 運用は注意が必要です（慎重に設定を確認してください）。

- DB:
  - DuckDB: 分析・シグナル取得に使用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・orders 永続化などに使用（デフォルト data/monitoring.db）。paper_trading では専用の PAPER_TRADING_SQLITE_PATH が利用可能。

- 停止・キルスイッチ:
  - kill.flag（設定で指定された KILL_FLAG_PATH）や stop_requested.flag ファイルがプロセスの停止に使われます。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

- リスク管理:
  - RiskManager は 3 段階のガードを提供。特にサーキットブレーカーやレート制限は API 障害時にエンジンを保護します。

- リコンシリエーション:
  - 起動時に OrderSent 状態の注文をブローカー側と同期し、ポジション差分があればログに出力します。これにより再起動後の不整合を検出・回復します。

追加依存ライブラリ（サンプル）
----------------------------
- duckdb
- httpx
- websocket-client
- PyYAML (config/*.yaml のパース検証に使用、未インストール時は警告でスキップ)
- defusedxml (RSS パース用)
- その他（logging/ sqlite3 は標準搭載）

よくあるコマンドまとめ
--------------------
- .env を対話式で作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring

開発者向けメモ
---------------
- config.py はプロジェクトルートの検出（.git または pyproject.toml）を行い、そのルートの .env / .env.local を自動読み込みします。テストから自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- validate_config は PyYAML が無い場合に YAML 内容検証をスキップしますが、ファイルの有無は警告します。
- MockBrokerClient は fill_mode（instant / partial / never / reject）により挙動を切り替えられ、単体テストでの振る舞い制御に便利です。
- 実運用では必ず validate_config で設定チェックを行い、KABUSYS_ENV=live のときは LINE 通知設定や kill flag 周りを特に確認してください。

ライセンス / 貢献
----------------
本ドキュメントはリポジトリ内のコードに基づく簡易説明です。実運用や配布時は LICENSE を確認し、機密情報（.env）は絶対に Git 等にコミットしないでください。

--- 

必要であれば README に記載する具体的な .env のサンプルや、config/*.yaml の簡単な説明（各 YAML の想定項目）を追加で作成します。どの情報を詳しく載せたいか教えてください。