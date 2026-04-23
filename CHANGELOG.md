# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。

- 該当リポジトリの初回公開/機能実装に基づき、コードベースから推測した変更履歴を記載しています。
- 日付は本ファイル生成日: 2026-04-23

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-23

### Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
- 環境設定 / 管理
  - 自動 .env ロード機能を追加（プロジェクトルート（.git または pyproject.toml）を基準に探索）。
  - .env ファイルの読み込みロジックを実装（export 形式、引用符、エスケープ、インラインコメント対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD によって自動読み込みを無効化可能。
  - Settings クラスを実装。環境変数からアプリ設定を取得するプロパティ群（トークン類、DB パス、ログレベル、環境種別、閾値など）。
  - PAPER_FILL_MODE の検証（"instant" / "partial" / "never" / "reject"）。
- 設定ウィザード CLI
  - `kabusys.config_setup` モジュールに対話式ウィザードを実装。
  - シークレット項目はマスク表示、選択肢・デフォルト値のサポート、既存 .env 読み込みと Enter による再利用、.env へのテンプレート出力機能を提供。
  - 出力される .env にはコミットしてはいけない旨の注記を含むテンプレートを作成。
- 設定検証 CLI
  - `kabusys.validate_config` モジュールに設定検証コマンドを実装。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性判定、DB パス親ディレクトリ存在確認、config/*.yaml の存在確認と PyYAML によるパース検証（PyYAML 不在時は警告でスキップ）。
  - `--strict` フラグにより警告も失敗扱いで exit(1) とするモードを追加。
  - KABUSYS_ENV=live 時の追加ガード（LINE トークンや KILL_FLAG_CLEAR_ON_START の警告）。
- 実行コンポーネント（Execution）
  - ExecutionEngine を実装。シグナル駆動の発注ループ（シグナル処理時間帯 / push ドレインループ / セッション管理）。
  - run_execution スクリプト（PID ファイル管理、kill.flag の検査・handling、paper_trading の専用 SQLite を使用する分離）。
  - Broker クライアント工場（BrokerClientFactory を想定）を用いたブローカー抽象化。
  - WebSocket push の受信スレッド実装（push を Queue に投入してドレイン処理）。
  - 発注フローでの Gate チェック（Gate1: シグナルレベル、Gate2: 実行レベル/レート制御、Gate3: ドローダウン監視）を組み込み、Gate3 NG で kill_switch を実行。
  - position_entries の DuckDB への書き込み（発注成功時に fill_date を記録。BUY / SELL の扱いを分離）。
  - PID ファイル書き込みと起動時の kill.flag 挙動（KILL_FLAG_CLEAR_ON_START による自動クリアを考慮）。
- 注文管理
  - OrderRecord データモデルと OrderState 列挙型を実装（状態遷移の許可表を定義）。
  - OrderRecord.transition_to による状態遷移検証（不正遷移は例外 InvalidStateTransitionError）。
  - OrderManager を実装（create_order / send_order / sync_order / cancel_order）。OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせる設計。
  - create_order: signal_id に対する重複 active 注文検出で DuplicateOrderError を投げる。DB の部分ユニークインデックス違反を DuplicateOrderError に変換。
  - send_order: クラッシュ耐性のため 2 相永続化パターンを採用（OrderSent を永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）。OrderRejectedError / OrderSentPendingError の扱いを明確化。
  - sync_order: broker 側の状態に同期。部分約定の量や平均価格のみの更新も考慮。
  - cancel_order: 終端状態ではキャンセル不可とする検証を実装し、broker API 呼び出しでキャンセル処理を行う。
- ブローカー実装（kabu station）
  - KabuStationClient を実装（httpx 同期クライアント、websocket 経由の push 支援）。
  - トークン取得の遅延初期化、401 受信時のトークン再取得と 1 回リトライ、HTTP エラーを BrokerAPIError / RateLimitError に変換。
  - kabu station のステータスコード → 内部ステータスマップを定義（open / partial / filled / cancelled / rejected）。
- 監視（Monitoring）
  - run_monitoring スクリプトにより SystemMonitor のポーリングループを提供。
  - MONITOR_POLL_INTERVAL 環境変数での上書きをサポート（不正値はデフォルト 60 秒にフォールバックし、警告を出力）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を実装。
  - 停止フラグ（stop_requested.flag）の検知でループを終了。
- DB 初期化/接続
  - monitoring 用 SQLite DB の初期化（init_monitoring_db）を各スクリプトで使用。
  - DuckDB 接続を分析用 DB として使用。
- ロギング / プロセス優先度
  - 起動時にアプリケーション名を渡して setup_logging を呼び出す慣習を導入。
  - set_process_priority("high") を実行開始時に呼び出し、実行プロセスの優先度設定を試みる設計。

### Changed
- （初回リリースのため過去との差分なし）

### Fixed / Reliability improvements
- .env パーサーの堅牢化: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、コメント取り扱いの改善。
- validate_config:
  - YAML パーサ（PyYAML）が未インストールの場合のフォールバック（警告表示 + パーススキップ）。
  - DB パスの親ディレクトリが存在しない場合は警告（起動時に自動作成される可能性がある旨を記載）。
  - KABUSYS_ENV=live の際に追加の安全確認（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
- OrderManager.send_order: クラッシュや broker の中間状態に対する堅牢性向上（broker_order_id を早期に永続化して Reconciliation を支援）。
- ExecutionEngine:
  - kill.flag 存在時の起動拒否/自動クリアの挙動を明示（KILL_FLAG_CLEAR_ON_START の考慮）。
  - WebSocket が未サポートの broker に対しては警告を出してスレッドをスキップ。
- Monitoring: MONITOR_POLL_INTERVAL が不正な整数（0 以下や非整数）の場合のフォールバックと警告を追加。

### Security
- .env を絶対に Git にコミットしない旨を .env テンプレートに明記。
- シークレット項目は対話時にマスク表示。

### Notes / Known limitations
- KabuStationClient は現時点で同期 HTTP クライアント (httpx.Client) を使用。将来的に非同期化するときは httpx.AsyncClient に差し替え可能な設計。
- 一部モジュール（OrderRepository 等）の詳細実装はこの差分に含まれないが、OrderManager / ExecutionEngine はそれらを前提に動作する設計になっている。
- config/*.yaml の検証は PyYAML が存在する場合のみ実行される（パーサが無ければファイル存在チェックのみ）。
- 一部のエラー・例外は呼び出し元で適切にハンドルすることを期待している（例: BrokerAPIError など）。

---

本 CHANGELOG はコードベースからの推測に基づいて作成しています。実際のリリースノート作成時は、コミット履歴やリリース管理（タグ・Issue・PR）と照らし合わせて調整してください。