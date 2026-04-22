KabuSys — 日本株自動売買システム（README）
========================================

概要
----
KabuSys は日本株の自動売買を想定した小規模なフレームワークです。  
主な責務は以下の通りです。

- シグナルに基づく発注フローの実行（ExecutionEngine）
- 発注状態管理（OrderRecord / OrderRepository / OrderManager）
- リスクガード（3段階: Gate1〜3）とサーキットブレーカー
- ブローカー抽象（kabu station 実装 / Mock 実装）
- 起動時のリコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor を用いた polling）
- データ周辺（マーケットカレンダー管理、ニュース収集など）
- 環境設定ウィザード（.env 作成）および検証ツール

主な機能一覧
--------------
- 環境設定ウィザード: python -m kabusys.config_setup による .env の対話式作成
- 設定検証: python -m kabusys.validate_config で .env / config/*.yaml の事前チェック
- 実行エンジン: 実際の発注フローを ExecutionEngine が実行（run_execution.py）
- 監視ループ: SystemMonitor を定期ポーリング（run_monitoring.py）
- 注文永続化: SQLite を利用する OrderRepository（orders テーブル）
- ブローカー抽象化: BrokerAPIProtocol（MockBrokerClient と将来の KabuStationClient）
- リスク管理: RiskManager（Gate1: 信号/余力等、Gate2: レート制限/CB、Gate3: ドローダウン）
- リコンシリエーション: 再起動後に OrderSent 状態をブローカーと照合
- データユーティリティ: DuckDB を用いたカレンダー管理、ニュース収集モジュール

前提・依存
-----------
実行に必要な代表的パッケージ（プロジェクトに requirements ファイルがある想定）:
- Python 3.9+
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config/*.yaml のパース検証に使用。未インストールでも検証はスキップされる）
- その他標準ライブラリ

セットアップ手順
----------------
1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo_url>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install duckdb httpx websocket-client defusedxml pyyaml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env の初期作成（対話式）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabu API パスワード / DB パス等を順に尋ねます。
   - 出力先はデフォルトでプロジェクトルートの .env（--env-file で変更可）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict を付与:
     python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意／よく使う:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker を使い data/paper_trading.db を用いる
  - live: 本番（現状 Live broker は未実装の旨メッセージあり）
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知（本番環境では未設定だと警告）

使い方（実行例）
----------------
- 環境ウィザード（.env 作成）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセス起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで検知

- 実行プロセス起動（発注エンジン）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合 MockBrokerClient を使い、paper_trading 専用 SQLite（data/paper_trading.db）を使用
  - 実行中の停止は同様に stop_requested.flag の作成で検知
  - 起動時に PID ファイル（data/execution.pid 等）を作成する

- 設定のプレビュー／検証フロー:
  1) .env を作成（config_setup）
  2) validate_config で確認
  3) run_monitoring/run_execution を起動

重要な運用ノート
----------------
- 監視 (monitoring) は KABUSYS_ENV に関わらず本番 sqlite_path を使用します。監視 DB を分離したい場合は SQLITE_PATH を調整してください。
- paper_trading 環境は MockBrokerClient を使い、本番 DB と分離して動作するよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- 起動時の kill.flag 振る舞い:
  - kill.flag が存在すると起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合は自動でクリアして起動）
  - 実行中は kill.flag の作成で即時停止（全 active 注文のキャンセルなどを行う）
- リコンシリエーション機能により OrderSent の不確定状態を起動時にブローカー照合で復旧します

開発／テスト向け留意点
---------------------
- MockBrokerClient は fill_mode（instant/partial/never/reject）などをサポートし、ユニット／統合テスト用に挙動を制御できます。
- create_broker_api(mock=True, ...) を通してモックを生成します。BrokerClientFactory は Settings を参照して自動的にモックを返します（development / paper_trading）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数読み込み・Settings（.env の自動読み込みロジック含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前検証 CLI
- run_execution.py — 発注エンジン起動スクリプト
- run_monitoring.py — 監視ループ起動スクリプト

execution/（発注周り）
- broker_api.py — BrokerAPI の Protocol、データモデル、例外、create_broker_api
- broker_factory.py — Settings に応じたクライアント生成
- kabu_client.py — kabu station REST API クライアント実装
- mock_client.py — MockBrokerClient（テスト用）
- order_record.py — 注文状態モデルと遷移ロジック（純粋ロジック）
- order_repository.py — SQLite 永続化層（orders テーブル）
- order_manager.py — OrderRecord と Repository / Broker をつなぐ外向き API
- execution_engine.py — セッション制御と発注ループ
- reconciler.py — 起動時リコンシリエーション
- risk_manager.py — Gate1〜3 のリスク制御

monitoring/
- monitoring_db.py, system_monitor.py など（監視 DB 初期化・監視ロジック）

data/
- calendar_management.py — 市場カレンダー管理（DuckDB）
- news_collector.py — RSS ベースのニュース収集（defusedxml 等の安全対策あり）
- jquants_client.py — J-Quants API 周り（参照される想定）

utils/
- logging_setup.py, process_priority.py など（ロギング設定やプロセス優先度の設定）

その他
-----
- config/*.yaml のテンプレート（system_config.yaml 等）をプロジェクトで使用します。不足時は validate_config が警告します。生成スクリプト（scripts/generate_config.py）が存在する想定です。
- README は実運用に合わせて .env の管理（Git 管理禁止）や監視 DB のバックアップ運用を別途整備してください。
- ライブブローカー（KabuStationClient による本番接続）は一部未実装／要確認の箇所があります。KABUSYS_ENV=live を使う際は十分な事前テストと安全策を講じてください。

ライセンス／コントリビュート
----------------------------
（このREADMEにはライセンス情報は含まれていません。必要に応じて LICENSE を追加してください。）

以上。必要であれば、README に含めるコマンドの具体例（.env のサンプル行や DB 初期化コマンド）、あるいは各モジュールの API ドキュメントを追加で作成します。どの情報を優先して深掘りしますか？