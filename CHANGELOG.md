# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に従います。  

変更の重大度はソースコードから推測して記載しています。実際のリリースノート作成時は必要に応じて調整してください。

## [Unreleased]

（現時点のコードベースでは未リリースの変更はありません）

## [0.1.0] - 2026-04-23

初回公開リリース。KabuSys の基本的な設定管理、実行エンジン、発注フロー、監視周りの実装を含みます。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 環境変数 / 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 必須変数取得用の _require()（未設定時は ValueError を送出）。
    - Paper Trading 用の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）。
    - 各種パス（duckdb / sqlite / pid / kill flag 等）を Path 型で提供。
    - env/log_level の検証ロジック（許容値チェック）。

  - .env ファイルパーサーの実装（クォートやエスケープ、コメントの処理に対応）。

- 環境設定ウィザード CLI
  - config_setup.py に対話式ウィザードを実装。
    - .env の初期作成・更新を対話式で支援。
    - シークレット項目はマスク表示、選択肢/デフォルト表示対応。
    - 書き込み用ヘッダとデフォルト値を含む .env 出力機能を実装。
    - 保存確認プロンプト、キャンセル時の振る舞いを実装。
    - .env に関する注意（Git にコミットしない等）を出力。

- 設定検証 CLI
  - validate_config.py に設定検証ツールを実装。
    - 必須・任意の環境変数チェック、プレースホルダ値検出（例: ending "_here", "your_value"）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検査（許容値チェック）。
    - DB パスの親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - --strict モードで警告も FAIL として exit(1) を返すオプション。
    - 結果を INFO/WARNING/ERROR に分類して出力。

- 実行/監視ランナー
  - run_execution.py: ExecutionEngine の立ち上げスクリプトを追加。
    - paper_trading 環境では専用 SQLite（paper_trading.db）を使用し、本番 DB と分離。
    - stop_requested.flag による起動/実行停止をサポート。
    - PID ファイル書き出し。
    - プロセス優先度設定（High）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。

- 実行エンジン本体
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（signal_send_start/ end 時間帯）と WebSocket push ドレイン処理を分離。
    - 発注フローにおける複数の Gate（Gate1: シグナルレベル、Gate2: 実行レート制御、Gate3: ポートフォリオ監視）を実装。
    - kill_flag 検査と KILL_FLAG_CLEAR_ON_START の挙動を実装。
    - PID ファイル管理、WebSocket スレッド（broker が stream_push を持つ場合）起動。
    - DuckDB からシグナル読み込み（_read_signals）を実装。

- 発注関連コンポーネント
  - OrderRecord（状態マシン／データモデル）を実装（src/kabusys/execution/order_record.py）。
    - 明確な OrderState 列挙（created/sent/accepted/partial/filled/closed/cancelled/rejected）。
    - 許容遷移マップ定義と transition_to による遷移検証（不正遷移は InvalidStateTransitionError）。
    - updated_at 自動更新、オプションフィールド（broker_order_id / filled_qty / avg_fill_price / error_message）更新に対応。

  - OrderRepository（SQLite 絡みの実装はファイル内参照）と組み合わせる OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id に対する重複検査（DB の部分ユニーク制約違反を DuplicateOrderError に変換）。
    - send_order: クラッシュ安全性を考えた扱い（OrderSent を事前に永続化 → broker 呼び出し → broker_order_id を先に永続化 → OrderAccepted へ移行）。
      - OrderSentPendingError の扱い（broker_order_id を永続化して OrderSent のまま残す）。
    - sync_order: broker.get_order_status による状態同期と partial→partial の数量/価格更新。
    - cancel_order: 終端状態のキャンセル禁止チェック、必要に応じて broker.cancel_order を呼ぶ。

  - Reconciler（参照あり）を用いた起動時リコンシリエーションを ExecutionEngine に統合。

  - RiskManager と連携する Gate チェック、API レート記録のフックを実装（RiskRejectReason 等を利用）。

- broker 実装（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST クライアント。
    - トークン取得の遅延初期化と自動再取得（401 の際に再取得して 1 回リトライ）。
    - レスポンス JSON のパースエラーハンドリングを BrokerAPIError に変換。
    - 429（レート制限）や 5xx を適切にエラー化。
    - websocket push 受信用の stream_push サポート（存在する場合に ExecutionEngine が使用）。

- 監視 DB / ロギング / ユーティリティ
  - monitoring_db 初期化フック（init_monitoring_db）の利用を run_monitoring/run_execution に統合。
  - ロギング設定とプロセス優先度設定ユーティリティを利用（setup_logging, set_process_priority）。
  - 監視 DB へのトレードイベントログ投入フックを ExecutionEngine の発注処理に追加（monitoring_db が渡された場合）。

### Changed
- 設計上の決定（ドキュメント化）
  - 発注の永続化戦略を明確化（クラッシュ耐性を考慮した 2 フェーズ的コミット設計）。
  - paper_trading 環境では本番監視 DB とは分離した SQLite を使用する設計を採用。
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用するという方針を明記。

### Fixed
- .env 読み込みの堅牢化
  - export prefix、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど多数のパターンに対応。

- MONITOR_POLL_INTERVAL の値検証追加
  - 0 以下や不正な文字列がセットされた場合にデフォルトにフォールバックし適切に警告を出すよう修正。

### Security / Notes
- .env ファイルは絶対に Git にコミットしない旨をウィザード出力に明記。
- KABUSYS_ENV=live の場合は本番向けの注意喚起を validate_config で警告し、LINE 通知設定等が未設定だと通知されないことを警告。
- KILL_FLAG_CLEAR_ON_START のデフォルトは 0（本番推奨）。live で 1 が設定されていると警告が出る。

### Breaking Changes / Migration notes
- Settings クラスの各プロパティ（env, log_level, PAPER_FILL_MODE 等）は不正値時に ValueError を投げるようになっています。上位で例外処理を行うか validate_config を事前に実行してください。
- .env の自動読み込みは既定で有効。テストや特殊環境で自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

このリリースはコードベースの解析から推測して作成した初期の変更履歴です。実際のコミット履歴やリリースポリシーに合わせて調整してください。