README.md
=========

概要
----
KabuSys は日本株向けの自動売買システムの小規模フレームワークです。  
本リポジトリには設定管理、監視ループ、発注エンジン、ブローカー抽象化、リスクガード、カレンダー管理、ニュース収集などの主要コンポーネントが含まれます。  
設計方針として「DB とビジネスロジックの分離」「クラッシュ耐性（2相永続化・リコンシリエーション）」「テスト容易性（Mock クライアント）」を重視しています。

主要機能
--------
- 環境設定ウィザード（.env を対話式作成 / 更新）: python -m kabusys.config_setup
- 設定検証ツール（.env と config/*.yaml の事前チェック）: python -m kabusys.validate_config
- 発注エンジン（ExecutionEngine）: シグナル処理 → WebSocket ドレイン、発注・取消・同期を行う
- 監視ループ（SystemMonitor）: 定期ポーリングしてシステム状態を記録
- Broker API 抽象化: 実際の kabu station クライアントと Mock クライアントの切替が可能
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）: 状態遷移の検証と永続化（SQLite）
- リスク管理（RiskManager）: Gate1~3（余力・ポジション上限、レート制限・CB、ドローダウン）
- リコンシリエーション（Reconciler）: 起動時の OrderSent 注文照合とポジション差分検出
- データユーティリティ: DuckDB を利用したカレンダー処理、ニュース収集等

セットアップ
-----------
1. Python (推奨 3.10+) を用意します。
2. 仮想環境を作成・有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストールします（例）:
   - pip install -r requirements.txt
   - 必須/推奨パッケージ（一例）:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML（config/*.yaml の中身検証を行う場合）
     - defusedxml（ニュース収集）
4. プロジェクトルートに .env を配置します（以下の方法を推奨）:
   - python -m kabusys.config_setup
   - ウィザードで対話的に入力すると .env を生成します。

重要な環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード
- 任意 / 推奨（デフォルトあり）:
  - KABUSYS_ENV           : 実行環境 (development / paper_trading / live)
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH           : 監視 DB（デフォルト data/monitoring.db）
  - LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL     : kabu station のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知設定（本番でのアラート用）
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（0/1）
- その他:
  - MONITOR_POLL_INTERVAL : 監視ループのポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE : ペーパートレードの振る舞い ("instant"|"partial"|"never"|"reject")
  - PAPER_TRADING_SQLITE_PATH : ペーパートレードの専用 SQLite パス（分離目的）

自動読み込み
- 設定モジュールはプロジェクトルート（.git または pyproject.toml がある場所）を基準に .env を自動ロードします。
- OS 環境変数が優先され、.env.local が .env を上書きします。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方
------
1. 環境ファイル作成（ウィザード）
   - python -m kabusys.config_setup
   - 既存の .env を読み込んで編集できます。終了後に .env を保存します。

2. 設定検証
   - python -m kabusys.validate_config
   - オプション:
     - --strict : 警告も FAIL として exit code 1 を返します
   - これは .env と config/*.yaml（存在と YAML パース）を起動前にチェックします。

3. 発注エンジン起動（本番相当のセッション）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient を使用（設定の paper_fill_mode に従う）
     - KABUSYS_ENV=live の実運用用 client は現状未実装で NotImplementedError が出ます（将来的な実装余地）
     - execution は pid ファイル（デフォルト data/execution.pid）を書き、 data/stop_requested.flag により停止を検知します
     - 起動時に kill.flag が存在し、KILL_FLAG_CLEAR_ON_START=0 の場合は起動を拒否します

4. 監視ループ起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60）
   - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用します

5. ロギング / 優先度
   - 起動時にプロセス優先度を "high" に設定するユーティリティが実行されます（プラットフォームに依存）

運用上の注意
- 本番（KABUSYS_ENV=live）では LINE 通知設定や KILL フラグなどを必ず確認してください。validate_config は live 設定時に追加ガードを実行します。
- BrokerClientFactory は paper_trading / development では MockBrokerClient（DB 分離）を返しますが、live は未実装です。
- DB の分離: paper_trading 環境は paper_trading 用 SQLite を使用して本番監視 DB とデータ分離します。

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py
  - パッケージ定義、__version__ を含む
- config.py
  - Settings クラス・.env 自動読み込み・環境変数取得ユーティリティ
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前設定チェック CLI（--strict オプションあり）
- run_execution.py
  - ExecutionEngine の起動スクリプト（発注エンジン）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

src/kabusys/execution/
- broker_api.py
  - Broker API の Protocol、データモデル、例外、create_broker_api ファクトリ
- broker_factory.py
  - Settings に応じた Broker クライアントの生成ラッパ
- kabu_client.py
  - kabu station 実装（HTTP + WebSocket）
- mock_client.py
  - 開発・テスト用の MockBrokerClient
- order_record.py
  - 注文状態モデルと状態遷移ロジック（OrderRecord / OrderState）
- order_repository.py
  - SQLite を用いた永続化層（orders テーブル定義・CRUD）
- order_manager.py
  - 外向け注文 API（create/send/sync/cancel）
- execution_engine.py
  - 発注エンジン本体（シグナル読み込み・push ドレイン・kill switch 等）
- reconciler.py
  - 起動時リコンシリエーション（OrderSent の突合・ポジション差分検出）
- risk_manager.py
  - 3段階リスクガード（Gate1~3）

src/kabusys/data/
- calendar_management.py
  - マーケットカレンダー管理（DuckDB ベース）、next_trading_day 等
- news_collector.py
  - RSS ニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去等）
- jquants_client.py (想定)
  - J-Quants へのクライアント（カレンダー等取得に利用）

src/kabusys/monitoring/
- monitoring_db.py (想定)
  - 監視 DB 初期化・書き込みユーティリティ
- system_monitor.py (想定)
  - システムの定期チェック処理

src/kabusys/utils/
- logging_setup.py (想定)
  - ログ出力の設定
- process_priority.py (想定)
  - プロセス優先度の設定ユーティリティ

（注）上記で “想定” とあるファイルはリポジトリ内で使用されているがここに抜粋されていない実装ファイルを指します。

開発者向けメモ
----------------
- 設定の自動ロードは project root（.git / pyproject.toml）を基準に行われます。パッケージ配布後も CWD に依存せず動作する設計です。
- OrderManager はクラッシュ耐性を考慮して「OrderSent を DB に永続化 → ブローカー呼び出し → broker_order_id を先に保存 → OrderAccepted 更新」というフローを採用しています（2相永続化）。
- ExecutionEngine は kill.flag（設定でパス変更可）での外部停止、stop_requested.flag で安全終了をサポートします。
- テストでは MockBrokerClient と paper_trading 環境を使うと本番ブローカー不要で振る舞い検証が可能です。
- config/*.yaml の雛形生成用スクリプト（scripts/generate_config.py）が言及されています。config ファイルの存在は validate_config でチェックされ、PyYAML があればパース検証も行います。

よくあるコマンドまとめ
---------------------
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 発注エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring

ライセンス / 貢献
-----------------
（ここにライセンス・貢献ガイドラインを追記してください）

以上。README に不足している項目（例: 依存パッケージの正確なバージョン、テスト手順、CI 設定等）があれば指示をください。必要に応じてサンプル .env テンプレートも作成します。