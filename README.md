KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買を想定した軽量なフレームワークです。  
主な機能としてシグナルを受けて発注する ExecutionEngine、発注状態の永続化と管理、起動時のリコンシリエーション、監視ループ、マーケットカレンダー管理やニュース収集などを備えます。  
実稼働（live）だけでなくペーパートレード（paper_trading）や開発（development）向けの挙動を考慮して設計されています。

主な機能
--------
- 設定管理
  - .env / .env.local の自動読み込み（OS 環境変数 > .env.local > .env）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン（Execution）
  - Signal Queue Pull 型の ExecutionEngine（発注窓 8:50–9:10、ドレイン 9:10–15:30 の想定）
  - OrderManager / OrderRecord による状態管理（状態遷移の検証）
  - OrderRepository（SQLite）による永続化
  - RiskManager による Gate1/2/3 の三段階ガード（余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン）
  - Reconciler による起動時の自動復旧（OrderSent の照合・ポジション差分検出）
- ブローカークライアント
  - MockBrokerClient（テスト／ペーパートレード用、fill_mode 対応）
  - KabuStationClient（kabuステーション REST API 実装、将来の Live 実装想定）
  - BrokerAPIProtocol / create_broker_api ファクトリ
- 監視（Monitoring）
  - SystemMonitor を定期実行する監視ループ（python -m kabusys.run_monitoring）
  - SQLite / DuckDB を用いた監視 DB と分析 DB
- データ管理
  - DuckDB ベースのデータアクセス（シグナル / ポートフォリオ等）
  - マーケットカレンダー管理（J-Quants ベースの更新ロジック）
  - ニュース収集（RSS 収集・前処理、SSRF 対策、XML 脆弱性対策）

セットアップ手順
----------------
前提
- Python 3.10+（PEP 604 の型記法等を使用しているため）
- SQLite（標準ライブラリ）、DuckDB（pip パッケージ）等

1. リポジトリをクローン／配置する
   - プロジェクトルートに src/ 配下が存在する構成を想定しています。

2. 仮想環境を作成して依存パッケージをインストール
   例:
   - pip install -r requirements.txt
   必要なパッケージ（例）
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（validate_config の YAML 構文チェックを有効にする場合）
   - そのほか（プロジェクト固有のパッケージがある場合）

3. .env を作成する
   - 対話式ウィザードで作成できます:
     python -m kabusys.config_setup
   - またはプロジェクトルートに .env を手動で作成します（次節参照）。

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトありや任意項目）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート通知用
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアする (0/1)
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

.env 読み込み挙動
- 読み込み順: OS 環境変数 > .env.local > .env
- .env.local は .env を上書きできます（テストやローカル差分用）
- OS 側の環境変数は保護され、.env/.env.local によって上書きされません
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

簡単な .env 例
----------------
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

使い方（主要コマンド）
--------------------
- 環境ウィザード（.env の初期作成・更新）
  python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml のチェック）
  python -m kabusys.validate_config
  警告も失敗扱いにする（CI 等）:
  python -m kabusys.validate_config --strict

  exit code:
  - 0: OK（エラーなし、警告なしまたは許容）
  - 1: エラーあり、または --strict かつ警告あり

- 実行エンジン起動（実際の発注ループ）
  python -m kabusys.run_execution
  注意:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録します。
  - 本番環境で起動する場合は kill.flag 等の安全設定を確認してください。

- 監視ループ起動（SystemMonitor の定期実行）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60）

- 開発／テスト用
  - MockBrokerClient を直接使って単体テストが可能（fill_mode は instant/partial/never/reject）

運用に関する注意
----------------
- KABUSYS_ENV=live の場合は本番運用になります。LINE 通知や KILL_FLAG の設定等を慎重に確認してください（validate_config は live 時に追加警告を出します）。
- kill.flag（デフォルト: data/kill.flag）と stop_requested.flag（data/stop_requested.flag）はプロセス間で停止指示に使われます。PID ファイルは data/*.pid に書き出されます。
- ExecutionEngine は起動時に Reconciler を走らせ、OrderSent の状態をブローカーと突合します。DB の整合性を保つため、再起動時はこの動作に依存します。

ディレクトリ構成（抜粋）
-----------------------
以下は本リポジトリの主要モジュールと役割（src/kabusys 以下）。

- __init__.py
  - パッケージ情報（__version__ 等）

- config.py
  - 環境変数の読み込み、Settings クラス（各種設定プロパティ）
  - 自動 .env ロードロジック（.env / .env.local）

- config_setup.py
  - インタラクティブな .env ウィザード

- validate_config.py
  - 起動前検証ツール（必須環境変数、KABUSYS_ENV の妥当性、YAML ファイルのパースなど）

- run_execution.py
  - ExecutionEngine を組み立ててセッションを実行する起動スクリプト

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- execution/
  - broker_api.py         — BrokerAPIProtocol、データモデル、例外、ファクトリ
  - kabu_client.py        — kabu station REST API 実装
  - mock_client.py        — MockBrokerClient（テスト用）
  - broker_factory.py     — Settings に応じたブローカー生成
  - order_record.py       — OrderRecord（状態遷移ロジック）
  - order_repository.py   — SQLite 永続化層（orders テーブル）
  - order_manager.py      — 発注 API（作成・送信・同期・キャンセル）
  - execution_engine.py   — ExecutionEngine（シグナル処理・push ドレイン）
  - reconciler.py         — 起動時リコンシリエーション（OrderSent 照合）
  - risk_manager.py       — Gate1/2/3 のリスクガード

- data/
  - （実行時に使用するデータベースやフラグファイル）
  - data/kabusys.duckdb（デフォルト）
  - data/monitoring.db（デフォルト SQLite）
  - data/paper_trading.db（paper_trading 用）
  - *.pid, kill.flag, stop_requested.flag

- data/（その他のデータ層）
  - monitoring/、news/、calendar 関連の DB 初期化ユーティリティなど（コード内で参照）

- data/*.yaml（config/*.yaml）
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - validate_config はこれらの存在と YAML 構文をチェックします（PyYAML 未導入時はパースはスキップして警告）

拡張ポイント
-------------
- Live broker の実装は将来的に KabuStationClient を用いた完全なライブ実装へ拡張可能（現状はペーパートレード／モックが主）。
- 監視・アラート送信（LINE）やログの外部集約は用途に応じて拡張可能。
- DuckDB を利用した分析パイプラインの追加（シグナル生成・バックテスト等）に適合。

サポート / 開発メモ
-------------------
- 設定検証（validate_config）を CI に組み込み、--strict を使うことで警告もエラー化できます。
- DB スキーマ作成（orders 等）は該当モジュールの init_* 関数（例: init_orders_db）を使って実行前に作成してください（run_execution 等は起動時に init_monitoring_db を呼びますが、orders テーブルは明示的な初期化が必要な場合があります）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

以上が簡易 README です。必要であれば以下を追記します：
- requirements.txt の候補（推奨バージョン含む）
- .env.example のフルテンプレート
- 起動・監視手順のより詳しい運用手順（systemd ユニット例など）