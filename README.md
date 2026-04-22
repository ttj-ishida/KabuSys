# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ＋起動スクリプト）の一部です。  
このリポジトリは発注エンジン、監視、設定ウィザード、環境検証ツールなどを含み、ローカル開発／ペーパートレード／本番（live）モードを想定した設計になっています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方
- 環境変数一覧（主要）
- 実行時のファイル／フラグ
- ディレクトリ構成

---

プロジェクト概要
- 発注エンジン（ExecutionEngine）を中心に、ブローカークライアント（実機／モック）、リスク管理、発注永続化（SQLite）、監視（Monitoring）、カレンダー管理、ニュース収集などの機能を提供します。
- 環境は `development` / `paper_trading` / `live` を想定。`paper_trading` は発注をモック化して専用のペーパートレード用 SQLite DB に記録します。`live` は本番想定の挙動（要注意）。
- .env ファイル読み込みの仕組みがあり、プロジェクトルート（.git または pyproject.toml を基準）から自動的に `.env` / `.env.local` を読み込みます（無効化可能）。

主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話式に .env を作成／更新
- 設定検証ツール（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在や基本的整合性を起動前にチェック
- 実行エンジン（python -m kabusys.run_execution）
  - Signal Queue ベースの発注ループ、リコンシリエーション、kill-switch 等
- 監視ループ（python -m kabusys.run_monitoring）
  - SystemMonitor のポーリングループ（監視用 DB に記録）
- ブローカークライアント抽象化
  - MockBrokerClient（テスト／開発用）
  - KabuStationClient（kabuステーションREST API 実装）
- 注文状態管理（OrderRecord / OrderState）
- 永続化レイヤ（OrderRepository: SQLite）
- リスク管理（3段階: Gate1/2/3）およびサーキットブレーカー
- データ関連ユーティリティ（DuckDB を用いたカレンダー管理、ニュース収集）

セットアップ手順（ローカル開発向け）
1. Python 環境を用意（推奨: 3.10+）
2. 必要な依存パッケージをインストール（例）
   - pip install -r requirements.txt
   - 主要な依存: duckdb, httpx, websocket-client, PyYAML（任意）, defusedxml
   - 注意: 実際の requirements.txt はプロジェクトに合わせて用意してください
3. .env の作成
   - 対話式ウィザードで生成するのが簡単:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成
   - .env は決して Git にコミットしないでください
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります
5. DB 初期化
   - Execution / Monitoring が起動すると必要テーブルを作成します（init_* 関数で冪等に初期化）
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

使い方（主要コマンド）
- 環境設定ウィザード（.env を作成／更新）
  - python -m kabusys.config_setup
  - オプション: --env-file /path/to/.env
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔上書き: MONITOR_POLL_INTERVAL（秒、デフォルト60）
  - 停止フラグ: data/stop_requested.flag を作成するとループが終了します
- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - ExecutionEngine は PID ファイルにプロセスIDを書きます（デフォルト: data/execution.pid）。kill.flag による安全停止（詳細は下記）を尊重します。

主要な環境変数（デフォルト値や説明）
- 必須（起動に必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- オプション（主なもの）
  - KABUSYS_ENV (development | paper_trading | live) — 実行環境（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 SQLite ファイル（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意、本番では必須推奨）
  - LINE_USER_ID — LINE 通知先ユーザー ID（任意、本番では必須推奨）
  - PAPER_FILL_MODE — paper_trading のモック発注動作（instant|partial|never|reject、デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 sqlite（デフォルト: data/paper_trading.db）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番は 0 推奨）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

起動時のファイル・フラグ
- data/kill.flag（デフォルトパスは KILL_FLAG_PATH 環境変数で変更可）
  - 発注エンジンは kill.flag を検出すると kill_switch を起動し、全 active 注文をキャンセルして停止します。
  - KILL_FLAG_CLEAR_ON_START=1 のときは起動時に自動でクリアされます（本番での使用は注意）。
- data/stop_requested.flag
  - run_monitoring / run_execution の外部停止用フラグ。ファイルが存在するとループを終了します。
- PID ファイル
  - 実行エンジンは PID をファイルに書きます（デフォルト: data/execution.pid）。監視プロセスも同様に pid ファイルを用いる場合があります。

設定ファイル（config/*.yaml）
- system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
- validate_config はこれらの存在と（PyYAML がインストールされていれば）パースを検証します。
- config/*.yaml がない場合、スクリプトで生成できる旨の注意メッセージが出ます（scripts/generate_config.py がある想定）。

重要な実装上の注意
- 発注フローはクラッシュ耐性を意識しており、OrderCreated → OrderSent の永続化を broker 呼び出し前に行い、broker_order_id を先に保存してから最終状態遷移をコミットするなどの2相的な永続化戦略を取っています。Reconciler による再同期で安全に復旧できます。
- paper_trading モードは本番 DB と分離して paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
- KabuStationClient は httpx（同期）と websocket-client を使って REST / WebSocket を扱います。ローカルの kabuステーション アプリが必要な点に注意してください（mock を利用してテスト可能）。
- .env 自動読み込みは OS 環境変数 > .env.local > .env の順。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル .env（最低限の必須項目）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み & Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py      — Settings に依存してクライアント生成
    - kabu_client.py         — kabu station REST/WebSocket 実装
    - mock_client.py         — テスト／開発用モック
    - order_record.py        — 注文状態モデルと遷移ロジック
    - order_repository.py    — SQLite ベースの永続化層
    - order_manager.py       — 発注フロー（OrderState Machine 結合）
    - execution_engine.py    — セッション管理（Signal 処理 / WebSocket ドレイン）
    - reconciler.py          — 再起動時のリコンシリエーション
    - risk_manager.py        — Gate1/2/3 のリスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS 収集／前処理
  - monitoring/               — 監視関連（DB 初期化、SystemMonitor 等が存在する想定）
  - utils/                    — ロギング設定・プロセス優先度等ユーティリティ（使用あり）

開発／テストに関するヒント
- 実機を使わない場合は KABUSYS_ENV=paper_trading または development を指定し、PAPER_FILL_MODE を調整して MockBrokerClient の挙動を変えられます（instant / partial / never / reject）。
- 設定を変更したら python -m kabusys.validate_config で確認してください。
- データベースファイルは data/ 以下にデフォルトで作成されます。テスト中にクリーンアップする場合はこれらを削除してください。

ライセンスや貢献ガイドラインはリポジトリのルートに合わせて追加してください。

問題報告・改善提案
- バグ報告や機能リクエストは Issue を立ててください。起動に関するエラーや環境変数に関するエラーは validate_config の出力を添えていただけると対応が早くなります。

以上。必要であれば、README に含める具体的なコマンドの実行例や .env.example の完全版、requirements.txt の候補を作成します。どの情報を追記しますか？