CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測した変更点を記載したもので、実際の履歴は開発リポジトリのコミットログを参照してください。

Unreleased
----------

- なし

[0.1.0] - 2026-04-22
--------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基本機能を実装。
- 環境設定 / 管理
  - Settings クラスを導入し、環境変数経由で各種設定へアクセス可能に（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH 等）。
  - .env 自動読み込み機能を実装（探索はパッケージファイル位置から .git または pyproject.toml を起点にプロジェクトルートを特定）。読み込み優先順位は OS 環境変数 > .env.local > .env。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルのパース強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い、無効行のスキップなど。
  - .env の読み書きユーティリティ（対話式ウィザード）を実装（python -m kabusys.config_setup）。対話式で .env を生成・更新し、secret 値はマスク表示。生成される .env にはコミット禁止の注意書きを含むテンプレートを出力。
- 設定検証 CLI
  - validate_config CLI を実装（python -m kabusys.validate_config）。.env と config/*.yaml の基本的な設定不備を起動前に検出。
  - 必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、YAML パーサ（PyYAML）が無い場合はパーススキップと警告、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認）を実装。
  - --strict オプションで警告も FAIL として扱う（exit code 1）。
- 実行・監視プロセス起動スクリプト
  - run_execution（ExecutionEngine 起動）を実装（python -m kabusys.run_execution）。Paper Trading 環境では専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring（SystemMonitor ポーリング）を実装（python -m kabusys.run_monitoring）。MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
  - 停止制御: data/stop_requested.flag（監視・実行の外部停止フラグ）と kill.flag（kill switch）を検知し安全にシャットダウンする挙動を実装。PID ファイル書き込み・削除処理を含む。
  - プロセス優先度設定ユーティリティを起動時に呼び出し（優先度を "high" に設定）。
- ExecutionEngine（発注エンジン）
  - Signal Queue Pull 型の ExecutionEngine を実装。セッションスケジュール（シグナル処理: 8:50–9:10、push ドレイン: 9:10–15:30）に基づく処理。
  - シグナル処理フロー: signals を DuckDB から読み込み、size_multiplier の適用、シグナル毎に Gate 1（シグナルレベル検査）→ Gate 2（エグゼキューション検査：レート制限等）を実行し、発注。発注成功時は position_entries テーブルへの書き込みを試みる。
  - WebSocket push の受信を別スレッドで行い、push をドレインして sync + Gate 3（ドローダウン監視）を実行。push による注文同期やポートフォリオ評価で Gate 3 が NG の場合は kill_switch 発動。
  - 発注関連の監視イベント（latency 等）を監視 DB にログ可能（MonitoringDB が渡された場合）。
- 注文状態管理・Order State Machine
  - OrderRecord データモデルと状態遷移ロジックを実装。Allowed transitions を厳密に定義し、不正遷移時は InvalidStateTransitionError を送出。
  - OrderManager により signal_id による重複検出（DuplicateOrderError）、2相永続化（OrderSent 状態を永続化してから broker 呼び出し、その後 broker_order_id を永続化→Accepted へ遷移）や OrderSentPendingError 取り扱い、sync_order による broker 状態との同期、キャンセル処理の実装。
  - 一貫性を保つための SQLite トランザクション/例外処理を含む（例: signal_id 部分ユニークインデックス違反を DuplicateOrderError に変換）。
- Broker API / KabuStation クライアント
  - KabuStationClient（kabu station REST API 実装）を追加。httpx を使った同期クライアント。トークン取得の遅延初期化と 401 時の再取得・リトライ、429 レート制限検出、サーバーエラー処理を行う。
  - WebSocket push は websocket 経由で受信（stream_push を持つクライアントに依存）。
  - kabu ステータスコード → 内部ステータスマッピングを実装（open/partial/filled/cancelled/rejected 等）。
- リスク管理、Reconciler、OrderRepository 等の主要コンポーネントの統合
  - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を組み立てる基本フローを整備。
  - RiskManager による Gate 判定（Signal / Execution / Metrics）の呼び出し箇所を実装。Circuit breaker の検出でシグナルループ停止を想定。
- DB 初期化・Monitoring
  - monitoring_db.init_monitoring_db 呼び出しを通じて監視用 SQLite DB の初期化を保証（冪等）。
  - DuckDB と SQLite の両方を利用する設計。デフォルトパスは data/kabusys.duckdb, data/monitoring.db。
- その他ユーティリティ
  - ロギングセットアップユーティリティの呼び出しによるログ初期化。
  - 一部ユーティリティで環境変数の妥当性チェックを実装（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の妥当性検査とエラーメッセージ）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- .env を生成するテンプレートに「絶対に Git にコミットしないこと」という注意を明記（config_setup にて）。機密情報（トークン・パスワード）は対話画面でマスクして表示。

Notes / Implementation details
- validate_config は PyYAML がインストールされていない場合は YAML 内容検証をスキップし、その旨を警告する実装になっています。
- ExecutionEngine のセッション中、kill.flag の扱い: KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に kill.flag を自動クリアするオプションあり（ただし本番では 0 を推奨）。
- OrderManager.send_order はクラッシュ安全性のために broker_order_id を先に永続化する 2 相永続化パターンを採用しており、Reconciler による照合で状態回復可能な設計。
- 設定値検証は Settings のプロパティ内でも厳密に行われ、無効値時は ValueError を送出する（起動時に fail-fast を意図）。

今後の予定（推測）
- 単体テストの追加（OrderRecord / OrderManager / ExecutionEngine 等）。
- 非同期 (async) 版 broker client（httpx.AsyncClient）への切替検討。
- YAML 設定ファイルのより詳細なスキーマ検証の実装（PyYAML + スキーマ利用）。
- ドキュメント・運用手順の充実（デプロイ手順、監視設定、復旧手順等）。

----- 
上記は提供されたソースコードの内容から推測して作成した CHANGELOG です。実際のリリースノートやコミット履歴が存在する場合はそちらを優先してください。