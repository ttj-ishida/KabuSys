# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測できる機能追加・仕様・修正点をもとに作成しています。

## [Unreleased]

- 今後のリリースで追加予定の変更点や既知の改善点をここに記載します。

## [0.1.0] - 2026-04-23

初回リリース — KabuSys の基礎機能を実装しました。主な追加点・挙動は以下のとおりです。

### Added
- 環境設定・読み込み
  - .env 自動読み込み機能を実装（優先順: OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装。以下に対応:
    - export KEY=val 形式、
    - シングル／ダブルクォートで囲まれた値（バックスラッシュエスケープを考慮）、
    - クォートなしの値でのインラインコメント（直前がスペース/タブの場合にコメントと認識）。
  - _load_env_file による上書き制御（override）および OS 環境変数を保護する protected オプションを実装。

- 設定 API
  - Settings クラスで各種設定値をプロパティとして提供（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、閾値など）。
  - 環境変数の検証を実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。不正値時は ValueError を送出。
  - paper_trading 向け DB（PAPER_TRADING_SQLITE_PATH）や kill flag 関連フラグの扱いを明確化。

- 対話式設定ウィザード
  - python -m kabusys.config_setup による .env 作成/更新ウィザードを実装。
  - デフォルト・選択肢・シークレット表示（マスク）・説明文を備えた対話式プロンプト。
  - .env のテンプレート出力機能（.env に保存する際の注意コメントを含む）。保存後に validate_config を推奨。

- 設定検証 CLI
  - python -m kabusys.validate_config を実装。必須環境変数の未設定チェック、プレースホルダの警告、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの存在確認、config/*.yaml の存在・YAML パース検証（PyYAML が無ければスキップ）を実行。
  - --strict モードで警告も FAIL（exit 1）扱いにできる。

- 実行用スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを実装。paper_trading の場合は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用。

- 発注・注文管理
  - OrderRecord: 注文状態の列挙型と状態遷移ロジック（状態遷移テーブル + InvalidStateTransitionError）を実装。updated_at は UTC で自動更新。
  - OrderManager: create/send/sync/cancel の高レベル API を実装。DuplicateOrderError 判定（signal_id による重複検出）、送信フローはクラッシュに強い二相的永続化を導入（OrderSent 状態を DB に残す等）。
    - OrderSentPendingError の取り扱い（注文番号は保存するが状態は Sent のまま残る）。
    - send_order のエラー種別ごとの振る舞い（Rejected, pending, 例外記録など）。
  - sync_order: broker 側ステータスに基づく同期処理（部分約定の増分反映、OrderSent→Filled/Partial の場合は OrderAccepted を経由して遷移）。
  - cancel_order: キャンセル不可状態の判定（Filled を含む終端状態はキャンセル不可）と broker cancel 呼び出し。

- ExecutionEngine（発注エンジン）
  - シグナル読み込み（DuckDB）→ Gate1/2 のリスクチェック → 発注 → position_entries への記録（買いは次営業日を fill_date とする）という一連処理を実装。
  - Gate2 のレート制御（リトライ最大3回）および Circuit Breaker 発動時の挙動。
  - 発注に伴う監視DBへのイベント記録（latency 等）統合ポイントを追加（MonitoringDB が提供されれば記録する）。
  - push（kabu push）ドレイン処理: broker_order_id をキーに同期を実行、ポートフォリオ評価に基づく Gate3（ドローダウン）チェックおよび必要時の kill_switch 発動。
  - kill_switch 実装: 全 active 注文をキャンセルしループを停止。外部からは stop() として呼び出せる。
  - WebSocket ワーカスレッド: broker が stream_push を持たない場合はスキップ。

- Broker クライアント（kabu）
  - KabuStationClient 実装:
    - API トークン取得（遅延初期化）と 401 時のトークン再取得＋リトライ。
    - レスポンス JSON パースエラーハンドリング、HTTP ステータス（401/429/5xx）に対する例外分類（BrokerAPIError / RateLimitError 等）。
    - kabu の注文状態コードを内部ステータスにマッピング。
  - httpx による同期実装（将来の async への切替を想定）。

- DB・監視
  - duckdb と sqlite3 を併用（分析用に DuckDB、監視/履歴に SQLite）。
  - monitoring_db の初期化ユーティリティ（init_monitoring_db）呼び出しを実行起動時に組み込み。

- ユーティリティ
  - process_priority 設定（起動時に "high" 設定を実行）。
  - ロギングセットアップの呼び出し（app_name 指定）。

### Changed
- プロジェクトルート検出ロジック: __file__ を基点に上位ディレクトリを探索し .git または pyproject.toml を検出する方式を採用（CWD に依存しない）。
- .env 読み込みポリシーを明示（.env と .env.local の上書きルール）。

### Fixed / Notes
- ExecutionEngine の起動時に kill.flag が既に存在する場合の扱い: KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動（警告を出す）、それ以外は起動拒否して SystemExit(1)。
- run_monitoring の MONITOR_POLL_INTERVAL は 0 以下や不正な文字列を検出するとデフォルト（60秒）にフォールバックし、ログに警告を出す（time.sleep に渡すと ValueError になることを回避）。
- config/*.yaml の検証は PyYAML がある場合に限りパース検証を行い、見つからないファイルは警告メッセージで生成方法（python scripts/generate_config.py）を案内。
- OrderRepository 側の UNIQUE 制約による部分的な重複検出（signal_id の部分ユニークインデックス違反）を DuplicateOrderError に変換してハンドリング。

### Security
- .env は絶対に Git にコミットしないことを .env テンプレートに明記。

---

注: 上記はソースコードの実装内容から推測して記載した CHANGELOG です。実際のコミット履歴や設計ドキュメントに基づくものではないため、細部（メッセージ文言や動作の逸脱）がある可能性があります。必要があれば、実際の変更点に合わせて調整します。