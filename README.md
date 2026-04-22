KabuSys
======

日本株自動売買システムのコアライブラリ。  
このリポジトリには、環境設定・検証・監視・発注エンジンの主要コンポーネントが含まれます。  
（本 README は src/kabusys 以下のコードをもとに作成しています）

概要
----
KabuSys は以下の主要機能を持つ自動売買フレームワーク（ライブラリ＋起動スクリプト）です。

- 環境設定ウィザード（.env の対話式生成 / 更新）
- 設定検証 CLI（.env と config/*.yaml の存在・妥当性チェック）
- 発注実行エンジン（ExecutionEngine）
  - signal ベースの発注処理（Gate1/2/3 によるリスク管理）
  - WebSocket push ドレイン処理（ブローカー通知の取り込み）
  - ペーパートレード用の Mock ブローカー対応
- 監視ループ（SystemMonitor を定期実行してメトリクスを記録）
- ブローカークライアント層（kabu station API 抽象化）
- データモジュール（マーケットカレンダー、ニュース収集など）
- 再起動時リコンシリエーション（OrderSent の突合せ・ポジション差分検出）

主な特徴
---------
- 環境依存設定を .env で管理（.env/.env.local を自動ロード）
- Settings クラス経由で型安全に環境変数を取得
- OrderRecord による状態遷移（状態遷移検証、InvalidStateTransitionError）
- 発注フローのクラッシュ耐性（OrderSent を DB に残す二相的永続化設計）
- 3段階のリスクガード（Gate1: シグナル、Gate2: レート制限/CB、Gate3: ドローダウン）
- MockBrokerClient によるテスト容易性（fill_mode: instant/partial/never/reject）
- DuckDB/SQLite を使用したデータ保存（デフォルトパス: data/*.db）

セットアップ
-----------
1. リポジトリをクローン:
   - git clone <repository-url>

2. Python 仮想環境を作成・有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows) .venv\Scripts\activate

3. 依存パッケージをインストール:
   - pip install -r requirements.txt
   ※ requirements.txt がない場合は主要依存を手動でインストール:
     - pip install duckdb httpx websocket-client PyYAML defusedxml

4. データディレクトリを作成（必要なら）:
   - mkdir -p data

5. .env を準備（手動編集またはウィザードを使用）
   - 推奨: python -m kabusys.config_setup

必須環境変数
-------------
以下は実行に必須の環境変数です（validate_config でもチェックされます）。

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

その他の主要環境変数（任意・デフォルトあり）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH: DuckDB データベースファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL: kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- PAPER_FILL_MODE: モックの約定挙動（instant / partial / never / reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env をロードしません（テスト用）

使い方（主な CLI）
-----------------

- 環境設定ウィザード（対話式 .env 生成）
  - python -m kabusys.config_setup
  - オプション: --env-file /path/to/.env

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン（Execution）
  - KABUSYS_ENV=paper_trading を指定してペーパートレードで実行（例）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 開発時はデフォルトで MockBrokerClient を使用（paper_trading/development）
  - 本番環境（KABUSYS_ENV=live）は現時点で実装未完（BrokerClientFactory は NotImplementedError を投げます）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定の自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動ロードします。
  - OS 環境変数 > .env.local > .env の優先順位です。

注意点 / 運用メモ
-----------------
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダにも注意書きがあります）。
- validate_config は PyYAML が未インストールだと YAML ファイルのパース検証をスキップします（警告を出します）。
- ペーパートレード時の DB 分離:
  - 実行エンジンは paper_trading 環境で paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離します。
- Kill Switch:
  - settings.kill_flag_path（デフォルト data/kill.flag）が存在すると起動や運用中に kill_switch を発動します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動で削除して起動します（本番では推奨されません）。
- MockBrokerClient の PAPER_FILL_MODE:
  - instant: 全量約定
  - partial: 部分約定（fill の一部のみ）
  - never: 注文番号は発行するが約定しない（OrderSentPendingError）
  - reject: 発注拒否（OrderRejectedError）
  - 環境変数名: PAPER_FILL_MODE

DB 関連
-------
- 起動スクリプトは必要なテーブル作成処理（init_monitoring_db / init_orders_db など）を呼び出します。初回起動時にテーブルが作成されます。
- デフォルトファイル:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - SQLite (paper_trading): data/paper_trading.db

ディレクトリ構成（要約）
-----------------------
以下は src/kabusys 以下の主なファイルと役割（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数の読み込み / Settings クラス（自動 .env ロード）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前検証 CLI（--strict オプションあり）
  - run_execution.py — ExecutionEngine を起動するスクリプト
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - execution/
    - broker_api.py — ブローカー API のデータモデル、Protocol、例外、ファクトリ
    - kabu_client.py — kabu station REST API クライアント（httpx ベース）
    - mock_client.py — テスト用 MockBrokerClient
    - broker_factory.py — 設定に応じたブローカークライアント生成
    - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン・kill_switch 等）
    - order_record.py — 注文状態モデルと遷移ロジック
    - order_repository.py — SQLite を使った永続化層（orders テーブル）
    - order_manager.py — 発注フローの外向き API（create/send/sync/cancel）
    - reconciler.py — リコンシリエーション（再起動時の突合せ）
    - risk_manager.py — Gate1/2/3 によるリスク制御
    - ...（その他 execution 周辺）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB ベース）
    - news_collector.py — RSS ニュース収集（セキュリティ対策済）
    - jquants_client.py — （データ取得用クライアント、リポジトリに含まれる想定）
  - monitoring/
    - monitoring_db.py — 監視用 DB 初期化・ログ記録（run_monitoring で使用）
    - system_monitor.py — システム監視ロジック（CPU/メモリ/ディスク閾値）
  - utils/
    - logging_setup.py — ロギング初期化
    - process_priority.py — プロセス優先度設定ユーティリティ

サンプル .env（生成される形式の例）
--------------------------------
以下は config_setup で生成される .env に近いサンプルです（機密値は伏せてください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

開発・テストに関する補足
-----------------------
- 自動 .env ロードを無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- unit/integration テストでは MockBrokerClient を使用してブローカー依存を切り離すことを推奨します。
- validate_config や config_setup を CI/運用前チェックに組み込むと安全です。

トラブルシューティング
----------------------
- validate_config が警告・エラーを出す場合は .env を確認し、プレースホルダ（_here / your_value 等）が残っていないか確認してください。
- run_execution 実行時に "kill.flag が存在する" メッセージが出ると起動を拒否します。意図的にクリアする場合は KILL_FLAG_CLEAR_ON_START=1 を利用してください（ただし本番では推奨されません）。
- 本番接続（kabu station）を行う際は KABU_API_BASE_URL と KABU_API_PASSWORD の設定と kabuステーション側の動作確認を行ってください。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスやコントリビューション手順を追記してください）

以上。必要であれば README に「運用チェックリスト」「サンプル docker-compose」や「詳細な DB テーブル定義」「開発向けのユースケース例（発注シナリオ）」などを追加できます。どの情報を優先して拡張しますか？