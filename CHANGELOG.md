# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。<https://keepachangelog.com/ja/1.0.0/>

注: 本ファイルはコードベースの内容から機能・変更点を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回公開リリース。日本株自動売買システム「KabuSys」の基本機能を実装しています。

### Added
- 環境設定 / ロード
  - Settings クラスを実装し、環境変数経由で各種設定にアクセス可能に。
  - .env 自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルパーサを実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
  - 必須環境変数取得用のヘルパー _require を実装（未設定時は ValueError を送出）。
  - 各種設定プロパティを提供（J-Quants トークン、kabu API パスワード/ベース URL、LINE トークン/ユーザ、DB パス、paper_trading 用設定、PID/Kill フラグパス、しきい値等）。

- 設定ウィザード CLI
  - config_setup CLI を実装し、対話式に .env を初期作成/更新するウィザードを提供。
  - シークレット項目は表示時にマスク。生成される .env テンプレートにはコメントと注意書きを含む。
  - 選択肢型入力・デフォルト値・オプション項目に対応。

- 設定検証 CLI
  - validate_config CLI を実装。起動前に .env と config/*.yaml の設定不備を検出。
  - 必須環境変数チェック（プレースホルダ検出含む）、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML 未インストール時はパースをスキップして警告）。
  - --strict オプションで警告を FAIL 扱い（exit code 1）にできる。

- 実行・監視ランナー
  - run_execution スクリプト: ExecutionEngine を起動するエントリポイントを提供。起動時にプロセス優先度を設定、PID ファイル書き込み、停止フラグ検知に対応。
  - run_monitoring スクリプト: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔上書き可能）。監視は環境に関係なく本番 sqlite_path を利用。

- 発注系コア実装
  - ExecutionEngine: シグナル読み込み→Gate1/2（リスク検査）→発注、WebSocket push ドレイン、Gate3（ドローダウン監視）および kill_switch を含むセッション実行ロジックを実装。
  - EngineConfig により発注・締切などのセッション時間を設定可能。
  - OrderRecord: 注文状態 (OrderState) を列挙し、allowed transitions を定義。transition_to で遷移検証とタイムスタンプ更新を行う。
  - OrderManager: create/send/sync/cancel の外向き API を実装。二相永続化（OrderSent 前後の処理）、OrderSentPendingError の取り扱い、DuplicateOrderError の判定を実装。
  - OrderRepository（参照）と組み合わせた DB 操作を前提に設計（SQLite ベース）。
  - Reconciler / MonitoringDB のフックを想定したリコンシリエーション・監視ログ連携。

- ブローカークライアント
  - KabuStationClient を実装（httpx ベース）。トークン管理（遅延取得・401 による再取得とリトライ）、レスポンス JSON パース、HTTP ステータスに応じた例外変換（RateLimitError 等）を実装。
  - WebSocket push 受信用に stream_push 想定の処理を ExecutionEngine が利用。

- データベース
  - DuckDB（分析用）と SQLite（監視/発注履歴）を併用する設計を採用。paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全分離。

- ユーティリティ統合
  - logging_setup と process_priority ユーティリティを利用してログ初期化・プロセス優先度設定を行う。
  - 監視 DB 初期化（init_monitoring_db）をランナー起動時に行う。

### Changed
- 初回リリースのため、プロジェクト構成と公開 API（Settings / ExecutionEngine / OrderManager 等）を確立。
- .env の読み込みルールと優先順位を明確化（OS 環境を保護）。

### Fixed / Robustness
- .env ファイル読み込み時のファイルアクセスエラーで警告を発するよう改善（読み込み失敗時にクラッシュさせない）。
- YAML パーサが未インストールでも validate_config が致命的にならないよう警告に留める実装。
- ExecutionEngine の発注フローでのクラッシュ耐性を考慮した永続化順序（OrderSent の前後で broker_order_id を確実に保存する設計）を採用し、リコンシリエーションでの回復を容易に。
- _get_poll_interval にて MONITOR_POLL_INTERVAL の不正値を検出し、デフォルトにフォールバックする挙動を追加。

### Security
- .env を絶対に Git へコミットしない旨の注記を config_setup の出力に明記。
- シークレット（J-Quants / Kabu API パスワード / LINE トークン等）はウィザード出力時にマスク表示。

### Notes / 既知の制限
- YAML の内容検証には PyYAML が必要。未インストール環境ではパースチェックがスキップされる（validate_config は警告する）。
- KabuStationClient は同期 httpx.Client を使用。将来的に async 対応を行う場合は httpx.AsyncClient へ差し替え可能な設計。
- 一部のエラー（BrokerAPIError 等）は設計上 send_order 内で抑止せず呼び出し元へ伝播させる想定（発注状態の診断を容易にするため）。
- 日付やセッション時間の扱いはローカルシステム時刻に依存する。必要に応じてタイムゾーン/同期の運用が推奨される。

---

今後のリリースでは以下を予定（例）:
- テストカバレッジ拡充とユニットテスト追加
- async 化・高負荷時のスケーリング対応
- 監視/アラート機能の強化（LINE 以外の通知チャネル追加）
- broker API 抽象化の強化とモッククライアントの整備

（以上）