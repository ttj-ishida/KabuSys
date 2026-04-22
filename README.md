# KabuSys

日本株自動売買システム（軽量プロトタイプ）

このリポジトリは、kabuステーション（ローカルのブローカーAPI）や J-Quants 等を想定した日本株の自動売買コンポーネント群（発注エンジン、リスクガード、監視、データ処理など）を含みます。実稼働を目的とした安全機能（多段階のリスクガード、リコンシリエーション、kill switch 等）を備えています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方
- 環境変数（主な項目）
- ディレクトリ構成と主要ファイル
- よくある注意点 / トラブルシュート

---

プロジェクト概要
- 発注処理（ExecutionEngine）を中心に、Signal → 発注 → 約定管理 → 監視／リコンシリエーションまでのフローを実装しています。
- 本番（live） / ペーパートレード（paper_trading） / 開発（development）モードを切り替え可能。
- ペーパートレード／開発では MockBrokerClient を利用して kabuステーションをエミュレートできます。
- 設定ウィザード（.env 作成）と起動前設定検証ツールが付属。

主な機能
- 多段階のリスクガード（Gate1: シグナル検査、Gate2: レート制限＆サーキットブレーカー、Gate3: ドローダウン監視）
- 注文状態管理（OrderRecord の状態遷移検証）
- 永続化層（SQLite）による注文 DB（orders テーブル）管理
- 起動時のリコンシリエーション（OrderSent の突合、ポジション差分検出）
- kabuステーション（実装済みの同期 REST クライアント）および Mock クライアント
- 監視プロセス（SystemMonitor を定期実行する run_monitoring）
- .env ウィザード（config_setup）と設定検証 CLI（validate_config）
- ニュース収集・カレンダー管理（DuckDB を想定したデータ処理モジュール）

セットアップ手順（開発向け）
1. リポジトリをクローン
   - git clone ... (省略)

2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - requirements.txt がない場合は最低限次のパッケージを入れてください:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（YAML 検証を有効にする場合）
   例:
     - pip install duckdb httpx websocket-client defusedxml pyyaml

4. .env を作成
   - 自動ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 手動で作る場合はプロジェクトルートに .env を置く（下記「環境変数」を参照）。
   - 自動で .env を読み込む仕組みがあります（OS 環境変数 > .env.local > .env）。
     - 自動読み込みを無効化する場合:
       - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前に必ず実行してください）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする（CI 等で有用）:
     - python -m kabusys.validate_config --strict

6. 実行
   - 発注エンジン（Execution）:
     - python -m kabusys.run_execution
     - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient が使われ、paper_trading 用の SQLite（デフォルト data/paper_trading.db）に記録します。
   - 監視プロセス:
     - python -m kabusys.run_monitoring
     - ポーリング間隔を変更する場合:
       - export MONITOR_POLL_INTERVAL=30  （秒）

