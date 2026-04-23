# KabuSys

日本株自動売買システム（KabuSys）のコードベース用 README（日本語）

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（よく使うコマンド）
- 主要環境変数
- .env 作成ウィザードと検証
- 起動時の挙動（paper/live の違い等）
- ディレクトリ構成（主要ファイルの説明）
- 備考

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムのコア実装です。
- 発注エンジン（ExecutionEngine）、注文管理（OrderManager / OrderRepository）、リスクガード（RiskManager）、リコンシリエーション（Reconciler）、監視ループ（SystemMonitor を用いた run_monitoring）やデータ周り（マーケットカレンダー、ニュース収集）など、実運用を意識したモジュール群を提供します。
- 本リポジトリには実際の kabuステーション API クライアント（KabuStationClient）と、テスト/ペーパートレード用のモッククライアント（MockBrokerClient）が含まれます。

主な機能
- 環境設定自動読み込み（.env / .env.local）および Settings 抽象化
- .env の対話式ウィザード（config_setup）
- 起動前設定検証 CLI（validate_config）
- ExecutionEngine：シグナル取得→Gate1/Gate2（リスク検査）→発注→WebSocket push ドレインのフロー
- OrderState を厳密に扱う OrderRecord と状態遷移検証
- SQLite を用いた注文永続化（OrderRepository）と監視 DB 初期化
- Reconciler：クラッシュ後の OrderSent 状態の復旧とブローカー照合
- RiskManager：3段階（シグナルレベル・エグゼキューションレベル・メトリクスレベル）のリスクガード（レート制限・サーキットブレーカー・ドローダウン監視 等）
- KabuStation REST/WebSocket クライアント（httpx + websocket-client）
- MockBrokerClient：テスト用の発注挙動（instant, partial, never, reject）
- データモジュール：マーケットカレンダー（DuckDB 経由）・ニュース収集（RSS）など
- 監視ループ（run_monitoring）: sqlite／duckdb に接続して定期的に監視を実行

セットアップ手順（開発環境向け）
1. Python バージョン
   - Python 3.10 以上を推奨（PEP 604 の型記法等を利用）。
2. リポジトリをクローン
   - git clone <repo-url>
3. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 必要パッケージをインストール
   - 代表的な依存（実際の requirements.txt がある場合はそれを利用してください）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - pyyaml (YAML 検証を行いたい場合に必要)
   - 例:
     - pip install duckdb httpx websocket-client defusedxml pyyaml
5. データディレクトリ作成
   - data ディレクトリは起動時に自動で作成されることが多いですが、手動で作る場合:
     - mkdir -p data
6. 環境変数設定（.env）
   - 対話式ウィザードを使って .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定する必要があるもの）は README 下部の「主要環境変数」を参照

使い方（主要コマンド）
- .env 作成ウィザード
  - python -m kabusys.config_setup
  - オプション: --env-file を指定すると別パスに保存可能
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする（CI 等で厳格化）:
    - python -m kabusys.validate_config --strict
- 実行エンジン起動（本番／ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて mock/live のクライアントが選ばれます（現状 live は未実装で NotImplementedError を投げます）。paper_trading / development は MockBrokerClient を使用。
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）

