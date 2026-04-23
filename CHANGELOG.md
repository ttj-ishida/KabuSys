# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - initial release

### 追加 (Added)
- CLI: 環境設定ウィザード `kabusys.config_setup` を追加。
  - 対話式で .env ファイルの初期作成・更新を支援。
  - シークレット入力（マスク表示）、選択肢、デフォルト値、任意項目のサポート。
  - `--env-file` オプションで保存先パスを指定可能。
  - .env ファイル生成時のヘッダ、Git にコミットしない旨の注意文を自動出力。

- CLI: 設定検証ツール `kabusys.validate_config` を追加。
  - .env と config/*.yaml の存在・基本的検証を実行。
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
  - KABUSYS_ENV / LOG_LEVEL の値検証、DB パス親ディレクトリ存在確認、PyYAML の未インストール時のスキップと警告。
  - `--strict` モードを追加（警告も失敗扱いで exit(1)）。

- 設定管理モジュール `kabusys.config` を追加。
  - .env 自動ロード機構（プロジェクトルート検出: .git または pyproject.toml）を実装。
  - 優先順位: OS 環境変数 > .env.local > .env。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを抑制可能。
  - .env の堅牢なパーサーを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等）。
  - `Settings` クラスで各種設定値プロパティを提供（パス、トークン、LINE 設定、閾値、env/log_level 検証など）。
  - Paper Trading 向けの `paper_sqlite_path`、`paper_fill_mode`（バリデーションあり）をサポート。

- 実行用スクリプトを追加:
  - `kabusys.run_execution`:
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出、DB 初期化（監視テーブルの冪等初期化）、DuckDB/SQLite 接続、paper_trading 時の DB 分離に対応。
  - `kabusys.run_monitoring`:
    - SystemMonitor のポーリングループを起動。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。

- 実行系コア:
  - `ExecutionEngine` を追加:
    - シグナル処理（8:50–9:10）と push ドレインループ（9:10–15:30）を管理するセッション実行ロジック。
    - WebSocket push の受信を別スレッドで行い、内部キューに投入して処理。
    - kill_flag の扱い（起動時のクリア挙動、KILL_FLAG_CLEAR_ON_START に対応）、PID ファイル管理、再結合（Reconciliation）フック。
    - シグナル毎の Gate チェック（Gate1: シグナルレベル、Gate2: 実行レート制限、Gate3: ドローダウン監視）とリスク連携。
    - 発注遅延計測・監視 DB へのイベント記録（可能な場合）。
    - size_multiplier の適用（BUY のみ、最小単位の切り捨て）。

  - `OrderRecord` / `OrderState`:
    - 注文状態を表す状態機械（enum）と状態遷移チェックを実装。
    - 不正遷移は `InvalidStateTransitionError` を送出。

  - `OrderManager`:
    - 注文作成（冪等キー: UUID）・重複検出（同一 signal_id の active 注文）処理。
    - send_order の二相的永続化戦略を実装（OrderSent を先に永続化し broker 呼び出しへ、broker_order_id を先に保存することで crash 耐性を向上）。
    - OrderRejected / OrderSentPending 等の細かな結果ハンドリング。
    - sync_order で broker 側のステータス照合および部分約定の更新（filled_qty / avg_fill_price）。
    - cancel_order はキャンセル不能状態のチェックと broker 側キャンセル呼び出し。

  - Broker クライアント: `KabuStationClient`
    - kabu station REST API 用クライアント実装（httpx 同期クライアントを使用）。
    - トークンの遅延取得と 401 に対するリトライ処理を実装。
    - レスポンス JSON パースエラー / タイムアウト / ネットワークエラー時に適切な例外に変換。
    - kabu の状態コードを内部状態（open/partial/filled/cancelled/rejected 等）へマッピング。
    - HTTP 429 を RateLimitError として扱う。

- 監視関連:
  - 監視 DB 初期化関数 `init_monitoring_db` の利用箇所を整備（Execution/Monitoring の起動で確実にテーブルを準備）。
  - Monitoring 用の SQLite は環境にかかわらず本番 sqlite_path を使用する設計を明記。

- ユーティリティ:
  - process_priority 設定ユーティリティの呼び出しを起動パスで導入（monitoring/execution 起動時に High 優先度へ）。
  - ロギングセットアップユーティリティの利用。

- パッケージメタ:
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

### 変更 (Changed)
- .env 読み込みの優先順位と保護ロジックを導入。
  - OS 環境変数を保護（上書き防止）したうえで `.env.local` は override=True（OS 以外は上書き）でロード。
- send_order の永続化フローを改善し、クラッシュ時の整合性を向上。
  - broker_order_id を先に保存することで後続の再照合（Reconciliation）で回復可能になる設計。
- sync_order の遷移ロジックを堅牢化。
  - OrderSent → Filled/PartialFill へ直接遷移できない場合は一旦 OrderAccepted を経由して同期する（ネットワーク障害後の復旧対応）。
- ExecutionEngine 内の例外ハンドリングを強化して長時間稼働時の安定性を向上（Reconciliation/monitoring 書き込み失敗等でセッションを継続する挙動）。
- run_monitoring と run_execution の挙動を明確化（停止フラグ検知、リソースクリーンアップ、接続クローズの保証）。

### 修正 (Fixed)
- .env のパースでのクォート・エスケープ・コメント処理を改善し、実運用でのフォーマット差異に対応。
- config/*.yaml のパースエラー検出を導入（PyYAML 未インストール時には検証をスキップして警告）。
- MONITOR_POLL_INTERVAL の不正値（0 以下など）で time.sleep に渡して例外になる問題を防止し、デフォルトにフォールバックする安全機構を追加。
- PID ファイル書き込み / 削除で残留する可能性に対する保護（起動時に kill.flag を検査し、KILL_FLAG_CLEAR_ON_START に応じてクリアするか起動拒否）。

### 注意 / ドキュメント (Notes)
- .env は絶対に Git にコミットしないことを .env 生成ヘッダで明記。
- 本番環境（KABUSYS_ENV=live）での起動時は LINE 通知設定の未設定や KILL_FLAG_CLEAR_ON_START=1 の危険性について明示的に警告する仕組みを追加。
- Paper Trading は本番 DB と分離される設計（paper_sqlite_path を利用）。設定ウィザードで paper_trading を選択して運用可能。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートやバージョニング方針と差異がある場合は、必要に応じて調整してください。