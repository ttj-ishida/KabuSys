Keep a Changelog
=================

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは Keep a Changelog に準拠しています。
要点: 変更はバージョン単位で分け、"Added", "Changed", "Fixed" 等で分類します。

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-23
-----------------

Added
- 初回リリース: KabuSys の基本機能を実装
  - package メタ情報
    - パッケージバージョンを `__version__ = "0.1.0"` として導入。
  - 設定管理（src/kabusys/config.py）
    - 環境変数・.env ファイルの自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env の読み取り時に `export KEY=val` 形式、クォートされた値（バックスラッシュエスケープ対応）、インラインコメントの取り扱いをサポートするパーサを実装。
    - `Settings` クラスを導入し、各種設定値（J-Quants トークン、kabu API パスワード、DB パス、PID / kill flag パス、しきい値、env/log level 等）をプロパティとして提供。値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODEなど）を行い、不正値時は ValueError を送出。
    - Paper Trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）と paper_fill_mode のバリデーションを実装。
  - 環境設定ウィザード（src/kabusys/config_setup.py）
    - 対話式 CLI による .env の初期作成 / 更新ウィザードを実装。
    - 対話プロンプトは既存 .env の読み込み・再利用、選択肢、デフォルト、シークレット表示（マスク）に対応。
    - .env を安全に書き出す `_write_env()` を実装し、ファイル生成時の注意コメントを付与（.env を Git にコミットしない注意喚起）。
  - 設定検証ツール（src/kabusys/validate_config.py）
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を実装。
    - 必須/任意環境変数リストを定義し、未設定やプレースホルダ（末尾が "_here" や "your_value"）の警告を表示。
    - KABUSYS_ENV / LOG_LEVEL の値チェック、DB パスの親ディレクトリ存在チェック（存在しない場合は警告）を実装。
    - config/*.yaml の存在確認と、PyYAML がインストールされている場合はパース検証を実行（PyYAML 未インストール時はスキップして警告）。
    - `--strict` オプションにより警告も失敗（exit 1）として扱うモードを実装。
    - 本番環境（KABUSYS_ENV=live）での追加安全チェック（LINE 設定、KILL_FLAG_CLEAR_ON_START 等）を実装。
  - 実行エントリスクリプト
    - run_execution（src/kabusys/run_execution.py）
      - ExecutionEngine の起動スクリプトを実装。プロセス優先度設定、PID ファイル管理、stop フラグ検知、SQLite / DuckDB の接続処理を含む。
      - Paper Trading 環境では paper_trading 用の SQLite DB を使用して本番 DB と隔離。
    - run_monitoring（src/kabusys/run_monitoring.py）
      - SystemMonitor のポーリングループ起動スクリプトを実装。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明記。
  - Execution / 発注フロー
    - ExecutionEngine（src/kabusys/execution/execution_engine.py）
      - シグナル処理（8:50–9:10）と push ドレインループ（9:10–15:30）に基づくセッション実行ロジックを実装。
      - WebSocket push のワーカースレッド、_push_queue による非同期通知処理を実装。
      - シグナル読み込みは DuckDB から行い、size_multiplier や発注単位（100株単位）等の前処理を実施。
      - Gate 1（シグナルレベル）、Gate 2（エグゼキューションレベル、レート制限とリトライ）、Gate 3（ドローダウン監視: kill switch 発動）を設計・組み込み。
      - kill_switch による全 active 注文のキャンセル、停止イベントの管理、PID 書き出しとクリーンアップを実装。
      - Reconciler の実行（起動時）に対応。モニタリングDBへ発注イベントの記録を行うフックを提供。
    - OrderRecord / OrderManager（src/kabusys/execution/order_record.py, order_manager.py）
      - OrderRecord: 注文状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許容遷移表を定義。遷移検証と updated_at 自動更新を実装。
      - OrderManager: create/send/sync/cancel の外向き API を実装。クラッシュ安全性を考慮した永続化シーケンス（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移等）を導入。OrderRejected/OrderSentPending などのケースを扱う。
      - DuplicateOrderError の導入（同一 signal_id の active 注文が存在する場合に検出）。
      - sync_order は broker の状態を照合して部分約定の進行や状態遷移を反映。キャンセル不可状態の判定と cancel_order 実装。
  - Broker クライアント
    - KabuStationClient（src/kabusys/execution/kabu_client.py）
      - kabu station REST API 用クライアントを実装（同期 httpx を使用）。
      - トークン取得（遅延初期化）、401 時の自動再取得と再試行、429（レート制限）や 5xx の扱い、JSON パース失敗のエラー変換等を実装。
      - kabu の内部状態コード → 内部ステータスへのマッピングを定義。
  - 監視 DB 初期化フック（init_monitoring_db）や process_priority / logging_setup 等のユーティリティを利用する設計（外部モジュールを呼び出す形で統合）。

Changed
- （該当なし／初回リリースのため履歴なし）

Fixed
- .env パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの判定を正しく処理することで、.env ファイルのさまざまな記法に対応。

Security
- .env ファイルに関する注意喚起
  - config_setup による .env 生成時に「.env は絶対に Git にコミットしないこと」というメッセージをファイルヘッダに記載。

Notes / 補足
- YAML パース検証は PyYAML に依存。PyYAML が未インストールの場合は validate_config が YAML 内容検証をスキップして警告する挙動になっています。
- 実運用（本番）では KABUSYS_ENV=live に設定した際の追加チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定確認）に注意してください。KILL_FLAG_CLEAR_ON_START=1 は本番で危険となるため警告が出ます。
- ExecutionEngine は WebSocket push を持たない broker の場合に WebSocket スレッドをスキップする旨の警告を出す設計です。

今後の予定（例）
- Reconciler / broker 関連のテストケース強化
- async 対応（httpx.AsyncClient へ移行）
- YAML スキーマ検証の導入（PyYAML + スキーマ）