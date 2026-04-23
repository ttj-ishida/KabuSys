# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します（https://keepachangelog.com/ja/）。

## [Unreleased]

## [0.1.0] - 2026-04-23

### Added
- 初回リリース。日本株自動売買フレームワーク「KabuSys」の基本機能を追加。
- 環境設定・管理
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パース機能を実装（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
  - Settings クラスを提供し、環境変数経由で各種設定値を安全に取得（必須項目は取得時に例外を送出）。
  - デフォルト値と妥当性チェックを導入（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 対話式設定ウィザード
  - config_setup CLI を追加（python -m kabusys.config_setup）。
  - 対話形式で .env の作成・更新を支援。シークレット値はマスク表示。
  - 設定候補（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークンなど）を定義し .env を出力。
  - .env ファイル出力テンプレートには注意書き（Git にコミットしない）を含む。

- 設定検証ツール
  - validate_config CLI を追加（python -m kabusys.validate_config）。
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定チェック、プレースホルダ判定、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実施。
  - config/*.yaml の存在確認と（PyYAML がインストールされている場合の）パース検証を実装。PyYAML 未導入時は警告でスキップ。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定確認や KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict オプションで警告を FAIL (exit 1) 扱いにできる。

- 実行・監視プロセス起動スクリプト
  - run_execution: ExecutionEngine の起動スクリプトを追加（プロセス優先度設定、PID ファイル、停止フラグ検出、paper_trading 用 DB の分離など）。
  - run_monitoring: SystemMonitor のポーリングループを追加（MONITOR_POLL_INTERVAL で間隔調整、監視は常に本番 sqlite_path を使用）。

- 発注エンジンと関連コンポーネント
  - ExecutionEngine を実装（シグナル処理ウィンドウ、WebSocket push ドレイン、セッションライフサイクル管理）。
  - EngineConfig によるセッション時刻（発注開始/終了、マーケット終了）制御。
  - kill_switch の実装により全 active 注文のキャンセルとループ停止を行う安全機構を提供。
  - WebSocket(push) を受けての _push_queue 処理機能を追加。stream_push が未実装の broker はスキップしログ出力。

- 注文状態管理（ドメインモデル）
  - OrderRecord と OrderState（状態列挙）を実装。許可遷移テーブルを定義し、不正遷移で InvalidStateTransitionError を送出。
  - データベースに触れない純粋な状態遷移ロジックを提供。

- OrderManager（外向き API）
  - create_order, send_order, sync_order, cancel_order の一連フローを実装。
  - DuplicateOrderError の判定（既存 active 注文検出、SQLite の部分ユニークインデックス違反を変換）を実装。
  - send_order はクラッシュ安全性を考慮した 2 段階永続化を採用（OrderSent を DB に保存してから broker 呼び出し、broker_order_id を先にコミットしてから OrderAccepted に遷移）。
  - OrderSentPendingError / OrderRejectedError など broker 側エラーに対する挙動を定義。
  - sync_order は broker 側ステータス照会で部分約定進行や状態遷移を同期。部分更新（filled_qty / avg_fill_price）を適切に反映。
  - cancel_order はキャンセル不可能な状態の拒否ロジックと broker cancel 呼び出しを実装。

- Broker 抽象と kabu station クライアント
  - BrokerAPIProtocol（インターフェース）は別モジュールで想定。
  - KabuStationClient を実装（同期 httpx を使用）。トークン取得の遅延初期化、自動再取得、401 リトライ、429 を RateLimitError として扱う、HTTP/ネットワーク例外を BrokerAPIError にラップ。
  - REST と併せて WebSocket の stream_push をサポートする設計（存在する場合にのみ利用）。
  - レスポンスの JSON パース失敗を明示的に扱う。

- 監視周り
  - monitoring DB 初期化関数を起動前に実行するユーティリティを利用（init_monitoring_db）。
  - 発注イベントの監視DB記録（latency 等）を行うフックを ExecutionEngine に追加（監視DB書き込み失敗は警告に留める設計）。

- リスク管理統合
  - RiskManager を利用した Gate チェックを実装（Gate1: シグナル、Gate2: 実行レート制限、Gate3: ポートフォリオ指標によるドローダウン監視 → kill_switch）。
  - Rate-limit のリトライループ（最大3回）や Circuit Breaker 発生時のループ停止挙動を定義。

- データベース接続
  - sqlite3（監視用）および duckdb（分析用）接続を使用。paper_trading では専用 SQLite（PAPER_TRADING_SQLITE_PATH）を用い、本番 DB と分離。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env は絶対にリポジトリへコミットしない旨をテンプレートに明記。
- シークレット値は config_setup の表示時にマスク。

### Notes / 注意事項
- config/*.yaml のパース検証は PyYAML (yaml) がインストールされている場合のみ行われます。未導入時は警告を出してスキップします。
- 環境変数のプレースホルダ（例: 値が your_value や *_here で終わる）は validate_config で警告されます。
- ExecutionEngine はセッション中に PID ファイルを書き、起動時に既存の kill.flag の有無をチェックします。KILL_FLAG_CLEAR_ON_START=1 の場合は既存の kill.flag をクリアして起動します（本番では 0 を推奨）。
- PAPER_FILL_MODE の無効値指定は Settings で ValueError を発生させます（有効値: "instant", "partial", "never", "reject"）。
- LOG_LEVEL / KABUSYS_ENV の妥当性チェックは Settings および validate_config の双方で行われる（validate_config は警告かエラーで報告、Settings は不正値で例外送出）。

今後の予定（例）
- BrokerAPIProtocol の具体実装（MockBrokerClient 等）の追加・テスト強化。
- 非同期（async）対応の検討（httpx.AsyncClient への移行可能設計）。
- 監視・リコンシリエーション機構の堅牢化とより詳細なメトリクス収集。