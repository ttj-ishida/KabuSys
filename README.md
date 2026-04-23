KabuSys — 日本株自動売買システム（README）
概要
- KabuSys は日本株の自動売買を想定した軽量なフレームワークです。  
  主な機能はシグナルに基づく発注エンジン（ExecutionEngine）、ブローカー抽象化（kabu station / モック対応）、起動時の設定ウィザードと設定検証、監視ループ、データ収集ユーティリティ（カレンダー・ニュース等）です。
- 設計方針は「DB と API 呼び出しの責務を分離」「クラッシュ/再起動時の復旧（リコンシリエーション）」「安全なリスクガード（3段階）」です。

主な機能一覧
- 環境設定ウィザード（.env の対話生成 / 更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の事前チェック）
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動スクリプト（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用して paper_trading 用 SQLite に記録
- 監視ループ起動スクリプト（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能
- ブローカー抽象化
  - create_broker_api() により MockBrokerClient または KabuStationClient を提供
- 注文状態管理（OrderRecord）と永続化（SQLite の OrderRepository）
- リスク管理（RiskManager）: Gate1 (signal), Gate2 (execution), Gate3 (metrics)
- リコンシリエーション（Reconciler）: 再起動後の OrderSent 注文の突合、ポジション差分検出
- データユーティリティ
  - マーケットカレンダー管理（duckdb ベース）
  - ニュース収集（RSS、SSRF 対策、テキスト前処理）

セットアップ手順（ローカル開発向け）
1. Python 環境を用意
   - Python 3.10+ を推奨
   - 仮想環境を作成: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストール
   - プロジェクトに requirements.txt がある場合はそれを使用してください。
   - 最低限想定されるパッケージ（例）:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML
     - defusedxml
   - 例: pip install duckdb httpx websocket-client PyYAML defusedxml

3. .env の作成
   - python -m kabusys.config_setup を実行して対話的に .env を作成・更新します。
   - 自動ロード: config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を見つけると自動で .env /.env.local を読み込みます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告があっても exit code 1 で失敗扱いになります。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意の主要変数
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

5. DB 初期化
   - orders テーブル等はコード内の init_* 関数で冪等に作成されます（例: init_orders_db, init_monitoring_db）。
   - 実行スクリプトが起動時に必要に応じてテーブルを作成します。

使い方（主要コマンド例）
- 環境ウィザード（.env を作る）
  - python -m kabusys.config_setup
- 構成検証（起動前）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine を起動（本番・ペーパートレード判定は KABUSYS_ENV）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid（デフォルト）に PID を書きます。停止は data/stop_requested.flag の作成で行えます。
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒単位のポーリング間隔を変更可能（デフォルト 60 秒）
- 注意:
  - 本番環境 (KABUSYS_ENV=live) では追加のガードが働きます（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）。
  - 設定検証は PyYAML の有無により config/*.yaml の内容検証をスキップすることがあります（PyYAML 未インストール時は警告）。

主要な設定項目（.env の例）
- 必須
  - JQUANTS_REFRESH_TOKEN=your_token_here
  - KABU_API_PASSWORD=your_password_here
- 推奨 / 任意
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - LOG_LEVEL=INFO
  - KILL_FLAG_CLEAR_ON_START=0
  - LINE_CHANNEL_ACCESS_TOKEN=
  - LINE_USER_ID=

安全性・運用上のポイント
- KILL FLAG
  - 起動時に data/kill.flag が存在すると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時にクリアし起動可能）。
  - 運用停止は data/stop_requested.flag を作成することでエンジン／監視ループに通知できます。
- リスクガード
  - Gate1: 余力・重複・ポジション上限
  - Gate2: レート制限（トークンバケツ）とサーキットブレーカー
  - Gate3: ドローダウン監視（初期ポートフォリオ評価値に基づく）
- リコンシリエーション
  - 起動時に OrderSent（未完了）注文をブローカーと照合し状態同期する処理が用意されています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込みと Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - execution/                — 発注関連コンポーネント
    - broker_api.py           — Broker API の Protocol, 型, ファクトリ
    - broker_factory.py       — Settings に基づくクライアント生成
    - kabu_client.py          — kabu station REST クライアント
    - mock_client.py          — MockBrokerClient（テスト用）
    - order_record.py         — 注文状態モデルと遷移ロジック
    - order_repository.py     — SQLite 永続化層
    - order_manager.py        — 注文管理（発注 / 同期 / 取消）
    - execution_engine.py     — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py           — リコンシリエーション
    - risk_manager.py         — リスク管理（Gate1/2/3）
  - data/                     — データ関連ユーティリティ
    - calendar_management.py  — マーケットカレンダー管理
    - news_collector.py       — RSS ニュース収集
    - jquants_client.py (参照) — J-Quants クライアント（データ取得用、本コードベースでは参照）
  - monitoring/               — 監視関連（DB 初期化等。init_monitoring_db など）
  - utils/                    — ロギング設定・プロセス優先度等ユーティリティ

トラブルシューティング（よくある事例）
- PyYAML 未インストール: validate_config が YAML 内容検証をスキップ（警告）。
- .env のプレースホルダ値（_here / your_value）: validate_config が警告を出します。実運用前に実値へ置換してください。
- KABUSYS_ENV の値が不正: 有効値は development / paper_trading / live。validate_config や Settings で検出されます。
- DB パスの親ディレクトリがない: 起動時に自動作成される場合がありますが、警告が出ます。data ディレクトリを事前に作成しておくと安全です。

拡張ポイント（将来想定）
- Live 環境向け KabuStationClient の実装強化（現在は制約あり）
- 非同期（async）クライアントへの差し替え（httpx.AsyncClient）
- 監視・アラートの強化（LINE 通知等）

ライセンス・バージョン
- パッケージバージョン: kabusys.__version__ == 0.1.0（該当コード内定義）

最後に
- まずは python -m kabusys.config_setup → python -m kabusys.validate_config を実行し、問題がなければ python -m kabusys.run_execution（開発は KABUSYS_ENV=paper_trading）で動作確認してください。運用前には .env を確実に整備し、必須トークンやパスワードを安全に管理してください。