主要環境変数（概要）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意／設定可能（主要なもの）:
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL — kabu station のベース URL（デフォルト http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0。production では 0 推奨）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- 注意:
  - validate_config は .env / config/*.yaml の欠如や不整合を事前に検出できます。CI に組み込むと安全です。

.env 作成ウィザードと検証
- python -m kabusys.config_setup
  - 対話形式で .env（または指定したパス）を作成します。シークレット項目は入力時にマスクされます。
  - 生成後は python -m kabusys.validate_config で設定検証を実行してください。
- python -m kabusys.validate_config [--strict]
  - .env による環境変数、config/*.yaml の存在と YAML パース（PyYAML がインストールされている場合）をチェックします。
  - --strict を付けると警告も exit code 1（FAIL）になります。

起動時の挙動（paper_trading と live の主な違い）
- KABUSYS_ENV=development または paper_trading:
  - Broker は MockBrokerClient（create_broker_api(mock=True,..)）を使用。発注・約定の振る舞いは fill_mode で制御できます（instant/partial/never/reject）。
  - paper_trading 時は SQLite の保存先が paper_trading 用に切り替わり（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）本番 DB と分離されます。
- KABUSYS_ENV=live:
  - 実際に KabuStationClient（実ブローカー）を使う想定ですが、現状の BrokerClientFactory では NotImplementedError を返す箇所があります。導入時は実装状況を確認してください。
- kill.flag
  - data/kill.flag（パスは Settings.kill_flag_path）を検出すると起動・ループで kill_switch がトリガーされ、全 active 注文をキャンセルします。
  - KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動で kill.flag をクリアして起動します（本番では推奨されません）。

ディレクトリ構成（src/kabusys の主要ファイルと説明）
- __init__.py
  - パッケージメタ（__version__ 等）
- config.py
  - 環境変数読み込み・Settings クラス（.env 自動読み込みロジックとアクセサ）
- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前チェック CLI（python -m kabusys.validate_config）
- run_execution.py
  - ExecutionEngine を組み立てて起動するエントリスクリプト
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- execution/
  - broker_api.py: BrokerAPIProtocol、データモデル、例外、ファクトリ
  - broker_factory.py: Settings を見て適切なブローカークライアントを返す
  - kabu_client.py: kabuステーション用の同期 REST/WebSocket クライアント（httpx, websocket-client）
  - mock_client.py: MockBrokerClient（テスト用）
  - order_record.py: OrderRecord と OrderState（状態遷移ロジック）
  - order_repository.py: SQLite ベースの永続化層（orders テーブルの初期化含む）
  - order_manager.py: OrderRecord と OrderRepository を組み合わせた外向き API（create/send/sync/cancel）
  - execution_engine.py: ExecutionEngine（シグナル処理・push ドレイン・kill_switch 等）
  - reconciler.py: 再起動時のリコンシリエーション処理
  - risk_manager.py: 3段階リスクガード（Gate1/2/3）
- data/
  - calendar_management.py: マーケットカレンダー管理（DuckDB 側のロジック）
  - news_collector.py: RSS 収集・前処理・DB 保存ロジック
  - jquants_client.py (参照されるが実装は別途)
- monitoring/
  - monitoring_db.py (監視 DB 初期化・ログ記録等、参照箇所あり)
  - system_monitor.py (SystemMonitor 実装、run_monitoring から使用)
- utils/
  - logging_setup.py（ロギング設定）
  - process_priority.py（プロセス優先度設定）
  - その他ユーティリティ群

備考 / 運用上の注意
- config/*.yaml（system_config.yaml など）はプロジェクトルートの config ディレクトリに置く想定です。validate_config は存在チェックと YAML パースを行います（PyYAML が必要）。
- DB ファイル（DuckDB / SQLite）はデフォルトで data/ 配下に作成されます。パスは環境変数で上書き可能です。
- 実ブローカー（kabuステーション）を使う場合はローカルの kabu station アプリの起動・API 設定が必要です。Credential の扱いには十分注意してください（.env は絶対に Git にコミットしないでください）。
- Reconciler は起動時に OrderSent の不確定注文を broker と照合し、ポジション差分を検出してログ出力します。クラッシュからの安全復旧のために Reconciler を有効にしてください。
- ログレベルや通知設定（LINE）を正しく設定しておくと、本番運用での可観測性が向上します。

以上が README のサマリーです。必要であれば README.md に含めるサンプル .env.example（テンプレ）や、実行例（systemd ユニットや Dockerfile の例）、CI に組み込む validate_config の使用例も追加できます。どの情報をより詳しく追記するか指示ください。