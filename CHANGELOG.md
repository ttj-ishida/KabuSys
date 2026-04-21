# Changelog

すべての重要な変更をここに記録します。形式は「Keep a Changelog」に準拠しています。  
このファイルは、提供されたソースコードから推測できる機能追加・改善点・修正点を基に作成しています。

すべての変更は SemVer を想定しています。現在のパッケージバージョンは src/kabusys/__init__.py に基づき v0.1.0 として記載しています。

## [Unreleased]

（今後の変更や修正をここに記載）

## [0.1.0] - 初回リリース
リリース日: 未設定

### Added
- CLI / ウィザード / 検証ツールを追加
  - `kabusys.config_setup`：対話式ウィザードで .env を生成・更新する CLI（python -m kabusys.config_setup）。
    - 設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE_* など）を定義。
    - 既存 .env の読み込み・再利用をサポート。保存前の確認プロンプトを実装。
  - `kabusys.validate_config`：起動前に .env および config/*.yaml の設定不備を検出する CLI（python -m kabusys.validate_config）。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、データベースパスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - `--strict` オプションで警告も失敗（exit 1）として扱うモードを提供。

- 環境設定管理
  - `kabusys.config`：
    - .env 自動ロード（プロジェクトルートの検出は .git または pyproject.toml に基づく）。`.env` を読み込み、`.env.local` があれば上書き（OS 環境変数は保護）。
    - .env パーサーを実装（export 前置、クォート文字列、バックスラッシュエスケープ、コメント取り扱いをサポート）。
    - Settings クラスで環境変数をラップ（必須変数取得時のエラー、型変換、妥当性チェック、デフォルト値の提供）。
    - Paper trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - PAPER_FILL_MODE 等、いくつかの設定の妥当性検証を実装。

- 実行 / 監視の起動スクリプト
  - `kabusys.run_execution`：ExecutionEngine を起動するエントリポイント。
    - プロセス優先度設定、PID ファイル管理、kill flag の取り扱い、DB 接続（paper_trading 時は専用 DB）を実装。
  - `kabusys.run_monitoring`：SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。

- 実行エンジン周り（発注ロジック）
  - `ExecutionEngine`：
    - シグナル取得（DuckDB）→ Gate1（シグナルレベル）/ Gate2（実行レベル）→ 発注 → WebSocket プッシュドレイン という処理フローを実装。
    - kill_switch による安全停止と全 active 注文のキャンセル。
    - WebSocket push をバックグラウンドで受信し、同期処理（sync_order）や Gate3（ドローダウン監視）を実行。
    - 発注時の監視DBへのログ記録インテグレーション（latency_ms 等）。

- 注文管理（State Machine）
  - `execution.order_record`：
    - OrderState 列挙と状態遷移の許可表（_ALLOWED_TRANSITIONS）を実装。
    - OrderRecord データモデルと transition_to による遷移検証（不正遷移で例外を投げる）。
  - `execution.order_manager`：
    - create_order（signal_id に対する重複検知）、send_order（クラッシュ安全性を考慮した 2 段階永続化のフロー）、sync_order（broker からの状態取得に基づく同期）、cancel_order（キャンセル不可能状態のチェック）を実装。
    - DuplicateOrderError、OrderSentPendingError 等のエラー処理を実装。
    - broker 側の部分約定や pending に対する扱いを明確化。

- broker クライアント実装（kabu ステーション）
  - `execution.kabu_client`：
    - KabuStationClient を実装（httpx 同期クライアント）。
    - トークンの遅延取得（自動再取得）と 401 時のリトライ処理を実装。
    - レスポンスの JSON パース時例外変換、429 レート制限の検出（RateLimitError）、サーバーエラー時の変換を実装。
    - send_order / cancel_order / get_order_status の基本処理（レスポンスチェック、OrderRejectedError の処理、注文ステータスコード→内部ステータスへのマッピング）を含む。

- 監視 DB 初期化
  - `monitoring.monitoring_db` の init_monitoring_db を使用して起動時にテーブルが存在することを保証（冪等）。

### Changed
- .env 自動ロードロジックの明確化
  - OS 環境変数を保護して .env/.env.local を読み込む実装（既存の OS 環境を上書きしない。`.env.local` は override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途等）。

- デフォルトパスと挙動
  - DUCKDB_PATH / SQLITE_PATH のデフォルトを "data/kabusys.duckdb" / "data/monitoring.db" に設定。
  - run_monitoring は説明に従い監視が常に本番 sqlite_path を使用する点を明記。
  - run_execution は paper_trading 環境を検知して paper_sqlite_path を使用（本番 DB と完全分離）。

- 発注フローのクラッシュ安全性向上
  - send_order の実装は「OrderSent を DB に保存してから broker 呼び出し、broker_order_id を先に永続化、その後 OrderAccepted に遷移して永続化」という 2 段階の永続化を採用し、クラッシュ時の復旧（Reconciliation）を容易にする設計を採用。

### Fixed / Improved
- .env パーサー改良
  - export プレフィックス対応、シングル/ダブルクォート文字列のバックスラッシュエスケープ処理、インラインコメントの取り扱い（クォートあり/なしでの挙動差異）などを実装・改善。
  - 不正な行はスキップし、読み込み時のエラーは警告に変換して処理継続。

- 設定検証の充実
  - validate_config にて必須環境変数未設定時はエラー、プレースホルダ値（例: endswith("_here") や "your_value"）は警告を出すなど、手早く設定ミスを見つけられるようになった。
  - KABUSYS_ENV の不正値はエラー、live の場合は注意喚起の警告を追加。
  - LOG_LEVEL の妥当性チェック（無効なら警告）。
  - config/*.yaml の存在確認と、PyYAML がインストールされていれば YAML の安全なパース検証を行う（未インストール時はスキップして警告）。

- 監視ポーリング間隔の堅牢化
  - MONITOR_POLL_INTERVAL のパース時に非正値や不正入力を検出し、警告ログを出してデフォルトにフォールバックする実装。

- kill flag / PID 管理の堅牢化
  - ExecutionEngine 起動時に既存の kill.flag を検査し、KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動、それ以外は起動を拒否する挙動を実装。
  - PID ファイルは起動時に書き込み、正常終了時に削除するように管理。

### Security
- KabuStation クライアントは API トークンを内部で管理し、401 に対してトークン更新を行うことで認証エラー時の自動復旧を図る実装。
- .env ファイルの生成時に「.env を絶対に Git にコミットしないこと」と明示するテンプレートを出力。

### Known issues / Notes
- config/*.yaml の内容検証は PyYAML に依存する。PyYAML がインストールされていない環境ではパース検証はスキップされ、警告が出る。
- KabuStationClient の get_order_status のパース実装がモジュールの切り出し/表示上で途中までしか示されていない箇所が見受けられます（提供されたコードの切り取りに起因している可能性あり）。実際の実装では注文リストを走査して OrderStatus を生成・返す処理が必要です。
- 実行環境（live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）が未設定だとアラートが届かないため注意。validate_config はその旨を警告する。

---

その他の細かい設計決定や内部 API（OrderRepository や BrokerAPIProtocol、Reconciler、RiskManager など）のメソッド仕様はソース内の docstring やコメントに従ってください。必要であれば、各コンポーネントごとの詳細な変更履歴（項目別の追加・修正点）を別途作成します。