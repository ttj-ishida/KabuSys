KabuSys — 日本株自動売買システム (README)
================================================

概要
----
KabuSys は日本株向けの自動売買（発注・監視）システムのコア実装です。  
主要な機能は発注エンジン（ExecutionEngine）、モニタリングループ、設定管理/検証、データ処理（カレンダー・ニュース収集）などで、ローカル開発（development）、ペーパートレード（paper_trading）、本番（live）を想定した設計になっています。開発中は MockBrokerClient（ブローカーのモック）を用いて kabuステーションを起動せずに動作確認ができます。

主な特徴
--------
- 環境変数ベースの設定管理（.env / .env.local を自動読み込み）
- 設定ウィザード（対話式）で .env を生成・更新
- 設定検証 CLI（必須環境変数のチェック、config/*.yaml の存在と YAML パースチェック）
- 発注ロジック分離（OrderRecord: 状態遷移、OrderRepository: 永続化、OrderManager: 外向き API）
- ExecutionEngine：シグナル読み込み→Gate（リスク）チェック→発注、WebSocket プッシュのドレイン
- リスク管理（Gate1/2/3：余力・重複・ポジション上限、レート制限・サーキットブレーカー、ドローダウン監視）
- 起動時リコンシリエーション（OrderSent 状態の自動照合）
- MockBrokerClient によるテスト容易性（fill_mode の切替等）
- DuckDB / SQLite を使ったデータ保存と監視テーブル

セットアップ（開発向け）
---------------------
1. リポジトリをクローンしてワークディレクトリに移動してください（例）:
   - git clone ... && cd <repo>

2. Python 仮想環境を作成し有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存ライブラリをインストール:
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主要な推奨パッケージ（プロジェクトで利用される可能性が高い）:
     - duckdb, sqlite3（標準ライブラリ）, httpx, websocket-client, PyYAML（yaml チェック用）, defusedxml

   例（最低限）:
     pip install duckdb httpx websocket-client PyYAML defusedxml

4. デフォルトのディレクトリ/ファイル
   - data/ 以下に DB やフラグファイルが作成されます（自動作成されることが多いです）。
   - config/ 以下に YAML 設定ファイル（system_config.yaml 等）を置きます。validate_config では config/*.yaml の存在を確認します。

設定 (.env)
-----------
- .env はプロジェクトルートに置きます（自動で .env → .env.local の順で読み込まれます。OS 環境変数は上書きされません）。
- 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（主なもの、デフォルト/必須）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）

- 任意 / 推奨
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1、デフォルト: 0）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（任意）

- その他: MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）、PID_FILE_PATH、KILL_FLAG_PATH など

使い方（コマンド）
-----------------

1. 設定ウィザード（.env の作成／更新）
   - python -m kabusys.config_setup
   - 対話式に値を入力して .env を生成できます。
   - ウィザード終了後のメッセージに従い python -m kabusys.validate_config で検証してください。

2. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗にする厳格モード:
     python -m kabusys.validate_config --strict

   重要: PyYAML がインストールされていると config/*.yaml のパース検証も行います。インストールされていない場合は警告が出て YAML の内容検証はスキップされます。

3. 実行エンジン起動（発注）
   - python -m kabusys.run_execution
   - KABUSYS_ENV が paper_trading または development の場合は mock ブローカーが使われます（create_broker_api の挙動）。
   - 実行前に kill.flag の存在がチェックされ、KILL_FLAG_CLEAR_ON_START=1 の場合は自動でクリアされます（注意して設定してください）。
   - 実行中に data/stop_requested.flag を作成すると安全に停止処理が行われます。

4. 監視ループ起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（デフォルト 60 秒）。
   - 監視は環境にかかわらず本番用の sqlite_path を使用します（ただし設定で上書き可能）。

設計上の注意点 / 運用メモ
-----------------------
- ExecutionEngine はシグナル処理フェーズ（8:50-9:10）と WebSocket ドレイン（9:10-15:30）を想定しているため、テスト時は個別メソッド（_process_signals や _drain_push_queue）を直接呼ぶことができます。
- OrderManager はクラッシュ安全性のため「OrderSent」状態の永続化を broker 呼び出しの前に行うなど二相的な永続化戦略を採っています。再起動時は Reconciler による同期で整合性回復を行います。
- リスク制御（RiskManager）は Gate1/2/3 を実装。サーキットブレーカーやレート制限、ドローダウンによる kill_switch 発動などを含みます。
- 本番（KABUSYS_ENV=live）では LINE 通知などの必須チェックと警告が強化されます。live を使う場合は十分に設定を確認してください（validate_config は live の場合に追加チェックを行います）。
- .env は絶対に Git にコミットしないでください（config_setup.py の出力ヘッダにも警告があります）。

簡易 .env 例
-------------
（config_setup の出力に合わせた例）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

ディレクトリ構成（要点）
----------------------
src/kabusys/
- __init__.py
  - パッケージ情報（__version__ 等）

- config.py
  - 環境変数の自動読み込みロジック（.env / .env.local）、Settings クラス（設定取得用プロパティ）
  - 必須チェック用の _require() を含む

- config_setup.py
  - 対話式 .env ウィザード（run_wizard / _write_env）

- validate_config.py
  - 起動前の設定検証 CLI（必須環境変数、KABUSYS_ENV の妥当性、YAML パース検査等）

- run_execution.py
  - ExecutionEngine の起動ラッパー（プロセス優先度設定、DB 初期化、停止フラグ監視）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動ラッパー

- execution/
  - broker_api.py — BrokerAPIProtocol、データモデル、ファクトリ
  - kabu_client.py — kabuステーション用 HTTP/WebSocket クライアント実装（KabuStationClient）
  - mock_client.py — テスト用 MockBrokerClient
  - broker_factory.py — Settings に基づくブローカ生成ファクトリ
  - order_record.py — OrderRecord、状態遷移ロジック
  - order_repository.py — SQLite 永続化層（orders テーブルのスキーマと I/O）
  - order_manager.py — 外向け注文 API（作成・送信・同期・キャンセル）
  - execution_engine.py — 発注エンジン（シグナル処理、push 処理、kill switch）
  - reconciler.py — 起動時のリコンシリエーション（OrderSent 照合、ポジション差分検出）
  - risk_manager.py — Gate1/2/3 によるリスク管理

- monitoring/
  - monitoring_db.py, system_monitor.py など（コードベースに含まれる監視関連ロジック）

- data/
  - calendar_management.py — カレンダー管理（営業日判定 / calendar_update_job）
  - news_collector.py — RSS ニュース収集・正規化・DB 保存（SSRF 対策、defusedxml 使用）

- utils/
  - logging_setup.py, process_priority.py などユーティリティモジュール

開発・テストのヒント
--------------------
- MockBrokerClient を使えば kabuステーションを用意せずに発注フローやリコンシリエーション、リスクロジックの単体テストが可能です。
- DuckDB は分析向けに signals / portfolio_targets / market_calendar 等を格納する想定です。テスト用に in-memory で接続することもできます。
- validate_config によるチェックを CI に組み込むと、環境変数漏れや YAML 不整合を事前に検出できます（--strict を CI で使うと警告も失敗扱いにできます）。

追加情報
-------
- config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）は外部設定ファイルです。validate_config は存在確認と（PyYAML があれば）パース検証を行います。必要に応じてスケルトン生成スクリプト（scripts/generate_config.py 等）をプロジェクトに追加してください。
- 本 README はコードの現在の実装（リポジトリに含まれるモジュール）に基づく概要です。詳細な運用手順やデプロイ方法は別途運用ドキュメントを用意することを推奨します。

以上。必要であれば、README にサンプル .env、systemd / Supervisor 用の起動ユニット、CI ワークフローの例、あるいは主要 API の簡単なシーケンス図を追記できます。どの情報を追加しますか？