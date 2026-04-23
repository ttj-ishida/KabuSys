# Changelog

すべての重要な変更をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

## [Unreleased]
- 今後のリリースに向けた変更点はここに記載します。

## [0.1.0] - 初回リリース
リリース日: (初回公開)

概要: 日本株自動売買システム KabuSys の初回公開。環境設定と起動スクリプト、発注処理・状態管理・監視機能のコアを実装しています。

### Added
- 基本パッケージ情報
  - パッケージ名とバージョンを定義 (src/kabusys/__init__.py: __version__ = "0.1.0")。

- 環境設定・読み込み
  - .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env のパースロジックを実装。以下に対応:
    - 空行・コメント行（#）
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - クォート無しでのインラインコメント（直前が空白/タブの場合）
  - OS 環境変数の保護（既存の OS 環境変数は上書きしない / .env.local は override 可能だが protected を尊重）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。

- 設定モデル
  - Settings クラスを実装（src/kabusys/config.py）。
    - J-Quants / kabu API / LINE / DB /監視 / システム設定などのプロパティを提供。
    - 必須環境変数取得時に未設定だと ValueError を発生させる `_require` 実装。
    - PAPER_FILL_MODE のバリデーション（有効値: instant/partial/never/reject）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（有効値のチェック）。
    - path 値は Path.expanduser() を使用して展開。

- 設定ウィザード CLI
  - 対話式ウィザードで .env を生成・更新するスクリプトを実装（src/kabusys/config_setup.py）。
    - 設定項目定義とデフォルト、選択肢、説明を含む。
    - シークレット項目は表示でマスク（保存時は実値）。
    - 既存 .env の読み込みと Enter での既存値再利用。
    - .env ファイルの書式テンプレートを生成（ファイルに保存しないよう注意喚起を含む）。
    - 中断処理（EOF/KeyboardInterrupt）に対応。

- 設定検証 CLI
  - .env と config/*.yaml の起動前チェックツールを実装（src/kabusys/validate_config.py）。
    - 必須/任意の環境変数チェック、プレースホルダ値検出。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（live に関する注意喚起）。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック。
    - PyYAML があれば config/*.yaml を safe_load によるパース検証、未インストール時はスキップして警告。
    - KABUSYS_ENV=live の追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告も失敗扱いにできる。

- 実行エントリ（プロセス）
  - 実行用スクリプトを実装:
    - run_execution: ExecutionEngine を立ち上げるエントリ（src/kabusys/run_execution.py）。
      - paper_trading での DB 分離（paper_trading 用 SQLite を利用）。
      - プロセス優先度設定、停止フラグの検出、スレッドでの実行制御。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 発注エンジンと状態管理
  - OrderRecord（状態機械とデータモデル）を実装（src/kabusys/execution/order_record.py）。
    - 明確な OrderState 列挙と許可遷移テーブル。
    - transition_to による遷移検証と updated_at の自動更新。
    - 不正遷移で InvalidStateTransitionError を送出。
  - OrderManager（発注 API への公開インタフェース）を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id 単位の重複防止。DB の部分ユニーク制約違反を DuplicateOrderError に翻訳。
    - send_order: 2相永続化の実装（OrderSent を先に永続化→API呼び出し→broker_order_id を保存→OrderAccepted に遷移）によりクラッシュ時の復元性を向上。
    - OrderRejectedError / OrderSentPendingError の扱いを実装。
    - sync_order: broker 側状態取得→内部状態同期（部分約定の進展はフィールド直接更新）。
    - cancel_order: キャンセル不可能状態の判定とキャンセル処理。
  - ExecutionEngine（セッション実行ロジック）を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）の分離。
    - Gate 1/2/3 によるリスク検査フロー:
      - Gate1: シグナルレベル検査（size_multiplier の適用、BUY のみ）。
      - Gate2: エグゼキューションレベル検査（レート制限、リトライ最大3回、回路遮断時はシグナルループ停止）。
      - Gate3: ドローダウン監視（NG の場合 kill_switch 発動）。
    - kill_switch 実装: 全 active 注文のキャンセル処理、ストップイベントセット。
    - WebSocket ワーカー: broker が stream_push を提供する場合に _push_queue に入れる仕組み。
    - PID ファイル管理と kill.flag の扱い（KILL_FLAG_CLEAR_ON_START の挙動に対応）。
    - position_entries の DuckDB への記録（約定日に次の営業日を使用）。

- ブローカークライアント（kabu station）
  - KabuStationClient 実装（src/kabusys/execution/kabu_client.py）。
    - httpx.Client を用いた同期 REST 実装。
    - トークン取得の遅延初期化と 401 の際の再取得・再試行。
    - HTTP エラーハンドリング（401/429/5xx 等を専用例外に変換）。
    - WebSocket 受信用に websocket 連携（stream_push 想定）。

- 監視 DB 初期化ユーティリティおよび SystemMonitor（モジュール経由の初期化呼び出しを所持）
  - run_monitoring / run_execution から init_monitoring_db を呼ぶことで監視テーブルの冪等な初期化を行う。

- ユーティリティ
  - ログ設定・プロセス優先度設定用ユーティリティを利用する呼び出し。
  - DuckDB / SQLite 接続箇所での適切なクローズ処理。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / 注意事項
- .env は絶対に Git にコミットしないでください（config_setup の生成ヘッダに注意書きあり）。
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行われます。未インストール時は警告を表示してスキップします。
- ExecutionEngine の動作（時間帯や kill.flag の扱い）や OrderManager の 2 相永続化など、クラッシュ後の復元ロジックに依存する設計が含まれます。運用前に validate_config と config_setup による検証を推奨します。
- paper_trading モードでは SQLite と Broker の動作が本番と分離されるように設計されています（本番 DB へ書き込まないことを保証）。

---

今後のリリースでは以下を検討しています（例）:
- 非同期対応（httpx.AsyncClient に切り替え）
- より詳細な監視メトリクスとダッシュボード連携
- テストカバレッジ拡充とエンドツーエンド検証シナリオの追加