# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトのバージョニングは SemVer に従います。

## [Unreleased]

## [0.1.0] - 2026-04-23

### Added
- 初回公開: KabuSys 自動売買フレームワークのコア実装を追加。
- CLI / ユーティリティ
  - `kabusys.config_setup`:
    - .env ファイルを対話式に作成・更新するウィザードを実装。
    - 各種設定項目 (KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* など) を定義し、説明付きで入力を促す機能を提供。
    - .env の読み取り・書き込みロジックを実装（既存値の再利用、シークレットのマスク表示、確認プロンプト）。
  - `kabusys.validate_config`:
    - 起動前に .env および config/*.yaml の設定不備を検出する検証ツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値検証、DB パス親ディレクトリ存在チェック、PyYAML があれば YAML パース検証、KABUSYS_ENV=live 用の追加ガードを提供。
    - `--strict` オプションで警告を失敗扱いにする機能を追加。
  - `run_execution.py`, `run_monitoring.py`:
    - ExecutionEngine / SystemMonitor の起動スクリプトを追加。環境変数や PID/stop フラグに基づき安全に起動・停止する。
    - `MONITOR_POLL_INTERVAL` による監視ポーリング間隔上書きをサポート（デフォルト 60 秒）。
- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数から設定値を取得する一元化インターフェースを提供（パスは Path オブジェクトで返却）。
  - 自動 .env ロード機構を実装（読み込み優先度: OS 環境変数 > .env.local > .env）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサーの強化: export 形式の対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの扱い等に対応。
  - PAPER_FILL_MODE（paper_trading 用のフィルモード）等のバリデーションを実装。
- 発注・注文管理
  - `execution.OrderRecord`:
    - 注文状態列挙（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）と遷移ルールを実装。遷移検証で不正遷移は例外を発生。
  - `execution.OrderManager`:
    - signal_id 単位での重複検出（DuplicateOrderError）。
    - create/send/sync/cancel のフロー実装。永続化と broker API 呼び出しの順序やクラッシュ安全性（2 相永続化など）を考慮した設計。
    - OrderSentPendingError などのケースを扱い、Reconciliation を容易にする振る舞いを実装。
  - `execution.execution_engine.ExecutionEngine`:
    - Signal Queue ベースの発注エンジン実装。シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）の二段構成。
    - Gate 1/2（シグナル・実行レベル）および Gate 3（ドローダウン監視）を導入し、リスク管理に基づく kill_switch 発動ロジックを実装。
    - WebSocket push 処理用のスレッドとキュー、push による同期（sync_order）処理を実装。
    - PID ファイル書き込み、kill.flag 検査、起動時のリコンシリエーション呼び出しなど運用上の安全策を実装。
- ブローカー/API クライアント
  - `execution.kabu_client.KabuStationClient`:
    - kabu ステーション REST API クライアントを httpx 同期クライアントで実装。トークン取得の遅延初期化、401 時の自動トークン再取得とリトライ、HTTP レスポンスのエラーマッピング（RateLimitError, BrokerAPIError）を提供。
    - WebSocket push（stream_push）との連携部分を想定した設計。
- データベース / 監視
  - DuckDB と SQLite を用途別に使い分け（分析用 DuckDB、監視/履歴用 SQLite）。
  - Paper trading 時は専用 SQLite（data/paper_trading.db）を使うことで本番 DB と分離。
  - 監視 DB 初期化処理（init_monitoring_db）を起動時に呼び出す仕組みを追加。
- その他ユーティリティ
  - ロギングセットアップ、プロセス優先度設定ユーティリティを利用して起動時に適切な初期化を行う。

### Changed
- なし（初回リリースのため差分なし）。

### Fixed
- なし（初回リリース）。

### Notes / 補足
- config/*.yaml の検証は PyYAML がインストールされている場合のみ実施されます。未インストール時は警告を出してスキップします。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。配布後やテスト実行時の影響を避けるため、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ExecutionEngine の時間帯（発注開始/終了、マーケットクローズ）は EngineConfig でカスタマイズ可能で、テストでは内部メソッドを直接呼ぶことで時間依存性を回避できます。

## Deprecated
- なし

## Removed
- なし

## Security
- なし

---  

（注）この CHANGELOG は提供されたコードベースから仕様・振る舞いを推測して作成しています。実際のリリースノートとして利用する場合は、リリース日や詳細説明、影響範囲をプロジェクトの実際の履歴に合わせて調整してください。