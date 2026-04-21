KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を想定した軽量フレームワークです。  
主に以下を目的としたコンポーネントを含みます:

- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注状態管理・永続化（SQLite）
- ブローカークライアントの抽象化（実運用向け / モック）
- リコンシリエーション（再起動時の状態復旧）
- 監視ループ（SystemMonitor）
- データ関連ユーティリティ（マーケットカレンダー、ニュース収集等）
- 環境設定ウィザードと起動前検証ツール

特徴
----
- 明確に分離されたレイヤ（APIクライアント / 注文ロジック / 永続化 / リスク制御）
- Paper trading 用モッククライアントにより実資金不要での動作確認が可能
- 起動時の設定検証（.env / config/*.yaml）を行う CLI
- 再起動後に OrderSent 状態の注文をブローカーと突合して整合性を回復する Reconciler
- 3 段階のリスクガード（Gate1: シグナル／ポジション、Gate2: レート制限＆CB、Gate3: ドローダウン）

必須 / 主要機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証ツール（python -m kabusys.validate_config）
- ExecutionEngine（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し paper_trading 用 SQLite に記録
- SystemMonitor（python -m kabusys.run_monitoring）
- Broker API 抽象（BrokerAPIProtocol）とファクトリ（create_broker_api）
- 注文状態管理（OrderRecord）と注文管理 API（OrderManager）
- 注文永続化（OrderRepository / SQLite）
- リスク管理（RiskManager）
- データ処理ユーティリティ（calendar_management, news_collector 等）

セットアップ手順
----------------
※ 以下は一般的なセットアップ手順の例です。プロジェクト固有の追加手順（pyproject.toml / requirements.txt）がある場合はそちらに従ってください。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限の推奨パッケージ例:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（config の YAML 検証を有効にする場合）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

4. .env の作成
   - 初回は環境設定ウィザードを使うと簡単です（下記参照）。
   - あるいは .env.example をコピーして編集してください（リポジトリにある場合）。

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も異常扱い（exit code=1）になります

環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意/推奨:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — paper_trading 時の専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト: 0）
- 自動ロード:
  - プロジェクトルートにある .env（および .env.local）を自動で読み込みます。OS 環境変数は上書きされません。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主要 CLI）
-----------------

1) 環境設定ウィザード
- コマンド:
  - python -m kabusys.config_setup
- 機能:
  - 対話式に主要な環境変数を入力して .env を生成／更新します。
  - シークレット項目は入力時にマスク扱い。
  - ウィザード実行後に .env を保存するか確認があります。

2) 起動前設定検証
- コマンド:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告もエラー扱いにする）
- 機能:
  - 必須環境変数・フォーマット・DB パスの親ディレクトリ存在・config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV が live の場合の追加ガード等をチェックします。
  - exit code: エラーあり→1、警告のみ（非 strict）→0（警告数を表示）

3) 実行エンジン（本番/ペーパートレード）
- コマンド:
  - python -m kabusys.run_execution
- 備考:
  - Settings から KABUSYS_ENV を参照し、paper_trading では MockBrokerClient を使い paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込みます。
  - PID ファイル（デフォルト: data/execution.pid）や kill.flag（data/kill.flag）を使用した起動・停止ガードを備えています。

4) 監視ループ（SystemMonitor）
- コマンド:
  - python -m kabusys.run_monitoring
- 備考:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定（秒、デフォルト 60）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計です。
  - 停止は data/stop_requested.flag を作成することでループ内で検出して終了できます。

運用上の注意点
- 本番環境（KABUSYS_ENV=live）は特に注意が必要です。validate_config は live での設定不足を警告します（LINE 通知未設定など）。
- kill.flag（KABUSYS 側で定義されたパス）や stop_requested.flag を使って安全に停止／キルスイッチが動作します。KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると危険です（自動クリアされます）。
- Paper trading と本番データベースは分離されています。paper_trading 用の DB を別に持つことで誤操作・データ混在を防止します。

ディレクトリ構成（src/kabusys）
-------------------------------
主要ファイル／モジュールの概観:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数自動ロード、Settings クラス（アプリ設定アクセス）
  - config_setup.py
    - .env を対話式に生成／更新するウィザード
  - validate_config.py
    - .env および config/*.yaml の起動前チェック CLI
  - run_execution.py
    - ExecutionEngine の起動スクリプト（PID / stop flag ハンドリング）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - execution/  (発注周り)
    - broker_api.py
      - BrokerAPIProtocol、データモデル、例外、create_broker_api ファクトリ
    - broker_factory.py
      - Settings に応じたブローカークライアント生成
    - kabu_client.py
      - kabuステーション REST API 実装（httpx 使用）
    - mock_client.py
      - テスト・開発用モック実装（fill_mode 等を制御可能）
    - execution_engine.py
      - ExecutionEngine（セッション・シグナル処理・push ドレイン等）
    - order_record.py
      - Order の状態モデルと状態遷移検証（状態遷移図を持つ）
    - order_repository.py
      - SQLite を用いた永続化層（orders テーブル / インデックス定義）
    - order_manager.py
      - 外向きの注文 API（create/send/sync/cancel）とクラッシュ安全性設計
    - reconciler.py
      - 起動時の OrderSent 照合およびポジション差分検出
    - risk_manager.py
      - Gate1〜3 によるリスクガードとサーキットブレーカー、レート制御
  - data/
    - calendar_management.py
      - マーケットカレンダーの管理（J-Quants 連携想定）
    - news_collector.py
      - RSS ベースのニュース取得・前処理・保存ロジック
    - jquants_client.py (参照箇所あり)
      - J-Quants API との連携用クライアント（リポジトリに依存する想定）
  - monitoring/
    - monitoring_db.py (参照される)
    - system_monitor.py (参照される)
  - utils/
    - logging_setup.py
    - process_priority.py

サンプル .env（config_setup により生成される例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0
- （任意）LINE_CHANNEL_ACCESS_TOKEN=...
- （任意）LINE_USER_ID=...

トラブルシューティング
-----------------------
- validate_config で YAML パースチェックがスキップされる:
  - PyYAML がインストールされていないためです。pip install PyYAML を行うと YAML の中身チェックが有効になります。
- 起動時にデータディレクトリや DB 親ディレクトリが無いと警告が出ます:
  - 利用時に自動作成される場合がありますが、明示的に data/ ディレクトリ等を作成しておくと良いです。
- WebSocket / HTTP 接続エラー:
  - kabu station が動作しているか、KABU_API_BASE_URL が正しいかを確認してください。

開発者向けメモ
---------------
- ExecutionEngine はテスト用に _process_signals() と _drain_push_queue() を直接呼べる構造にしてあり、時刻依存の挙動を回避して単体テストが可能です。
- OrderManager の send_order はクラッシュ安全性を考慮して 2 段階の永続化（OrderSent 保存 → broker 呼び出し → broker_order_id 保存 → OrderAccepted）を採用しています。
- Reconciler は起動時の自動復旧を担当し、OrderSent の状態から broker 側の状態を照合して同期します。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンス情報や貢献ガイドラインはリポジトリのトップにある LICENSE / CONTRIBUTING 等を参照してください（存在する場合）。

以上が README の要点です。必要ならば各コマンドの具体的な実行例（環境変数のエクスポート例や systemd / サービス化例）や、requirements.txt の推奨内容を追加で作成できます。どの部分を詳しく書き足しましょうか？