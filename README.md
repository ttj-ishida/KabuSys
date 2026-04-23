KabuSys — 日本株自動売買システム (簡易 README)
概要
- KabuSys は日本株の自動売買プラットフォーム向けに設計された Python パッケージです。  
  主な機能はシグナルに基づく発注（Execution Engine）、発注の安全化を目的としたリスクガード群、発注状態の永続化とリコンシリエーション、システム監視ループ、データ基盤関連ユーティリティ（市場カレンダー管理、ニュース収集）などです。
- 設定は .env ファイルまたは環境変数から読み込まれ、対話型ウィザードと検証 CLI を備えます。

主な機能一覧
- 設定管理
  - Settings クラスによる環境変数アクセス（自動 .env ロード機能）
  - 対話型 .env 作成ウィザード (python -m kabusys.config_setup)
  - 設定検証 CLI (python -m kabusys.validate_config, --strict オプション)
- 実行（Execution）
  - ExecutionEngine：シグナルの読み込み→Gate1/2 を経て発注、WebSocket push ドレイン
  - OrderManager / OrderRecord / OrderRepository：注文状態管理と SQLite 永続化
  - ブローカーインターフェース（BrokerAPIProtocol）
    - MockBrokerClient（ペーパートレード / 開発用）
    - KabuStationClient（kabuステーション REST API 実装、将来の本番実装）
  - リスク管理（RiskManager）：Gate1（シグナル水準）、Gate2（レート制限・サーキットブレーカー）、Gate3（ドローダウン監視）
  - Reconciler：起動時の OrderSent 状態の復旧・ブローカー照合、ポジション差分検出
- 監視（Monitoring）
  - run_monitoring スクリプト：SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔制御）
  - 監視用 SQLite / DuckDB 接続の初期化をサポート
- データユーティリティ
  - calendar_management：JPX カレンダーの管理・営業日判定（DuckDB 利用）
  - news_collector：RSS 収集と前処理（SSRF/XML脆弱性対策を考慮）
- 補助
  - 環境安全機構（kill.flag / kill switch / PID ファイル / KILL_FLAG_CLEAR_ON_START）
  - 発注のクラッシュ耐性のための二相永続化パターン（OrderSent 前保存 / broker_order_id の先保存 等）

前提（推奨）
- Python 3.10+
- SQLite（標準ライブラリ）
- DuckDB（pip install duckdb）
- httpx（kabu client 用）
- websocket-client（WebSocket push 用）
- defusedxml（ニュース収集の安全な XML パース）
- PyYAML（config/*.yaml の内容検証に任意で使用）
- その他：requests 等は現状の実装により不要だが環境に応じて追加

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone <repo> && cd <repo>
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - 基本例:
     - pip install duckdb httpx websocket-client defusedxml
     - （YAML 検証を使う場合）pip install pyyaml
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
4. .env を作成
   - 対話式ウィザードを利用（推奨）:
     - python -m kabusys.config_setup
     - ウィザードは .env を生成/更新し、必須トークン等の入力を促します。
   - または手動で .env を作成（以下を参照）
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit 1）
6. DB 初期化・実行
   - 実行スクリプト:
     - 実エンジン（ペーパートレード/開発）: python -m kabusys.run_execution
     - 監視ループ: python -m kabusys.run_monitoring

環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 推奨
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（live 時に推奨）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、デフォルト 0）
- .env 自動読み込み
  - プロジェクトルート (.git または pyproject.toml の所在) にある .env を自動読み込みします。
  - OS 環境変数が優先され、.env.local は .env を上書きする形で読み込まれます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

サンプル .env（例）
- .env の一例（必ず各値を実環境用に置き換えてください）
  - JQUANTS_REFRESH_TOKEN=your_jquants_token_here
  - KABU_API_PASSWORD=your_kabu_api_password_here
  - KABU_API_BASE_URL=http://localhost:18080/kabusapi
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO
  - KILL_FLAG_CLEAR_ON_START=0
  - LINE_CHANNEL_ACCESS_TOKEN=your_line_token (optional)
  - LINE_USER_ID=your_line_user_id (optional)

主要コマンド例
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict
- 実行エンジン起動（development/paper_trading）:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60）

運用上の注意
- KABUSYS_ENV=live を使用する場合は特に注意が必要です。validate_config は live 設定で警告を出します（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START=1 など）。
- kill.flag（デフォルト data/kill.flag）を用いて外部から起動中プロセスを安全に停止できます。設定 KILL_FLAG_CLEAR_ON_START が 0 の場合、kill.flag が残っていると起動を拒否します（安全措置）。
- ExecutionEngine は発注のクラッシュ安全性を考慮した永続化シーケンスを採用していますが、実運用では適切な監視・監査ログ、手動オペレーション手順を整備してください。
- 本パッケージは本番ブローカー実装（KabuStationClient）を利用する際、ローカルの kabuステーションアプリが稼働していることが前提となります。現時点で BrokerClientFactory は paper_trading/dev を Mock に割り当て、live は未実装で NotImplementedError を投げます。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・.env 読み込み・Settings
  - config_setup.py         — .env 作成ウィザード CLI
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - execution/              — 発注関連実装
    - __init__.py
    - broker_api.py         — Protocol / データモデル / ファクトリ
    - broker_factory.py     — Settings からクライアント作成
    - kabu_client.py        — kabuステーション REST 実装
    - mock_client.py        — Mock ブローカー（テスト用）
    - order_record.py       — 注文状態モデルと遷移ロジック
    - order_repository.py   — SQLite 永続化レイヤ
    - order_manager.py      — OrderStateMachine の外向け API
    - execution_engine.py   — セッション制御と発注ループ
    - reconciler.py         — 再起動時のリコンシリエーション
    - risk_manager.py       — Gate1/2/3 のリスクガード
  - data/                   — データ関連ユーティリティ（例）
    - calendar_management.py
    - news_collector.py
    - jquants_client.py      — （参照されるが省略されている可能性あり）
  - monitoring/             — 監視関連（SystemMonitor, monitoring_db 等: 一部ファイルは省略）
  - utils/                  — ロギング設定・プロセス優先度等ユーティリティ（参照）
  - strategy/ data/ ...     — 戦略やその他のサブパッケージ（リポジトリにより変動）

開発者向けメモ
- Settings クラスはプロジェクトルートを __file__ の親から .git または pyproject.toml で探索して決定します。配布後は自動 .env 読み込みがスキップされることがあります。
- OrderManager / ExecutionEngine 周りは高いクラッシュ耐性・冪等性を重視した設計になっています。OrderSent の中間状態や broker_order_id の先保存等はリコンシリエーションで回復可能なように考慮されています。
- データベースの初期化関数（init_orders_db, init_monitoring_db 等）を起動時に呼んでテーブル作成を保証してください（多くの起動スクリプトはこれらを実行します）。

ライセンス / 責任
- この README はコードベースに基づく簡易説明です。実運用前にコードの理解と十分なテストを行ってください。金融取引に関わるシステムは法令・規約の遵守と厳重な検証が必須です。

必要があれば以下も提供できます
- requirements.txt の候補
- 詳細な .env.example（コメント付き）
- 実行シナリオ（ローカルペーパートレードの手順）
- 各モジュール（ExecutionEngine, RiskManager, Reconciler 等）の詳細設計ドキュメント

必要な追加情報や出力形式（README.md の整形など）があれば指示してください。