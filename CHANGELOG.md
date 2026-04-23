# Keep a Changelog
すべての重要な変更履歴をここに記載します。  
このファイルは Keep a Changelog の規約に準拠しています。

フォーマット:
- "Added", "Changed", "Fixed", "Deprecated", "Removed", "Security" セクションを可能な限り使用しています。

## [Unreleased]
（次回リリースに含める変更をここに記載）

## [0.1.0] - 2026-04-23
初回公開リリース。

### Added
- 全体
  - プロジェクト初期版を公開。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。

- 設定 / 起動支援
  - Settings クラス（src/kabusys/config.py）
    - 環境変数からアプリケーション設定を一元取得する API を提供（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、閾値等）。
    - 自動的にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込み（CWD 非依存）。読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 設定値の簡易バリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等で不正値検出時は ValueError を送出）。
    - 本番・ペーパートレード用の DB パス分離（paper_trading 時は paper_sqlite_path を使用）。
  - 環境設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話的に .env を初期作成・更新するウィザードを追加。
    - シークレット項目は表示時にマスク（****）。
    - 選択肢・デフォルト値・説明付きの入力プロンプトを提供。キャンセルや中断に対応。
    - .env の読み書き（既存値の再利用、書式保持、README 的ヘッダを出力）。
    - デフォルト設定項目一覧（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。

  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env および config/*.yaml の設定不備を起動前に検出する CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）とプレースホルダ検出（末尾が "_here" または "your_value"）。
    - KABUSYS_ENV 値チェック（development, paper_trading, live のみ有効）。live 時は注意喚起の警告を出力。
    - LOG_LEVEL 値チェック。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在チェックと PyYAML があればパース検証（PyYAML 未インストール時は検証をスキップして警告）。
    - live 環境向け追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定の警告）。
    - 出力：INFO/WARNING/ERROR を列挙。--strict オプションで警告も FAIL (exit 1) 扱い。

  - 実行スクリプト
    - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
      - ExecutionEngine を起動するエントリポイントを提供。起動前にプロセス優先度を高く設定。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite を使用して本番 DB と分離。
      - stop_requested.flag の検出で起動を抑止・実行中の停止を制御。
    - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
      - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは本番 DB を想定）。
      - 起動時にプロセス優先度を高く設定。停止フラグによる終了処理、例外時の再試行ログ等を実装。

  - Execution コンポーネント（src/kabusys/execution/*）
    - ExecutionEngine（execution_engine.py）
      - Signal Queue プル型の発注エンジンを実装。シグナル処理時間帯（デフォルト 8:50-9:10）と市場クローズ（15:30）に基づくセッション制御。
      - WebSocket push ドレインループを持ち、push を受け取って注文同期や Gate 3（ドローダウン監視）を評価。
      - kill.flag の検査と KILL_FLAG_CLEAR_ON_START による起動時クリア動作の実装。PID ファイル書き込み/削除を行う。
      - 発注フローにおける Gate 1（シグナルレベル） / Gate 2（エグゼキューションレベル、レート制限） / Gate 3（ポートフォリオメトリクス）を組み合わせたリスク制御。
      - 発注時の再試行 / レート制限ロジック、発注遅延（latency）を監視DBへ記録するフックポイント。
      - position_entries テーブルへのエントリ記録（買いは新規エントリ、売りは売却日時更新）を実装。
    - OrderRecord（order_record.py）
      - 注文状態を表す状態機械（OrderState enum）と遷移検証を提供。InvalidStateTransitionError を用いた不正遷移検出。
      - created/ sent / accepted / partial / filled / closed / cancelled / rejected の状態モデル。
      - 状態遷移時に updated_at を UTC で更新し、オプションフィールド（broker_order_id, filled_qty, avg_fill_price, error_message）を安全に更新。
    - OrderManager（order_manager.py）
      - OrderRecord と OrderRepository を組み合わせた外向き API を実装（create_order, send_order, sync_order, cancel_order）。
      - create_order: signal_id に対してアクティブ注文の重複をチェックして DuplicateOrderError を送出する。
      - send_order: 「OrderSent を先に永続化」→ ブローカー API 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移、という2相永続化を実装してクラッシュ耐性を確保。
      - OrderRejectedError / OrderSentPendingError の扱いを明確化。OrderSentPendingError の場合は broker_order_id を永続化したまま例外を再送出。
      - sync_order: broker 側の状態を取得してローカル状態へ同期。部分約定などで filled_qty / avg_fill_price が変化した場合は更新する。
      - cancel_order: 終端状態やキャンセル不可能な状態のチェック、broker API 呼び出し、Cancelled への遷移を実装。

    - KabuStationClient（kabu_client.py）
      - kabuステーション REST API 実装（同期 httpx.Client を使用）。
      - トークン取得（遅延初期化）、401 発生時のトークン再取得→1回リトライを実装。
      - レスポンス JSON パース失敗、タイムアウト、ネットワークエラーを適切に BrokerAPIError 等へ変換。
      - HTTP 429 を RateLimitError にマッピング。サーバーエラー（5xx）は BrokerAPIError にマッピング。
      - WebSocket push（別モジュールの stream_push に依存）による通知受信を想定。

  - モニタリング・DB 初期化
    - monitoring_db 初期化フック（init_monitoring_db）を run_monitoring/run_execution から呼び出し、監視テーブルが存在することを保証。

### Changed
- なし（初回リリースのため該当なし）

### Fixed
- なし（初回リリースのため該当なし）

### Deprecated
- なし

### Removed
- なし

### Security
- なし（初回リリースのため該当なし）

---

補足:
- PyYAML がインストールされていない環境でも動作するよう、validate_config は YAML パース検証をスキップして警告を出す振る舞いとしています。
- .env 読み込みは OS 環境変数を保護する仕組み（既存 OS 環境変数を上書きしない / .env.local は上書きで読み込む）が含まれます。
- Execution/Monitoring の起動には外部依存（duckdb, sqlite3, httpx, websocket など）が必要です。検証ツールやウィザードで事前チェックを行って下さい。