使い方（主要 CLI）
- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話形式で .env を作成 / 更新します。シークレットはマスク表示されます。
- 設定検証
  - python -m kabusys.validate_config [--strict]
  - .env と config/*.yaml（存在する場合）の存在・妥当性をチェックします。PyYAML 未インストール時は YAML 内容検証をスキップします。
- 実行（ExecutionEngine / monitoring）
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

停止制御・PID / フラグ
- 停止フラグ: data/stop_requested.flag を配置すると監視ループ・エンジンは安全に停止します。
- kill flag: data/kill.flag を置くと ExecutionEngine は起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動クリア可）。
- PID ファイル:
  - デフォルト: data/execution.pid（設定で変更可能）
  - 起動時に PID を書き込む実装があります（セッション終了時に削除）。

主要環境変数（必須 / 任意）
- 必須:
  - JQUANTS_REFRESH_TOKEN  — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD      — kabuステーション API パスワード（必須）
- 任意（デフォルトあり / 推奨設定）:
  - KABUSYS_ENV            — 実行環境 (development | paper_trading | live) （デフォルト: development）
  - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH            — 監視用 SQLite（デフォルト: data/monitoring.db）
  - LOG_LEVEL              — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL      — kabuステーション API のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（本番でのアラート用）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアする（0/1）
  - PAPER_FILL_MODE        — paper_trading 時のモックの fill 動作（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 専用 SQLite（デフォルト data/paper_trading.db）
  - MONITOR_POLL_INTERVAL  — run_monitoring のポーリング間隔（秒、デフォルト 60）

サンプル .env（最小）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

（実運用時は .env を Git 管理しないでください）

ディレクトリ構成（抜粋: src/kabusys）
- __init__.py
- config.py
  - 環境変数の自動ロード（.env/.env.local）、Settings クラス（アプリケーション設定）
- config_setup.py
  - .env 作成用の対話ウィザード
- validate_config.py
  - 起動前に .env と config/*.yaml を検証する CLI
- run_execution.py
  - ExecutionEngine の起動スクリプト（PID / stop flag / DB 接続等）
- run_monitoring.py
  - 監視ループ起動スクリプト（MONITOR_POLL_INTERVAL）
- execution/
  - broker_api.py            — BrokerAPIProtocol、データモデル、ファクトリ
  - broker_factory.py        — Settings から適切な broker を生成
  - kabu_client.py           — KabuStationClient（httpx ベース）
  - mock_client.py           — MockBrokerClient（テスト用）
  - order_record.py          — 注文状態モデルと遷移ロジック
  - order_repository.py      — SQLite を用いた persistence 層
  - order_manager.py         — 発注フロー（作成・送信・同期・取消）
  - execution_engine.py      — 発注エンジン本体（シグナル処理 / push drain / kill）
  - reconciler.py            — 起動時リコンシリエーション / ポジション差分検出
  - risk_manager.py          — Gate1/2/3 のリスク制御
- data/
  - calendar_management.py   — マーケットカレンダー（DuckDB ベース）
  - news_collector.py        — RSS ニュースの収集・正規化

（注）監視用 DB 周りや utils / monitoring モジュールの一部はソース内で参照されていますが、README に示したファイル以外の補助モジュールも存在する可能性があります。

設計上の注意点 / トラブルシュート
- validate_config:
  - PyYAML がインストールされていないと config/*.yaml のパース検証はスキップされ、警告が出ます。
  - --strict を付けると警告も exit code 1 として扱うため CI でのチェックに便利です。
- auto .env 読み込み:
  - Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。テストで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番モード（KABUSYS_ENV=live）:
  - live モードは注意が必要です。validate_config は live 設定時に警告を出すチェックがあり、LINE 通知等の未設定を警告します。
  - BrokerClientFactory は live 用のブローカークライアントを未実装としている箇所があり、現在は paper_trading/development で Mock を使う想定です。
- kill flag と自動クリア:
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動で削除します（開発用）。本番では 0 を推奨します。
- DB パスの親ディレクトリ:
  - DUCKDB_PATH / SQLITE_PATH の親ディレクトリが存在しない場合は警告が出ますが、多くの起動スクリプトは起動時に親ディレクトリを自動作成する場合があります。

貢献・拡張案
- Live broker client（KabuStationClient を本番向けに整備）
- async 化（httpx.AsyncClient, asyncio ベースの WebSocket）
- より詳細な運用ドキュメント（デプロイ手順、監視アラート設計、バックアップ、マイグレーション）
- tests／CI 設定（validate_config を CI に組み込む）

---

問い合わせ・開発メモ
- まずは python -m kabusys.config_setup → python -m kabusys.validate_config を実行し、警告・エラーを解消してから run_execution / run_monitoring を起動してください。
- 本リポジトリはあくまで参照用の構成例・プロトタイプです。実稼働の前に十分な検証と安全対策（アクセス制御、認証情報管理、監査、フェイルセーフ）を行ってください。

以上。