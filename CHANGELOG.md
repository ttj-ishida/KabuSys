CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) のガイドラインに準拠して記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-22
-------------------

Added
- 初回リリースとして KabuSys コードベースを追加。
- 環境設定 / 検証関連
  - Settings クラスを追加し、環境変数から各種設定を取得可能に（J-Quants / kabu API / LINE / DB / システム設定等）。
  - 自動 .env 読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順序および挙動を明確化（OS 環境変数は保護され、.env.local は上書き可能）。
  - .env パーサを強化: export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い改善。
  - Settings のプロパティにより環境値の検証を実施（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。不正値は ValueError を送出。
  - settings インスタンスをモジュールロード時に提供。

- 設定ウィザード / 検証 CLI
  - 対話式ウィザード (kabusys.config_setup) を追加。.env の初期作成・更新を支援。
  - ウィザードは既存値の読み取り、シークレットマスク、選択肢表示、保存確認をサポート。
  - .env を安全なテンプレート形式で出力（コミット禁止の注意文を含む）。
  - 設定検証 CLI (kabusys.validate_config) を追加。`.env` と config/*.yaml の基本的な整合性チェックを提供。
  - validate_config は必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パーサが存在する場合は config/*.yaml のパースチェック、KABUSYS_ENV=live 時の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実施。
  - validate CLI に --strict オプションを追加。警告を FAIL として exit(1) で終了させることが可能。

- 実行スクリプト
  - run_execution スクリプトを追加。ExecutionEngine を起動し、プロセス優先度設定、PID ファイル管理、SQLite/DuckDB 接続、paper_trading 時の DB 分離（paper 用 SQLite を使用）を実装。
  - run_monitoring スクリプトを追加。SystemMonitor のポーリングループを提供。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する点を明確化。
  - 両スクリプトとも停止フラグファイル（data/stop_requested.flag）の検知で安全にシャットダウンする実装。

- Execution / 発注ロジック
  - ExecutionEngine を実装。シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）のセッション制御、WebSocket スレッド、PID ファイル、kill.flag の起動時チェック（KILL_FLAG_CLEAR_ON_START による自動クリアオプション）などをサポート。
  - シグナル処理ループでは以下のフローを実装:
    - size_multiplier の適用（BUY のみ、100株単位に切り捨て）
    - Gate 1（シグナルレベル検査）と Gate 2（エグゼキューションレベル検査、レート制限とリトライ / サーキットブレーカー処理）
    - 発注フロー（OrderManager 経由）：Order レコード生成 → 送信 → 成功/保留/拒否のハンドリング
    - 発注後に position_entries への書き込み（BUY/pending/SELL の扱いなど）
    - 監視 DB へのトレードイベント記録（監視 DB が提供されている場合）
  - push イベント処理での Gate 3（ドローダウン監視）を実装。Gate 3 NG の場合に kill_switch を発動して全 active 注文をキャンセル。

- 注文管理 / 状態遷移
  - OrderRecord データモデルと状態遷移ロジックを追加（OrderState 列挙体 + 許可遷移表）。
  - transition_to による遷移検証と updated_at の自動更新。InvalidStateTransitionError を導入。
  - OrderManager を実装。create_order（同一 signal_id の重複検出）、send_order（クラッシュ安全性を意識した 2 相永続化: OrderSent を先にコミット→broker 呼び出し→broker_order_id 保存→OrderAccepted へ遷移）、sync_order（broker 側ステータス取得と同期）、cancel_order（キャンセル可能性チェックと API 呼び出し）を提供。
  - send_order での特別例外ハンドリング：
    - OrderRejectedError → Rejected に遷移
    - OrderSentPendingError → broker_order_id を保存して OrderSent のまま残す（Reconciliation 対象として再スロー）

- ブローカー API クライアント
  - KabuStationClient を実装（httpx を使用する同期クライアント）。
  - トークン取得の遅延初期化・自動再取得を実装（401 時に再取得してリトライ）。
  - HTTP エラーコードに対する例外分類（401, 429(rate limit), 5xx→BrokerAPIError / RateLimitError）。
  - レスポンス JSON パース失敗を BrokerAPIError に変換。
  - WebSocket push の受取（stream_push）を想定した設計（存在しない場合は警告しスキップ）。

- 監視・DB 初期化
  - monitoring_db 初期化ヘルパー呼び出しを run_monitoring / run_execution に追加して監視テーブルの存在を保証。
  - DuckDB/SQLite 接続の作成・クローズを適切に管理。

Changed
- 設定読み込み/パース挙動を明示化（.env の引用符・コメント処理、export 形式対応）。
- デフォルト値の明確化:
  - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - LOG_LEVEL: INFO
  - PAPER_FILL_MODE デフォルト: instant（認証・検証ロジックを追加）

Fixed
- DB パスの親ディレクトリが存在しない場合は警告するようにし、起動時にディレクトリ自動作成される可能性を案内（validate_config と run スクリプトの整合性向上）。
- ExecutionEngine の起動時に kill.flag が存在するケースを明確に扱い、KILL_FLAG_CLEAR_ON_START により自動クリアできるようにした（誤起動防止）。
- send_order におけるクラッシュ耐性の強化（broker_order_id を先に永続化することで Reconciliation が状態回復できる設計）。

Security
- .env の自動生成テンプレートに「絶対に Git にコミットしないこと」を明記し、シークレットはウィザード表示でマスク。
- .env ロード処理で OS 環境変数を保護する mechanism を導入（.env.local の上書き時も OS 環境変数は上書きされない）。

Notes / Implementation details
- 本リリースは初期実装のため、OrderRepository / BrokerAPI の詳細な実装や外部接続の疎通検証は別モジュール/テストで補完されることを想定しています。
- YAML 内容検証は PyYAML がインストールされている場合のみ行われ、未インストール時は警告してスキップします。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB を想定）。
- ExecutionEngine の時刻ベースのセッション（signal_send_start/end, market_close）やポーリングの間隔は EngineConfig および環境変数で調整可能。

今後の予定（提案）
- Broker API / OrderRepository のユニットテスト、統合テストの整備。
- 非同期化（httpx.AsyncClient への移行）や WebSocket の堅牢化。
- より詳細な監視イベントとアラート統合（LINE 通知のテンプレート等）。
- リコンシリエーション結果を可視化する管理ツール。

---