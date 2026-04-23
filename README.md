# KabuSys — 日本株自動売買システム（README）

概要
- KabuSys は日本株の自動売買を想定したシステムのコアライブラリです。
- シグナル取得 → リスクガード → 発注 → 約定・監視・リコンシリエーション、という流れを想定したコンポーネント群を含みます。
- 実運用（kabuステーション連携）およびペーパートレード（Mock ブローカー）を想定した切り替えが可能です。

主要な機能一覧
- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup
- 設定検証ツール（.env と config/*.yaml の事前チェック）: kabusys.validate_config
- 実行エンジン（ExecutionEngine）: シグナル処理、発注・プッシュ処理、kill-switch
- ブローカー抽象化（BrokerAPIProtocol）:
  - MockBrokerClient（テスト／ペーパートレード用）
  - KabuStationClient（kabuステーション REST / WebSocket クライアント）
- 注文管理:
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（発注ワークフロー、DB 永続化の二相化など）
- リスク管理（RiskManager）:
  - Gate1 (シグナルレベル)、Gate2 (実行レベル: rate limit / circuit breaker)、Gate3 (ドローダウン監視)
- リコンシリエーション（Reconciler）: 起動時の OrderSent 照合・ポジション差分検出
- 監視ループ（SystemMonitor を用いる run_monitoring スクリプト）
- データユーティリティ:
  - カレンダー管理（JPX 営業日管理、next_trading_day など）
  - ニュース収集（RSS -> raw_news 保存、URL 正規化・SSRF 対策等）

セットアップ手順（開発・ローカル実行向け）
1. 前提
   - Python 3.10 以上（typing の | 記法や一部の構文を使用）
   - システムに sqlite3 ライブラリがあること（通常 Python に同梱）

2. リポジトリを取得
   - git clone ... （プロジェクトルートに移動）

3. 依存パッケージをインストール
   - 必要なライブラリの例:
     - duckdb
     - httpx
     - websocket-client
     - pyyaml (config のパース検証に使用。無くても検証はスキップされます)
     - defusedxml
   - インストール例:
     - pip install duckdb httpx websocket-client pyyaml defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. .env の準備（推奨）
   - 対話式ウィザードで .env を作成／更新:
     - python -m kabusys.config_setup
   - ウィザードは .env の既存値を読み取り、Enter で既存値を再利用できます。
   - 生成後は .env を絶対に Git にコミットしないでください（トークン／パスワード等を含むため）。

5. 設定検証
   - 作成した .env と config/*.yaml を起動前にチェック:
     - python -m kabusys.validate_config
     - すべて合格で exit 0。警告やエラーが出ます。
     - --strict を付けると警告も失敗（exit 1）として扱います。

必須 / 推奨の環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（設定すると機能に影響）:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabuステーションのベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、デフォルト 0）

自動 .env 読み込み
- 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

使い方（主要スクリプト）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン（発注ループ）
  - python -m kabusys.run_execution
  - 備考: KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient が使用されます。live は未実装の旨 NotImplementedError を投げます。
  - 停止制御:
    - 永続化 PID ファイル: data/execution.pid（settings で変更可）
    - 停止指示: data/stop_requested.flag を作成するとループが検出して安全停止します。
    - Kill Switch: data/kill.flag により起動中の kill_switch を誘発します（KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアも可能）。
- 監視ループ（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（settings.sqlite_path）を使用します（paper_trading であっても分離されない点に注意）。

挙動／設計上のポイント
- 発注のクラッシュ耐性:
  - OrderManager.send_order は「OrderCreated → OrderSent（DB commit）→ ブローカー呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移」といった二相永続化を行い、途中クラッシュ時にリコンシリエーションで回復可能な設計です。
- Reconciler:
  - 起動時に OrderSent（不確定）状態の注文をブローカー照合し、状態同期・ポジション差分検出を行います。
- RiskManager（3段階ガード）:
  - Gate1: シグナル単位の余力・重複・ポジション上限検査
  - Gate2: レート制限（token bucket）・サーキットブレーカー
  - Gate3: ドローダウン監視（キルスイッチ）
- MockBrokerClient:
  - paper_trading / development 用。fill_mode により即時約定 / 部分約定 / never / reject の挙動を模擬できます。

データベース
- DuckDB: 分析用（signals、portfolio_targets、position_entries 等を想定）
  - デフォルト: data/kabusys.duckdb（環境変数 DUCKDB_PATH）
- SQLite: 監視・注文永続化用
  - デフォルト: data/monitoring.db（環境変数 SQLITE_PATH）
  - paper_trading 実行時は settings.paper_sqlite_path（data/paper_trading.db がデフォルト）を使用して本番 DB と分離

ログ / プロセス優先度
- 起動スクリプトは setup_logging を呼んでログを設定します（LOG_LEVEL 環境変数で調整）。
- 起動直後に set_process_priority("high") を呼んでプロセス優先度を上げる処理が含まれています（プラットフォーム依存）。

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数読み込みロジックと Settings クラス
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 起動前の設定検証ツール
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py              — BrokerProtocol / データモデル / ファクトリ
      - kabu_client.py             — kabuステーション REST/WebSocket 実装
      - mock_client.py             — テスト用 Mock ブローカー
      - broker_factory.py          — Settings に基づくブローカー生成
      - order_record.py            — 注文状態モデルと遷移ロジック
      - order_repository.py        — SQLite 永続化層
      - order_manager.py           — 発注ワークフロー（DB + broker）
      - execution_engine.py        — セッション実行（シグナル処理＋push drain）
      - reconciler.py              — リコンシリエーション処理
      - risk_manager.py            — 3 段階リスクガード
      - ... その他（order_* 等）
    - data/
      - calendar_management.py     — 市場カレンダー管理（DuckDB と J-Quants 連携想定）
      - news_collector.py          — RSS ニュース収集
      - ...（jquants_client 等外部モジュール想定）
    - monitoring/
      - monitoring_db.py           — 監視用 SQLite テーブル初期化等（参照あり）
      - system_monitor.py          — 監視ロジック（参照あり）
    - utils/
      - logging_setup.py           — ログ初期化ユーティリティ（参照あり）
      - process_priority.py        — プロセス優先度設定ユーティリティ（参照あり）
    - config/                      — yaml 設定ファイル群（system_config.yaml 等）
- data/                            — デフォルト DB / PID / flag ファイル置き場（実行時自動作成想定）
- .env, .env.local (生成・配置する)

補足・運用のヒント
- .env は機密情報を含むため、必ず .gitignore に追加し、リポジトリへコミットしないでください。
- validate_config は PyYAML 未インストールでも動作しますが、YAML の内容検証がスキップされます。可能なら pyyaml をインストールしてください。
- 本番運用時は KABUSYS_ENV=live を指定できますが、README に含まれる KabuStationClient の直接利用や Live ブローカーの実装状況に留意してください（本リポジトリ内では live 向けのクライアント実装が未整備な箇所があります）。
- 停止・緊急停止は stop_requested.flag / kill.flag / KILL_FLAG_CLEAR_ON_START の組み合わせで制御できます。起動時に残った kill.flag による誤起動防止設定に注意してください。

ライセンス / 責任
- この README はコードベース（ソース群）を元に自動生成的にまとめたものであり、実際の運用や細部の挙動はコードを参照してください。
- 本システムを実際の資金で運用する場合は十分なテスト・レビューを行ってください。

以上。プロジェクトの特定の機能や使い方についてさらに詳しいドキュメント（API リファレンスや運用手順）が必要であれば教えてください。必要に応じてコマンド例や .env のサンプル、典型的な運用フローを追加で作成します。