プロジェクト: KabuSys — 日本株自動売買システム (簡易ドキュメント)
  
以下は、このリポジトリの簡易 README（日本語）です。プロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成をまとめています。

プロジェクト概要
- KabuSys は日本株の自動売買を想定した小規模な自動売買フレームワークです。
- シグナルを読み取って発注を管理し、発注の永続化・同期・リコンシリエーション・監視を行います。
- 実運用（live）とペーパートレード（paper_trading）、開発（development）を想定した設定があり、テスト用に MockBrokerClient を提供します。

主な機能一覧
- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 対話式ウィザードで .env を生成・更新 (kabuys.config_setup)
- 設定検証
  - .env と config/*.yaml の存在・基本妥当性チェック（PyYAML があれば YAML パース検証） (kabusys.validate_config)
- 実行エンジン
  - ExecutionEngine: シグナル取得 → Gate (リスク判定) → 発注 → WebSocket ドレイン / push 処理
  - 発注の二相永続化、状態遷移検証、キャンセル、同期ロジック
- ブローカー抽象化
  - BrokerAPIProtocol を定義。MockBrokerClient（テスト）と KabuStationClient（kabuステーション連携）を実装
- リスク管理
  - 3段階のリスクガード (Gate1: シグナル/余力/重複/ポジション上限、Gate2: レート制限/サーキットブレーカー、Gate3: ドローダウン)
- 永続化 / リコンシリエーション
  - SQLite に orders テーブルで注文を永続化。再起動時に OrderSent の不確定注文をブローカー照合して状態回復
- 監視プロセス
  - SystemMonitor をポーリングして監視情報を SQLite/duckdb に記録する（run_monitoring）
- データ関連ユーティリティ
  - DuckDB を用いたマーケットカレンダー管理、ニュース収集(RSS) などの補助モジュール

前提 / 必要なソフトウェア
- Python 3.9+（コードは型ヒントと標準ライブラリの機能を利用）
- 必須ライブラリ（最低限）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
- 推奨 / オプション
  - PyYAML（config/*.yaml の内容検証に使用）
  - その他、logging 周りのセットアップに応じたライブラリ

セットアップ手順
1. リポジトリをクローン（例）:
   - git clone <repo-url>
2. Python 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール:
   - pip install duckdb httpx websocket-client defusedxml
   - YAML 検証を利用するなら: pip install PyYAML
4. 環境変数ファイルを準備:
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成
   - .env は絶対に Git にコミットしないこと（ウィザード内でも注意喚起があります）
5. 設定検証:
   - python -m kabusys.validate_config
   - 警告も厳密に FAIL にしたい場合:
     - python -m kabusys.validate_config --strict

重要な環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 推奨 / 任意:
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL
  - KABU_API_BASE_URL — kabu station のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート通知
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動でクリアするか (0/1、本番では 0 推奨)
- その他:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading の MockBrokerClient の振る舞い（instant/partial/never/reject）
- 自動 .env ロードを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

使い方（主要なコマンド）
- 環境ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 警告もエラー扱い: python -m kabusys.validate_config --strict
- 実行エンジン起動（本番・ペーパー共通エントリ）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV によって Mock / 実ブローカーが切り替わります。現状 live の実ブローカは NotImplementedError を投げます（ドキュメント内に注記あり）。
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
- 停止制御
  - プロジェクトルート data ディレクトリに stop_requested.flag や kill.flag を置くことで外部からの停止・キルスイッチを制御します。
  - PID ファイル: data/execution.pid（設定により変更可能）

実行に関する挙動メモ
- ExecutionEngine は以下のタイムラインに基づくセッション実行を想定:
  - シグナル処理時間帯: 08:50 〜 09:10（デフォルト）
  - WebSocket ドレイン: 09:10 〜 15:30（デフォルト）
- 発注フローはクラッシュ安全性を考慮した 2 段階永続化（OrderSent を先にコミット → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ更新）を採用
- 再起動時は Reconciler により OrderSent の不確定注文をブローカー側と照合して状態を復旧する
- paper_trading / development では MockBrokerClient を使用し、PAPER_FILL_MODE により即時約定や部分約定・拒否などをシミュレート可能

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / Settings 管理、.env の自動ロードロジック
  - config_setup.py — 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前の設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（python -m kabusys.run_monitoring）
  - execution/
    - __init__.py — execution 層の公開 API
    - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
    - broker_factory.py — Settings から適切な BrokerClient を生成
    - kabu_client.py — 実ブローカー（kabuステーション）クライアント実装
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — 注文状態モデルと状態遷移ロジック（DB に依存しない純粋ロジック）
    - order_repository.py — SQLite を使った永続化レイヤ（orders テーブル定義含む）
    - order_manager.py — 外向きの注文管理 API（create/send/sync/cancel）
    - execution_engine.py — 実際の発注エンジン（シグナル処理 / push ドレイン / kill_switch 等）
    - reconciler.py — 起動時のリコンシリエーション / ポジション差分照合
    - risk_manager.py — Gate1/2/3 のリスク管理
  - monitoring/
    - monitoring_db.py (参照のみ) — 監視DB 初期化・ロギング用（run_monitoring で使用）
    - system_monitor.py (参照のみ) — システム監視ロジック
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集と前処理
  - utils/
    - logging_setup.py (参照) — ログ設定ユーティリティ
    - process_priority.py (参照) — プロセス優先度設定ユーティリティ

開発・運用上の注意
- .env は機密情報を含むため絶対に Git にコミットしないでください。README やリポジトリには .env.example を置く運用が推奨されます（本コードにはウィザードで生成する仕組みあり）。
- KABUSYS_ENV=live の場合は本番運用となり、LINE トークンなどのアラート設定・Kill Switch の確認を慎重に行ってください。validate_config は live での追加ガードを実行します。
- SQLite / DuckDB のパス（デフォルト data/ 配下）は .env で適宜調整してください。親ディレクトリが存在しない場合は警告が出ますが、起動時に自動作成されることがあります。
- 実ブローカー連携（KabuStationClient）を使う場合は kabuステーションがローカルで起動していることが前提です。現状 live クライアントの直接起動に関する注意はコード内にも記載されています（BrokerClientFactory で NotImplementedError の可能性あり）。

サンプル .env（最小例）
- 以下はウィザードが生成する内容の一例（機密情報は適宜置き換えること）:
  JQUANTS_REFRESH_TOKEN=your_refresh_token_here
  KABU_API_PASSWORD=your_kabu_api_password_here
  KABU_API_BASE_URL=http://localhost:18080/kabusapi
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  KABUSYS_ENV=development
  LOG_LEVEL=INFO
  KILL_FLAG_CLEAR_ON_START=0

付録・デバッグコマンド
- 設定検証が通ったらまずはモックで実行して挙動確認:
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=development python -m kabusys.run_monitoring
- .env 自動ロードを無効にしてユニットテスト的に環境を制御する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

この README はコードベースの主要な点を簡潔にまとめたものです。実装の細部（API 例外の挙動、DB スキーマ、リスクパラメータ等）は各モジュール内の docstring / コメントを参照してください。質問や補足があれば教えてください。