KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株自動売買のための軽量なフレームワークです。  
主要な機能（シグナルの読み取り・発注・リスク管理・リコンシリエーション・監視）を備え、実運用（live）・ペーパートレード（paper_trading）・開発（development）に対応する設計になっています。

主な特徴
--------
- 環境設定ウィザード（.env 作成支援）: python -m kabusys.config_setup
- 起動前設定検証ツール（環境変数・config/*.yaml のチェック）: python -m kabusys.validate_config
- 実行エンジン（ExecutionEngine）: シグナル読み取り → 発注 → WebSocket ドレインループ
- 3 段階のリスクガード（Gate1/2/3）による安全制御（余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視）
- ブローカークライアント抽象化（MockBrokerClient / KabuStationClient）
- 起動時リコンシリエーション（OrderSent の自動突合せ、ポジション差分検出）
- 監視プロセス（SystemMonitor）用のポーリングループ（run_monitoring）
- DuckDB / SQLite を用いたデータ保管・分析基盤

セットアップ
-----------

1. リポジトリをクローンして作業ディレクトリへ
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

3. 必要パッケージをインストール
   - 必須（main 機能）: duckdb, httpx, websocket-client, defusedxml
   - オプション（YAML 検証）: PyYAML
   - 例（概算）:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

   > 注意: このリポジトリに requirements.txt は含まれていないため、上の一覧を参照して適宜インストールしてください。

4. データディレクトリ作成
   - data ディレクトリを作成します（例: mkdir -p data）
   - 実行中に自動作成されることもありますが、権限などで失敗する可能性があるため事前作成を推奨します。

環境変数 / .env
----------------
Settings モジュールはプロジェクトルートの .env / .env.local を自動的に読み込みます（OS 環境変数が最優先）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須の環境変数
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

推奨／任意の環境変数（主なもの）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知トークン（本番でのアラート用、任意）
- LINE_USER_ID — LINE 送信先ユーザー ID（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動的にクリアする（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

簡単な .env の例
- .env ファイルの最小例：
  JQUANTS_REFRESH_TOKEN=your_token_here
  KABU_API_PASSWORD=your_password_here
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - 対話式に必要項目を入力して .env を生成します。

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで終了コード 1 を返します。
  - config/*.yaml の存在と（PyYAML があれば）YAML パースも確認します。
  - 警告やエラーは出力されるので、起動前に確認してください。

- 実行エンジン起動（本番／ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading または development の場合、MockBrokerClient が使われます。
  - paper_trading の場合は settings.paper_sqlite_path（既定: data/paper_trading.db）に分離して記録します。
  - 起動前に stop_requested.flag / kill.flag 等のフラグファイルの有無に注意してください。

- 監視プロセス起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。

注意点・運用上の挙動
--------------------
- KABUSYS_ENV=live の場合は追加チェック（LINE 通知設定や Kill Switch）で警告が出ます。live の設定は慎重に行ってください。
- kill.flag（設定: KILL_FLAG_PATH のデフォルト data/kill.flag）や stop_requested.flag（data/stop_requested.flag）により起動やループの停止を制御します。KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合、kill.flag が存在しても起動時に自動でクリアします（本番では 0 を推奨）。
- ExecutionEngine は起動時に PID ファイルを書き出します（既定: data/execution.pid）。終了時に削除されます。
- database（DuckDB / SQLite）はデフォルトで data 下に保存されます。パーミッションやバックアップ方針を検討してください。
- YAML 設定ファイル（config/*.yaml）は validate_config により確認されます。生成スクリプトはリポジトリ内の scripts/generate_config.py を参照してください（バイナリや存在しない場合は警告になります）。

ディレクトリ構成（主なファイル）
------------------------------
src/
  kabusys/
    __init__.py                — パッケージ定義
    config.py                  — 環境変数/.env 読み込みと Settings
    config_setup.py            — .env 対話式ウィザード
    validate_config.py         — 起動前検証 CLI
    run_execution.py           — ExecutionEngine 起動スクリプト
    run_monitoring.py          — SystemMonitor 起動スクリプト
    execution/                 — 発注周りのモジュール
      broker_api.py            — Broker API の Protocol / 型 / ファクトリ
      kabu_client.py           — KabuStationClient 実装（httpx）
      mock_client.py           — MockBrokerClient（テスト用）
      broker_factory.py        — Settings に応じたクライアント生成
      order_record.py          — 注文状態遷移モデル
      order_repository.py      — SQLite 永続化層
      order_manager.py         — 発注フロー（create/send/sync/cancel）
      execution_engine.py      — ExecutionEngine（シグナル処理・push ドレイン）
      reconciler.py            — リコンシリエーション / 起動時復旧
      risk_manager.py         — Gate1/2/3 のリスク管理ロジック
    data/                      — データ処理モジュール（DuckDB 関連）
      calendar_management.py   — マーケットカレンダー管理
      news_collector.py        — RSS ニュース収集
      (... その他の data モジュール ...)
    monitoring/                — 監視関連（DB 初期化 / SystemMonitor 等）
    utils/                     — ロギング設定・プロセス優先度などユーティリティ

開発・テストに関する補足
-----------------------
- MockBrokerClient を利用することで kabuステーションなしで発注フローをテストできます（fill_mode により instant/partial/never/reject の振る舞いを再現）。
- ExecutionEngine はテスト用途において _process_signals や _drain_push_queue を個別に呼び出すことで短時間での検証が可能です。
- OrderRepository / init_orders_db、monitoring_db の初期化関数があり、テスト用 DB を作成して利用できます。

トラブルシューティング
---------------------
- validate_config で "PyYAML がインストールされていません" の警告が出る場合、YAML の内容検証がスキップされます。PyYAML を入れると config/*.yaml のパースチェックが行われます。
- run_execution/run_monitoring 起動時にファイル書き込み権限やディレクトリが存在しない場合、警告・例外が発生します。data ディレクトリや指定パスの権限を確認してください。
- KABUSYS_ENV の値が unknown の場合、Settings が ValueError を出します。development / paper_trading / live のいずれかを設定してください。

ライセンス・貢献
----------------
（この README ではライセンス情報は明示していません。プロジェクトの LICENSE ファイルを参照してください）

最後に
------
まずは .env を config_setup で作成し、validate_config でチェックした上で run_execution（ペーパートレード）や run_monitoring を試してください。デフォルトで paper_trading/development は MockBrokerClient を使うため、安全に動作確認が行えます。必要があれば README を拡張して運用手順・監視手順・バックアップ手順を追加してください。