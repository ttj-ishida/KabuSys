KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買を想定した小規模なトレーディングフレームワークです。  
主に以下を提供します。

- 環境変数 / YAML 設定の検証ツール
- 対話式 .env 作成ウィザード
- 発注エンジン（ExecutionEngine）とその周辺コンポーネント（OrderManager / RiskManager / Reconciler 等）
- ブローカークライアント（MockBrokerClient / KabuStationClient）
- 監視プロセス（SystemMonitor をポーリングする run_monitoring）
- マーケットカレンダー管理やニュース収集などのデータユーティリティ

このリポジトリは実際の証券会社接続を模した設計になっており、テストやペーパートレードでの動作を重視しています。

主な機能
--------
- .env 対話式セットアップ（python -m kabusys.config_setup）
- 起動前設定検証（環境変数、config/*.yaml、パス等）（python -m kabusys.validate_config）
- ExecutionEngine によるシグナル駆動の発注フロー（本番 / ペーパー切替）
- 注文状態の堅牢な取り扱い（OrderRecord の状態遷移、DB 永続化、Reconciler による復旧）
- 3段階リスクガード（Gate1: シグナル、Gate2: 実行、Gate3: ドローダウン監視）
- Mock ブローカーによるテスト容易化（fill_mode 指定可）
- DuckDB / SQLite を利用したデータ保存と監視

セットアップ手順
----------------
前提
- Python 3.10 以上（型表記や union 型等を使用）
- Git 等の一般的な開発ツール

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ...
   - cd <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - 必須・便利なパッケージ例:
     - duckdb
     - PyYAML
     - httpx
     - websocket-client
     - defusedxml
   - 例:
     - pip install duckdb PyYAML httpx websocket-client defusedxml

   （requirements.txt がある場合はそれを利用してください）

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - ウィザードは .env を作成/更新します（デフォルトはプロジェクトルート/.env）。
   - あるいは手動で .env を作成（.env.example があれば参照してください）。
   - 自動ロード: app 起動時に .env / .env.local を自動で読み込みます。テストで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- オプション（主なもの）
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
  - KABU_API_BASE_URL — kabu station API のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 本番での kill.flag 自動クリア（0/1）

使い方
------
1. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup
   - ウィザード後は python -m kabusys.validate_config で検証してください。

2. 設定検証
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

   validate_config は .env および config/*.yaml の存在やパース（PyYAML があれば）をチェックします。

3. 実行エンジン（Execution）
   - 本番相当（KABUSYS_ENV=live を想定）やペーパートレードで動かすための起動スクリプト:
     - python -m kabusys.run_execution

   動作要点:
   - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient が使われます（デフォルトは paper_trading でペーパートレードDB を使用）。
   - エンジンは PID ファイルや kill.flag を監視します。デフォルト PID ファイル: data/execution.pid。停止フラグ: data/stop_requested.flag。
   - 起動時に Reconciler によるリコンシリエーションが走ります（クラッシュ復旧用）。

4. 監視プロセス（SystemMonitor ポーリング）
   - python -m kabusys.run_monitoring
   - ポーリング間隔を変える:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

5. ログ
   - ログレベルは LOG_LEVEL 環境変数で制御します（デフォルト INFO）。

注意点・トラブルシューティング
------------------------------
- .env を絶対にリポジトリにコミットしないでください（config_setup はヘッダに警告を入れます）。
- validate_config は PyYAML がない場合 YAML パースをスキップして警告を出します。YAML の完全検証を行うには PyYAML をインストールしてください。
- duckdb / sqlite のパスの親ディレクトリが存在しない場合、起動時に自動で作成されることがありますが、validate_config が警告を出します。data/ ディレクトリの作成は手動でも可。
- KABUSYS_ENV=live を設定すると本番用チェックが有効になり、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告等が出ます。live 時の設定は慎重に。
- Python バージョンにより型記法や機能が使えない場合があります。Python 3.10 以上を推奨します。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主なファイルと簡単な説明です。

- __init__.py
  - パッケージ定義とバージョン

- config.py
  - 環境変数の自動読み込みロジック（.env/.env.local）と Settings クラス（アプリ設定の取得）

- config_setup.py
  - .env 対話式セットアップウィザード（python -m kabusys.config_setup）

- validate_config.py
  - 起動前の環境検証 CLI（python -m kabusys.validate_config）

- run_execution.py
  - ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（python -m kabusys.run_monitoring）

- execution/
  - broker_api.py        — ブローカー API の Protocol / データモデル / ファクトリ
  - kabu_client.py       — kabuステーション REST クライアント（HTTP / WebSocket）
  - mock_client.py       — MockBrokerClient（テスト・ペーパー用）
  - broker_factory.py    — Settings に応じたクライアント生成
  - order_record.py      — 注文状態機械（OrderRecord と遷移検証ロジック）
  - order_repository.py  — SQLite による永続化層
  - order_manager.py     — DB と Broker を組み合わせる外向き API（発注フロー）
  - execution_engine.py  — 実際の発注エンジン（シグナル読み込み・WebSocket ドレイン等）
  - reconciler.py        — 起動時のリコンシリエーション（OrderSent の復旧等）
  - risk_manager.py      — 3段階リスクガード

- data/
  - calendar_management.py — マーケットカレンダーロジック（DuckDB を利用）
  - news_collector.py      — RSS ニュース収集・前処理ロジック

- monitoring/
  - monitoring_db.py  — 監視用 SQLite テーブルの初期化・書き込み（参照のみ、実装は別ファイルにあります）
  - system_monitor.py  — 実際の監視ロジック（run_monitoring から利用）

補足
----
- DB 初期化: run_execution/run_monitoring 内で必要なテーブルの初期化関数（init_monitoring_db や init_orders_db）が呼ばれます。テスト時は sqlite 接続を差し替えてください。
- MockBrokerClient は fill_mode パラメータ（instant, partial, never, reject）でテスト挙動を制御できます。
- 設計は「DB による不整合を最小化する2相永続化」など運用上の安全策を意識しており、クラッシュ耐性を考慮しています。

ライセンスや貢献
----------------
- 本リポジトリのライセンス表記はソース内に明記がない場合があります。商用利用や公開利用を行う前に必ずライセンスを確認してください。  
- バグ修正や改善提案は Pull Request をお願いします。

以上。セットアップや実行で不明点があれば具体的なエラーメッセージや実行コマンドを添えて質問してください。