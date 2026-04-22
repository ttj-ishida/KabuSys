README
======

概要
----
KabuSys は日本株向けの自動売買システムの参照実装です。本リポジトリは以下の主要機能を持つモジュール群で構成されています:

- 環境変数 / 設定管理（.env 自動ロード / ウィザード）
- 設定検証 CLI（起動前に .env と config/*.yaml をチェック）
- 発注エンジン（ExecutionEngine） — シグナルを読み込みブローカーへ発注
- ブローカー抽象化層（実ブローカー / モック対応）
- 注文状態管理（State Machine）と永続化（SQLite）
- 起動時リコンシリエーション（Reconciler）
- リスク管理（3段階ガード）
- 監視ループ（SystemMonitor のポーリング）
- データ側ユーティリティ（マーケットカレンダー、ニュース収集等）

本 README はセットアップ手順・使い方・主要ファイルの説明をまとめたものです。

主な機能
--------
- 環境設定ウィザード: python -m kabusys.config_setup による対話的 .env 生成/更新
- 設定検証: python -m kabusys.validate_config (--strict オプション有)
- 発注エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV に応じて MockBrokerClient（paper_trading / development）を使用
  - 発注フローはクラッシュ耐性を考慮した 2 相永続化を採用
  - kill.flag / stop_requested.flag による運用制御
- 監視プロセス起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可（デフォルト: 60秒）
  - 監視 DB は環境に関係なく本番 sqlite_path を使用
- ブローカー抽象化: BrokerAPIProtocol（実装: KabuStationClient / MockBrokerClient）
- 注文の永続化: SQLite（orders テーブル、一意制約による重複防止）
- リスク管理: Gate1~3 による発注前・送信前・約定後の保護
- カレンダー / ニュース収集ユーティリティ（DuckDB / J-Quants 想定）

前提条件
--------
- Python 3.10 以上
- DuckDB（Python パッケージ duckdb）
- httpx, websocket-client（kabu station クライアント使用時）
- defusedxml（ニュース収集）
- PyYAML（config/*.yaml の内容検証を行う場合に必要。無ければ警告を出してスキップ）
- なお SQLite は標準ライブラリで利用可能です。

インストール例（仮）
- requirements.txt がある場合:
  pip install -r requirements.txt
- 個別にインストールする場合の例:
  pip install duckdb httpx websocket-client defusedxml pyyaml

環境変数（重要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトあり・あるいは運用に応じて設定）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知設定（本番環境では必須推奨）
- その他: KILL_FLAG_CLEAR_ON_START, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等

.env の自動ロードについて:
- 起動時にプロジェクトルート（.git または pyproject.toml を探索）を見つければ .env（→ .env.local）を自動的に読み込みます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
------------
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. Python 環境作成（推奨: venv）
   python -m venv .venv
   source .venv/bin/activate  # Windows は .venv\Scripts\activate

3. 依存パッケージをインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は上記の必要パッケージを個別にインストール）

4. 初期 .env を作成（対話式ウィザード）
   python -m kabusys.config_setup
   - ウィザードに従って必須トークンや設定を入力してください。
   - 生成された .env は Git にコミットしないでください（README 内の注意に従って下さい）。

5. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いして exit 1 で終了します。
   - PyYAML が入っていれば config/*.yaml のパース検証も行います。

使い方
------
- 発注エンジンを起動（development / paper_trading の場合モックブローカーを使用）
  python -m kabusys.run_execution

  運用メモ:
  - run_execution は data/execution.pid 等の PID ファイルを作成します（設定で変更可）。
  - 停止要求: data/stop_requested.flag を作成すると安全停止をリクエストできます（監視ループ / エンジンが検出して終了）。
  - kill.flag: 即時 kill switch を発動するために使用。起動時に存在すると KILL_FLAG_CLEAR_ON_START の値次第で動作が変わります（0: 起動拒否、1: 自動クリアして起動）。

- 監視プロセスを起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。

- 設定検証（再掲）
  python -m kabusys.validate_config [--strict]

- 設定ウィザード（再掲）
  python -m kabusys.config_setup [--env-file PATH]

.env の最小例
--------------
以下は最小限の例（必須のみ）。実際には .env ウィザードを使って生成してください。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

運用上の注意
------------
- .env は絶対にリポジトリにコミットしないでください（API トークンやパスワードが含まれます）。
- 本番（KABUSYS_ENV=live）では LINE 通知の設定を必ず確認し、KILL_FLAG_CLEAR_ON_START を誤って 1 にしないでください。
- run_execution は paper_trading モードであれば paper_trading 用の SQLite（data/paper_trading.db）を使用して本番 DB と分離します。
- 起動前に python -m kabusys.validate_config を実行して設定ミスを検出してください。

ディレクトリ構成（主要ファイル）
-----------------------------
プロジェクトルートからの主要ファイル・ディレクトリ（src/kabusys 以下）:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の自動読み込み、Settings クラス
- src/kabusys/config_setup.py
  - .env 対話式ウィザード
- src/kabusys/validate_config.py
  - 起動前の設定検証 CLI
- src/kabusys/run_execution.py
  - ExecutionEngine を起動するスクリプト
- src/kabusys/run_monitoring.py
  - SystemMonitor をポーリングするスクリプト
- src/kabusys/execution/
  - broker_api.py — Protocol / データモデル / ファクトリ
  - kabu_client.py — kabu station 実装（httpx + websocket）
  - mock_client.py — テスト用モックブローカー
  - broker_factory.py — Settings に応じたクライアント生成
  - order_record.py — 注文状態・遷移（State Machine）
  - order_repository.py — SQLite 永続化層
  - order_manager.py — 発注の外向き API（DB + broker 連携）
  - execution_engine.py — セッション管理・シグナル処理・WebSocket ドレイン
  - reconciler.py — 起動時のリコンシリエーション
  - risk_manager.py — Gate1/2/3 によるリスク管理
- src/kabusys/data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB）
  - news_collector.py — RSS ニュース収集（defusedxml 等を使用）
- src/kabusys/monitoring/
  - monitoring_db.py, system_monitor.py など（実装ファイルは本 README のコード参照）
- src/kabusys/utils/
  - logging_setup.py, process_priority.py などのユーティリティ

（上記は主要なファイルを抜粋しています。詳細はソースをご参照ください。）

開発者向けメモ
---------------
- Settings クラスは環境変数の検証（値の正当性チェック）を行います。テストから自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OrderManager / OrderRepository / OrderRecord の責務は明確に分離されています:
  - OrderRecord: 純粋なビジネスロジック（状態遷移）
  - OrderRepository: DB の読み書きのみ
  - OrderManager: 上記を組み合わせて発注ロジックを実装
- ブローカーの実運用用クライアント（KabuStationClient）は同期 httpx クライアントを使用。将来的に async 化する場合は httpx.AsyncClient に置き換え可能です。

ライセンス
---------
（ここにプロジェクトのライセンス情報を記載してください。該当情報がない場合は適宜追加してください。）

補足
----
- config/*.yaml の存在・構文チェックは PyYAML がインストールされている場合に行われます。ない場合は警告を出してスキップします。
- ニュース収集やカレンダー更新等の外部 API 呼び出しを行う機能は、各 API の利用規約に従ってください。

問題・貢献
----------
バグ報告や改善提案は Issue を立ててください。プルリクエスト歓迎します。

--- 

この README はコードベースの主要機能と運用手順をまとめたものです。実行時の詳細や追加のユーティリティはソースコード内の docstring とコメントを参照してください。