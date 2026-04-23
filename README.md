# KabuSys

日本株自動売買システム（KabuSys）の簡易 README

このリポジトリは、kabu ステーションや J-Quants 等を利用した自動売買のコアライブラリと実行スクリプトを含みます。開発／ペーパートレーディング／本番環境を切り替えて動作することを想定した設計です。

## プロジェクト概要
- 環境変数ベースで設定を管理し、.env/.env.local から自動読み込み（OS 環境変数を優先）。
- 発注フローは Signal Queue を Pull して発注する ExecutionEngine を中心に構成。
- 発注の状態管理は OrderRecord（状態遷移ロジック）と OrderRepository（SQLite 永続化）で実装。
- ブローカー API の抽象化により、実際の kabu ステーションクライアントとテスト用 Mock クライアントを切り替え可能。
- 起動時の設定検証・対話式設定ウィザード、監視用ポーリングループ、リコンシリエーション等を備えます。

## 主な機能一覧
- 環境設定ウィザード（config_setup.py）
  - 対話式に .env を生成／更新
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の存在・基本妥当性検証（--strict で警告も失敗扱い）
- ExecutionEngine（run_execution.py）
  - シグナル処理、WebSocket ドレイン、発注フロー、リスクガード、kill switch
- Broker クライアント実装
  - KabuStationClient（実ブローカー用、httpx + websocket）
  - MockBrokerClient（テスト・開発用、fill_mode を指定可能）
- 注文管理
  - OrderRecord（状態遷移検証）、OrderRepository（SQLite 永続化）、OrderManager（送信/同期/取消）
- リスク管理（RiskManager）
  - Gate1（シグナルレベル）、Gate2（レート制限／サーキットブレーカー）、Gate3（ドローダウン監視）
- リコンシリエーション（起動時の復旧処理）
  - OrderSent 状態の同期・ポジション差分検出
- 監視プロセス（run_monitoring.py）
  - SystemMonitor のポーリングループ（監視 DB に書き込む）
- データ系ユーティリティ
  - マーケットカレンダー管理（duckdb を想定）
  - ニュース収集（RSS から raw_news 保存、SSRF 対策等）

## 必要な環境変数（主なもの）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／デフォルトあり:
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用の sqlite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）

注意:
- 自動 .env 読み込み順序: OS env > .env.local > .env（プロジェクトルートが .git または pyproject.toml を検出できる場合のみ自動読み込み）
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を用意
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
3. 必要パッケージをインストール
   - 主な依存（ファイル内 import を参照）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（validate_config が YAML の中身を検証する場合）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML
   - プロジェクトに requirements.txt が用意されている場合はそれを使用してください。
4. .env を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参照すること）

## 使い方（主要スクリプト）
- 環境設定ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup
  - 実行後、.env に保存されます。完了後は python -m kabusys.validate_config で検証してください。

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする:
    - python -m kabusys.validate_config --strict

- 実行エンジン（発注プロセス）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading または development の場合は MockBrokerClient を使用（paper_trading は paper_sqlite_path に記録）
  - 実行中にプロセス優先度を調整し、PID ファイルを data/execution.pid（デフォルト）に書き込みます。
  - 停止: プロジェクトの data/stop_requested.flag を作成すると安全に停止します。kill.flag による停止・キルスイッチ制御もサポート。

- 監視プロセス
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視 DB の分離は行いません）

- その他ユーティリティ
  - DB 初期化: order テーブル等は init_orders_db(conn)、init_monitoring_db(conn) で冪等に作成します（スクリプト内で使用）。
  - ブローカー生成: kabusys.execution.create_broker_api(mock=True, ...) を利用して Mock / Live の切替が可能。

## .env の自動読み込みルール
- プロジェクトルートはこのパッケージファイル位置を基準に .git または pyproject.toml を探索して決定します（CWD に依存しない）。
- 読み込み順:
  1. OS 環境変数（既存の環境変数は保護される）
  2. .env （override=False: 未設定のキーのみセット）
  3. .env.local（override=True: .env の値を上書き。ただし OS の既存キーは保護される）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みをスキップできます（テスト時に便利）。

## 設定ファイル（config/*.yaml）
- validate_config は config ディレクトリの YAML ファイル群（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）存在チェックおよび PyYAML があればパース検証を行います。
- これらが見つからない場合は警告になります（生成スクリプト scripts/generate_config.py を参照する旨のメッセージが出ます）。

## 推奨ワークフロー
1. 仮想環境を用意して依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定を検証（--strict を必要に応じて使用）
4. DuckDB / SQLite のパスに必要なディレクトリを作成（存在しない場合は警告）
5. 本番またはテストの実行:
   - 開発/テスト: KABUSYS_ENV=development / paper_trading → python -m kabusys.run_execution
   - 監視: python -m kabusys.run_monitoring

## ディレクトリ構成（抜粋）
プロジェクトルート
- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数読み込み・Settings
    - config_setup.py              — 対話式 .env ウィザード
    - validate_config.py           — 起動前設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py              — Broker API の Protocol / データモデル / ファクトリ
      - kabu_client.py             — kabu ステーション用クライアント（httpx/websocket）
      - mock_client.py             — テスト用モッククライアント
      - broker_factory.py          — Settings から BrokerClient を生成
      - order_record.py            — 注文状態マシンのデータモデル
      - order_repository.py        — SQLite 永続化層
      - order_manager.py           — 外向き発注 API（状態遷移 + broker 呼び出し）
      - execution_engine.py        — ExecutionEngine（セッションロジック）
      - reconciler.py              — 起動時リコンシリエーション
      - risk_manager.py            — 3段階リスクガード
    - data/
      - calendar_management.py     — マーケットカレンダー管理（DuckDB）
      - news_collector.py          — RSS 収集・前処理
      - jquants_client.py          — （外部 API クライアント、実装参照）
    - monitoring/
      - monitoring_db.py          — 監視用 DB 初期化/書込ユーティリティ
      - system_monitor.py         — システム監視ロジック
    - utils/
      - logging_setup.py          — ロギング設定ユーティリティ
      - process_priority.py       — プロセス優先度設定ユーティリティ
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （上記はプロジェクトに存在しない場合、validate_config が警告を出力します）

## 参考・注意事項
- KABUSYS_ENV=live を使用する場合は特に注意：
  - 本番では実際に発注が行われます。LINE 通知設定や Kill Switch の確認を必ず行ってください。
  - validate_config は live のときに追加の注意喚起を行います（LINE 未設定や KILL_FLAG_CLEAR_ON_START の危険な値など）。
- 発注のクラッシュ安全性：
  - OrderManager.send_order はクラッシュ耐性を考慮した 2 段階永続化（OrderSent の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）を取り入れています。クラッシュ後は Reconciler により復旧を試みます。
- セキュリティ：
  - news_collector は SSRF 対策や defusedxml を利用した安全な XML 解析を行います。
  - .env は絶対に VCS にコミットしないでください（config_setup も同様に注意喚起を出します）。

---

追加で README の補足項目（依存関係の正確なリスト、CI / デプロイ手順、運用ガイド等）を作成したい場合は、要望を教えてください。必要に応じてサンプル .env.example の生成や運用チェックリストも作成します。