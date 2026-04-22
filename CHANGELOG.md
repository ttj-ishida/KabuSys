# Changelog

全ての重要な変更点を記録します。本ファイルは Keep a Changelog のスタイルに準拠します。

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョン: パッケージの __version__ は 0.1.0 に設定されています。

## [Unreleased]

（今後の変更をここに記載）

## [0.1.0] - 2026-04-22

初回リリース（コードベースから推測して記載）。

### Added
- パッケージ初期実装:
  - kabusys パッケージの基本モジュールを追加。
  - バージョン: `__version__ = "0.1.0"`。

- 環境 / 設定関連:
  - config モジュール（src/kabusys/config.py）
    - .env ファイルの自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env の行パースは export プレフィックス・クォート・エスケープ・インラインコメントに対応した堅牢な実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 必須環境変数取得用のヘルパー `_require()` を提供（未設定時は ValueError）。
    - Settings クラスで各種設定値を型付きプロパティとして提供（トークン・DB パス・PID ファイル・閾値など）。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。不正値は ValueError。
    - デフォルト値:
      - KABU_API_BASE_URL: http://localhost:18080/kabusapi
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
      - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
      - PID_FILE_PATH: data/execution.pid
      - KILL_FLAG_PATH: data/kill.flag

  - config_setup CLI（src/kabusys/config_setup.py）
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目のマスク表示、選択肢・デフォルトサポート。
    - .env 読み書きロジック（既存値の維持、フォーマット済み書き出し）。
    - CLI オプション: `--env-file` で保存先を指定可能。

  - validate_config CLI（src/kabusys/validate_config.py）
    - 起動前に .env と config/*.yaml の設定不備を検出。
    - 検出内容を INFO/WARNING/ERROR に分類して出力。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV, LOG_LEVEL の妥当性チェック。`live` 環境では追加警告（LINE 設定、Kill Flag 設定等）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）について親ディレクトリ存在チェック。
    - PyYAML があれば config/*.yaml をパースして検証、未インストール時は検証をスキップする柔軟性。
    - CLI オプション: `--strict`（警告も FAIL として exit(1) で終了）。

- 実行スクリプト / ランナー:
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - プロセス優先度を High に設定（utils.process_priority 経由）。
    - stop フラグ検出に基づく安全な起動・停止処理。
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用。

- 発注 / 実行エンジン関連（execution パッケージの主要機能）:
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態を列挙した状態遷移モデル（OrderState enum）。
    - 許可遷移テーブルおよび transition_to による遷移検証。
    - DB に触れない純粋なビジネスロジック実装。InvalidStateTransitionError を定義。
  - OrderRepository（参照のみ、実装は別ファイル）を用いた OrderManager（src/kabusys/execution/order_manager.py）
    - create_order: signal_id 単位での部分ユニーク制約・重複検出（DuplicateOrderError）。
    - send_order: 送信前に OrderSent を永続化 → broker API 呼び出し → broker_order_id を先に永続化 → OrderAccepted へ遷移する 2 相永続化設計（クラッシュ耐性を考慮）。
    - OrderRejectedError / OrderSentPendingError などの扱いを明示。OrderSentPendingError は呼び出し元へ伝播（pending の扱い）。
    - sync_order: ブローカ API からの状態を反映し、部分約定の数量・平均価格を更新。OrderSent→Filled などの特殊ケースの回復処理をサポート。
    - cancel_order: 終端状態ではキャンセル不可（InvalidStateTransitionError）、それ以外はブローカーへ cancel を実行し Cancelled に遷移。
    - 内部で _CANCEL_INELIGIBLE_STATES を定義し、Filled をキャンセル不可能に含める等の設計判断を反映。

  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル（DuckDB）を読み込み、Gate1/2（signal / execution レベルのリスクチェック）を通して発注。
    - size_multiplier の適用（BUY のみ）と 100 株単位での切り捨て。
    - Gate 2 のレート制限は最大3回のリトライ、サーキットブレーカー検出でループ停止。
    - 発注後に position_entries を更新（約定日は翌営業日へ）し、発注成功・pending に応じて処理。
    - WebSocket push ドレイン処理: push ペイロードを受け、broker_order_id から client_order_id を突き合わせて sync を実行。
    - Gate 3（ドローダウン監視）で NG の場合は kill_switch を発動して全 active 注文をキャンセル。
    - kill.flag の扱い:
      - 起動時に存在 → KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動、それ以外は起動拒否。
      - kill_switch は全 active 注文をキャンセルし、ループを停止。
    - PID ファイル書き出し / 削除の処理。
    - run_session で 8:50 のシグナル処理開始、9:10 発注締切、15:30 セッション終了というスケジュール。

  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx（同期）を用いた kabu station REST API クライアント実装。
    - トークン取得ロジック（遅延初期化・401 時の再取得）を内蔵。
    - HTTP エラーやタイムアウト、429 に対する専用例外（RateLimitError 等）を適切に変換。
    - websocket（push）受信のための stream_push を想定した設計（有れば ExecutionEngine が利用）。

- リスク管理・リコンサイル・監視系の統合:
  - Reconciler, RiskManager, MonitoringDB 等の呼び出しポイントを実装（各実体は別ファイル）。
  - 監視DB初期化用 init_monitoring_db の呼び出しを run_execution/run_monitoring で実施。

### Changed
- 初回リリースのため該当なし（初期追加）。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数ファイル（.env）に関して、「絶対に Git にコミットしないこと」を README 相当の注意書きとして .env 書き出しヘッダーに明記。

---

注記（コードから推測して記載しています）
- 実装の一部（例えば OrderRepository の詳細実装、監視・リスクの具体ロジック、broker API の具象クライアントやテスト用モック等）は別ファイルに存在する想定です。本 CHANGELOG は提供されたソース群の内容から主要な追加点・設計意図を要約したものです。