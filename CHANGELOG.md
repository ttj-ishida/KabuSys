CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-22
-------------------

Added
- 基本リリース: パッケージ初版 (バージョン 0.1.0) を追加。
- 環境設定 / 読み込み
  - .env ファイルおよび環境変数を扱う機能を提供する設定モジュールを追加。
  - .env 自動読み込み:
    - プロジェクトルート（.git または pyproject.toml を基準）を探索し、ルートが見つかれば .env を読み込み、.env.local があれば .env.local によって上書きする（OS 環境変数は保護され上書きされない）。
    - 自動ロードを無効化するために環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用可能。
  - .env パーサーを強化:
    - export KEY=... 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープに対応して値を正しく解釈。
    - クォート無し行での inline コメント判定を改良（'#' の直前が空白/タブの場合のみコメント扱い）。
- 設定オブジェクト
  - Settings クラスを導入し、プロパティ経由で設定にアクセス可能（例: settings.jquants_refresh_token, settings.sqlite_path 等）。
  - 各種プロパティにデフォルト値とバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - DB パスは Path 型で返却し expanduser を行う。
  - Paper Trading (KABUSYS_ENV=paper_trading) 向けに paper_sqlite_path を提供し、本番 DB と分離できる。
  - kill flag 関連設定（KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）や監視閾値（CPU/MEM/DISK）などを追加。
- 対話式 .env ウィザード
  - kabusys.config_setup モジュールで .env の初期生成・更新を支援する対話式ウィザードを追加。
  - シークレット入力のマスク表示、選択肢・説明付きプロンプト、保存前の確認機能を提供。
  - 保存フォーマットには注意喚起コメントを含め、.env を Git にコミットしない旨を明記。
- 設定検証 CLI
  - kabusys.validate_config により起動前に環境変数や config/*.yaml の存在・簡易整合性をチェックする CLI を追加。
  - --strict オプションを追加（警告も失敗扱いにして exit(1)）。
  - PyYAML が存在する場合は config/*.yaml をパースして内容チェックを行う（未インストール時はスキップし警告出力）。
  - 本番環境 (KABUSYS_ENV=live) 向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START=1 の警告）を追加。
- 実行系スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - 起動時にプロセス優先度を上げ、PID ファイルを書き込み、stop フラグ検知で安全停止。
    - Paper Trading モードでは専用 SQLite (paper_trading.db) を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する動作で実装。
- 注文管理 / 発注エンジン
  - OrderRecord / OrderState: 注文状態遷移を表すステートマシンを実装。
    - 許容される遷移テーブルを定義し、transition_to() で遷移検証と updated_at 自動更新を行う。
    - 不正な遷移は InvalidStateTransitionError を raise。
  - OrderManager: DB（OrderRepository）と broker API を組み合わせた発注ワークフローを実装。
    - create_order: signal_id に対する重複注文の検出（DuplicateOrderError）。
    - send_order: クラッシュ安全性を考慮した 2 相永続化のワークフロー（OrderSent を先に保存 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移等）。
      - OrderRejectedError / OrderSentPendingError の取り扱いを明確化。
    - sync_order: broker 側ステータス照合を行い filled_qty / avg_fill_price の差分更新や状態遷移を行う。
    - cancel_order: 終端状態ではキャンセル不可として例外を返す。broker 側キャンセルを呼び出し、Cancelled に遷移。
  - ExecutionEngine: Signal Queue ベースの発注エンジンを実装。
    - シグナル処理（8:50–9:10）と WebSocket push ドレイン（9:10–15:30）を区別した処理フロー。
    - Gate 1（シグナル単位のチェック）、Gate 2（実行時のレート制限等）および Gate 3（ポートフォリオ指標監視による kill switch）を実装。
    - size_multiplier 適用（BUY のみ、100 株刻みで切り捨て）。
    - 発注成功/保留/失敗に応じて監視 DB へイベント記録（monitoring_db が提供されている場合）。
    - push 通知処理で broker_order_id から同期を試行し、ポジション評価で Gate 3 をチェック。
    - kill_switch(): 全 active 注文のキャンセルとループ停止を行う公開 API を提供（stop() はエイリアス）。
- ブローカークライアント
  - KabuStationClient を追加（kabu ステーション REST API 実装）。
    - httpx を用いた同期 HTTP クライアント。
    - トークン取得の遅延初期化と 401 時の再取得リトライ実装。
    - HTTP ステータス 429 を RateLimitError にマッピング、500 系は BrokerAPIError として扱う。
    - kabu ステーションの注文状態コードを内部ステータス ("open"/"partial"/"filled"/"cancelled"/"rejected") にマップ。
    - websocket（push）受信用の stream_push を呼び出す仕組みを想定（on_message コールバックを受け取る設計）。
- データベース / 監視
  - monitoring_db の初期化関数 init_monitoring_db を利用して起動時に監視テーブルの存在を保証。
  - DuckDB および SQLite の接続を各実行スクリプト内で確立し、適切にクローズする実装。

Changed
- validate_config: 各チェック項目を整理。環境変数がプレースホルダ（例: endswith "_here" や "your_value"）の場合に警告を出すようにした。
- config_setup: 対話式の対話文言や既存値のマスク表示を整備。

Fixed
- .env パーサーの改善により、引用符内のエスケープや inline コメントの誤判定など以前問題になり得るケースに対応。

Breaking Changes
- Settings の一部プロパティは不正な値を受け取った場合に ValueError を送出するようになっています:
  - KABUSYS_ENV（有効値: development / paper_trading / live）
  - LOG_LEVEL（有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL）
  - PAPER_FILL_MODE（有効値: instant / partial / never / reject）
  これらは呼び出し側で例外処理を行う必要があります。
- 自動 .env 読み込みの挙動:
  - パッケージ読み込み時にプロジェクトルートが見つかると自動で .env, .env.local を読み込みます。テストや CI 等で環境を固定したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は「環境にかかわらず」本番 sqlite_path を使用するため、監視プロセスが誤って別の DB を参照しないように注意してください。
- validate_config CLI の exit コード:
  - エラーが見つかった場合は exit(1)。
  - --strict を付けると警告も FAIL 扱いで exit(1) になる点に注意してください。

Notes / Operational guidance
- 起動時の kill.flag（KILL_FLAG_PATH）検査:
  - ExecutionEngine は起動時に kill.flag が存在すると起動を拒否します。環境変数 KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に自動でクリアして起動する動作になります（本番では 0 を推奨）。
- PID 管理:
  - ExecutionEngine は PID ファイルを書き込み、終了時に削除します。PID ファイルパスは設定により変更可能。
- クラッシュ安全性:
  - send_order のワークフローは、クラッシュや異常終了時にも再照合（Reconciliation）で復旧可能なように broker_order_id を先に永続化する等の対策が施されています。

未分類 / 今後の作業候補（このリリースには含まれないが言及）
- KabuStationClient の WebSocket 実装は stream_push を broker 側で提供することを前提にしており、実行環境側での接続安定化・再接続戦略の強化は今後の改善点です。
- テストカバレッジや E2E テストは別途拡充を推奨します（特に再起動・クラッシュ復旧シナリオ）。

[Unreleased]
- 今後のリリースで記載します。