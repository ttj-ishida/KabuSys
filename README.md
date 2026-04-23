# KabuSys README

注意: この README はコードベース（src/kabusys 以下）に基づいて作成しています。実行時の実際の依存関係や配布パッケージはプロジェクトの packaging / requirements を確認してください。

プロジェクト概要
- KabuSys は日本株向けの自動売買フレームワーク（プロトタイプ）です。
- シグナルを DuckDB から読み取り、ブローカー API（実装例: kabuステーション）へ発注する ExecutionEngine、監視用の SystemMonitor、再起動時のリコンシリエーション機能、環境設定ウィザード等を提供します。
- 開発/ペーパートレード/本番（live）を区別する設計で、paper_trading / development では MockBrokerClient による完全分離テストが可能です。

主な機能
- 環境設定ウィザード（.env の初期作成/更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の不足や不整合を起動前に検出）:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)
- 実行エンジン（ExecutionEngine）:
  - シグナル読み取り → Gate1/2 リスクチェック → 発注 → push ドレイン等の一連処理
  - paper_trading では MockBrokerClient を使用し data/paper_trading.db に分離して記録
- 監視ループ（SystemMonitor）: python -m kabusys.run_monitoring
- ブローカー抽象化層（BrokerAPIProtocol）とファクトリ（create_broker_api）
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabuステーション REST API 実装）
- 注文の状態管理（OrderRecord）と永続化（SQLite を用いた OrderRepository）
- 起動時リコンシリエーション（Reconciler）: OrderSent 状態の注文照合とポジション差分検出
- リスク管理（RiskManager）: Gate1（余力・重複・ポジション上限）、Gate2（レート制限・サーキットブレーカー）、Gate3（ドローダウン監視）
- データ系ユーティリティ（マーケットカレンダー管理、ニュース収集など）

必要となる主な環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意／設定することが多い:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
  - KABU_API_BASE_URL (kabu station API)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (本番でのアラートに必要)
  - KILL_FLAG_CLEAR_ON_START (0/1、デフォルト 0)
- .env の自動読み込み:
  - 自動読み込み順序: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env はプロジェクトルートに配置（.git / pyproject.toml を基にプロジェクトルートを自動検出します）

セットアップ手順（開発用）
1. リポジトリをクローンしてプロジェクトルートへ移動
   - git clone ...
   - cd <project_root>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 実行に必要な主なパッケージ（例）:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML (validate_config が YAML 中身を検証する場合)
     - defusedxml (news_collector)
   - 例:
     - pip install duckdb httpx websocket-client PyYAML defusedxml
   - 実際の requirements.txt がある場合はそれを使用してください:
     - pip install -r requirements.txt

4. .env を作成する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - ウィザードで生成した .env は Git にコミットしないこと（README にも留意）。

基本的な使い方
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
  - 出力: INFO / WARNING / ERROR を表示。ERROR があれば exit code 1。--strict 指定で WARNING も exit code 1。

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup
  - ウィザードで入力完了後、.env に保存されます（保存時に確認が入ります）。
  - ウィザードの最後に validate_config を実行して検証することが推奨されます。

- ExecutionEngine を起動（本番相当のワークフロー）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient が使用されます（本番向け KabuStationClient は未実装の箇所があります）。
  - ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を書き、停止は data/stop_requested.flag の作成で行うことが想定されています。
  - paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）へ記録され、本番の monitoring DB とは分離されます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視 DB は settings.sqlite_path（デフォルト data/monitoring.db）を使用（Monitoring は環境にかかわらず本番 sqlite_path を使用）

- ライブラリとして利用
  - 設定アクセス:
    - from kabusys.config import settings
    - settings.jquants_refresh_token, settings.duckdb_path などのプロパティで環境変数を取得（未設定時は ValueError を送出するプロパティもあります）
  - ブローカーファクトリ:
    - from kabusys.execution import create_broker_api
    - create_broker_api(mock=True, fill_mode="instant") など

注意点 / 実行時の振る舞い
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基に行われます。テストや CI で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config は PyYAML がインストールされていれば config/*.yaml のパース検証を行い、未インストールの場合は警告を出します。
- run_execution / run_monitoring は stop フラグ（data/stop_requested.flag）や kill.flag 等のファイルベースフラグを使って停止制御を行います。KILL_FLAG_CLEAR_ON_START=1 は起動時に kill.flag を自動クリアする挙動を許可します（本番では 0 推奨）。
- ExecutionEngine の発注フローはクラッシュ安全性を考慮した 2 相永続化の設計（OrderSent の永続化→ブローカー呼び出し→broker_order_id 保存→OrderAccepted）を採っています。
- KabuStationClient は httpx（同期）を使った実装で、WebSocket は websocket-client を用いて接続します。API のトークン管理は内部で処理します。
- MockBrokerClient は単体テストやローカル検証での振る舞いを模擬可能です（fill_mode: instant/partial/never/reject）。

ディレクトリ構成（主要ファイルと概要）
- src/kabusys/
  - __init__.py — パッケージ宣言、__version__
  - config.py — 設定管理（.env 自動読み込み、Settings クラス）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前設定検証 CLI（.env と config/*.yaml）
  - run_execution.py — ExecutionEngine 起動スクリプト（メイン実行フロー）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py — execution パッケージの公開 API
    - broker_api.py — BrokerAPIProtocol、データモデル、例外、create_broker_api
    - broker_factory.py — Settings に基づくブローカー生成ファクトリ
    - kabu_client.py — KabuStationClient（kabuステーション REST 実装）
    - mock_client.py — MockBrokerClient（開発・テスト用）
    - order_record.py — OrderRecord / OrderState（状態遷移ロジック）
    - order_repository.py — SQLite ベースの永続化層
    - order_manager.py — Order 管理（作成・送信・同期・キャンセル）
    - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン・kill）
    - reconciler.py — 起動時リコンシリエーション（OrderSent 照合、ポジション差分）
    - risk_manager.py — RiskManager（Gate1~3）
  - data/
    - calendar_management.py — マーケットカレンダー管理、営業日判定、カレンダー更新ジョブ
    - news_collector.py — RSS ニュース収集 / 前処理（defusedxml 等利用）
    - (jquants_client 等、データ取得クライアントは別ファイルに格納されている想定)
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化・ログ関連（参照されているが本 README のコード断片には一部のみ）
    - system_monitor.py — SystemMonitor 実装（参照あり）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ
  - その他: scripts/generate_config.py（config/*.yaml の生成ヘルパ等がある想定）

よくある操作例
- 新規環境の設定を作る:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
- ペーパートレードで Execution を試す:
  - 環境変数: KABUSYS_ENV=paper_trading を設定（.env に保存）
  - python -m kabusys.run_execution
- 監視ループを短い間隔で動かす（デバッグ）:
  - MONITOR_POLL_INTERVAL=5 python -m kabusys.run_monitoring

トラブルシューティングのヒント
- validate_config でエラーが出たら、該当メッセージに従って .env を修正してください。--strict を使うと WARNING も失敗扱いになります。
- .env の自動ロードが期待通り動かない場合は、プロジェクトルートが .git または pyproject.toml で検出されるか確認し、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境変数を読み込んでください。
- 実際の本番ブローカー（kabuステーション）連携はネットワーク・権限・kabuアプリの起動が必要です。最初は MockBrokerClient で動作確認することを推奨します。

ライセンス・貢献
- この README はコード内容の要約です。実際のライセンスや貢献ガイドはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上。必要であれば README をプロジェクトの実際の setup.py / pyproject.toml / requirements.txt を参照して具体的なインストール手順や依存関係の正確なリストに合わせて調整します。