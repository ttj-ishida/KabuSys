# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog のガイドラインに準拠しています。  

## [Unreleased]

### Added
- ドキュメント化されていないユーティリティ / テスト用フラグ
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env 読み込みの無効化機能を追加（テストでの環境隔離に利用可能）。
- 複数の内部 API/インターフェイスの安定化（将来的なバージョンでの拡張に備えた準備）。

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-23

初回リリース。本リリースでは自動売買システム KabuSys のコア設定・実行・監視周りの基本機能を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - Settings クラスを実装し、環境変数経由でシステム設定を取得可能に。
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - .env 読み込み時の優先順位: OS 環境変数 > .env.local > .env。
  - .env のパース処理の充実：
    - export プレフィックス対応、
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - 行内コメントの扱い（非クォート値での注釈扱い）などに対応。
  - 必須環境変数取得時に未設定なら ValueError を投げる `_require()` を提供。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装し、.env の初期作成・更新を支援。
  - ウィザードはシークレット項目のマスク表示、選択肢やデフォルト提示、途中キャンセル対応を実装。
  - `.env` を生成する `_write_env()` を用意し、生成時のヘッダや注意書きを出力。

- 設定検証 CLI
  - `kabusys.validate_config` により、起動前に環境変数や config/*.yaml の存在・妥当性を検証する CLI を実装。
  - 検証は errors / warnings / infos を集計して出力。`--strict` モードで警告も失敗扱いにできる。
  - PyYAML 未インストール時には YAML 検証をスキップし警告を出す。

- 実行・監視スクリプト
  - `run_execution.py`：ExecutionEngine を起動するエントリポイントを実装。
    - paper_trading 環境時には paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（stop_requested.flag）検知を行う。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きに対応。
    - 監視は実行環境にかかわらず本番 sqlite_path を使用する旨を実装。

- 実行エンジン（ExecutionEngine）
  - シグナル取得→Gate1/Gate2 を通した発注ループ、WebSocket push のドレインループ、セッション管理（時刻ベース）を実装。
  - kill.flag の検査と KILL_FLAG_CLEAR_ON_START による起動時自動クリアオプションを実装。
  - PID ファイル管理（作成/削除）を実装。
  - WebSocket push を受け取るワーカースレッドをサポート（broker が stream_push を実装している場合）。
  - position_entries への書き込み（約定記録）実装。失敗しても発注フローを継続するように安全化。
  - 発注に関する監視 DB へのイベント記録機能（MonitoringDB が提供される場合）。

- 注文状態管理
  - `OrderRecord`（状態遷移ロジックを含む純粋モデル）を実装。
  - OrderState 列挙と許容遷移マップを定義。InvalidStateTransitionError を導入。
  - transition_to により updated_at を自動更新し、オプションで broker_order_id / filled_qty / avg_fill_price / error_message を更新可能。

- OrderManager（外向き API）
  - シグナルから注文生成、送信、同期（sync）、キャンセル処理を実装。
  - create_order で signal_id に対する同一アクティブ注文の重複検出（DuplicateOrderError）を実装。DB の UNIQUE 制約違反からの変換も実装。
  - send_order はクラッシュ耐性を考慮した2相永続化:
    1. OrderSent に遷移してコミット（送信前）
    2. broker へ送信 → broker_order_id を DB に先に保存（state は Sent のまま）
    3. OrderAccepted へ遷移してコミット
    - OrderRejectedError / OrderSentPendingError の特別ハンドリング実装。
  - sync_order による broker 側ステータスとの同期間合処理を実装（部分約定時のフィールド更新含む）。
  - cancel_order は終端状態チェック（キャンセル不可の状態）を行い、必要なら broker cancel API を呼んでから状態を Cancelled に遷移。

- Broker クライアント（kabu station）
  - `KabuStationClient` を実装（httpx を使用した同期クライアント）。
  - トークン取得の遅延初期化、401 時の再取得・1回リトライを実装。
  - レスポンスの JSON パースエラー・ネットワークエラー・タイムアウトを BrokerAPIError に変換。
  - 429（レート制限）を RateLimitError として扱う。
  - 内部で kabu station のステータスコード -> 内部ステータス文字列マッピングを提供。

- リスク管理 / リコンシリエーション
  - ExecutionEngine 側で Gate1（シグナル検査）/ Gate2（実行レート制限・サーキットブレーカー）/ Gate3（ポートフォリオメトリクス）を参照するロジックを実装。
  - サーキットブレーカ発動時の処理（Gate2 で CB OPEN → シグナルループ停止）を実装。
  - リコンシリエーション（Reconciler）を起動時に呼び出し、同期結果をログ出力する仕組みを実装（Reconciler 実装は別モジュール）。

- 監視側初期化
  - monitoring 用 SQLite の初期化関数 init_monitoring_db を使用してテーブルの存在を保証。

- その他ユーティリティ
  - 環境に依存しないプロジェクトルートの検出、パスの展開、親ディレクトリ存在チェック等のユーティリティを追加。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- .env ファイル生成時に「.env を絶対に Git にコミットしないこと」旨の注意書きを追加（ベストプラクティスの明示）。

---

注意:
- 本 CHANGELOG はコードベースから推測して作成した初期リリースノートです。実際の変更履歴やリリースノートとして公開する際は、コミットログやリリースプロセスに基づいて適宜修正してください。