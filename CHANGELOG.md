# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]
- 現在なし

## [0.1.0] - 2026-04-23
初回リリース。日本株自動売買システム「KabuSys」の基本的な実行基盤・設定管理・発注フローを実装。

### Added
- 基本バージョニング
  - パッケージバージョンを src/kabusys/__init__.py にて `0.1.0` として定義。
- 環境設定・管理
  - 環境変数を自動読込する機能を実装（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む。
    - .env の行解析で export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - OS 環境変数を保護するための上書きルール（protected set）をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - Settings クラスを実装してアプリ全体の設定を型的に提供（J-Quants / kabu API トークン、DB パス、ログレベル、環境判定、各種しきい値など）。
    - 一部設定値は値検証を行い、不正値で ValueError を送出（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- 環境構築ウィザード
  - src/kabusys/config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - 質問リスト、シークレット扱い、選択肢、デフォルト表示、既存値の読み込み・再利用、保存確認などをサポート。
    - 保存時のテンプレートヘッダに「.env を Git にコミットしない」旨の注意を含む。
- 設定検証 CLI
  - src/kabusys/validate_config.py: 起動前に .env と config/*.yaml の設定不備を検出する CLI を実装。
    - 必須/任意環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス親ディレクトリ存在チェック、YAML のパース検査（PyYAML が存在する場合）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認など）。
    - --strict フラグで警告も失敗扱いにできる。
- 実行スクリプト
  - src/kabusys/run_execution.py: ExecutionEngine を起動するエントリポイントを実装。
    - paper_trading 時は専用 SQLite（paper_trading DB）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）の扱いを実装。
    - プロセス優先度設定・ロギング初期化を組み込み。
  - src/kabusys/run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを実装。
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用することを明記。
- 発注エンジン（Execution）
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）を実装。
    - セッション制御（signal_send_start: 8:50 / signal_send_end: 9:10 / market_close: 15:30）。
    - シグナル読み込み（DuckDB）→ Gate1/Gate2 によるリスクチェック → 発注 → push ドレインループ（WebSocket）による同期。
    - kill.flag による起動拒否や起動時自動クリア（KILL_FLAG_CLEAR_ON_START）対応。
    - WebSocket push を受けて内部キューに入れ、sync + Gate3 チェックを実施。
    - ExecutionEngine.run_session の安全な PID 書き込み / 後片付け処理。
- 注文状態管理
  - OrderRecord（src/kabusys/execution/order_record.py）:
    - 注文状態の列挙型 OrderState と状態遷移テーブルを実装。
    - transition_to による遷移検証（不正遷移で InvalidStateTransitionError を送出）。
    - created_at/updated_at の自動更新、部分約定情報等の保持。
  - OrderManager（src/kabusys/execution/order_manager.py）:
    - create_order / send_order / sync_order / cancel_order の外向き API を実装。
    - 同一 signal_id の重複防止（DB 参照＋部分ユニーク制約ハンドリングによる DuplicateOrderError）。
    - send_order はクラッシュ安全性を意識した手順（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 遷移）を実装（2相永続化）。
    - OrderSentPendingError を適切に扱い、pending 状態の保存と呼び出し元伝播を行う。
    - sync_order では broker 状態を DB に反映し、部分約定の進展はフィールド更新で対応。
    - cancel_order はキャンセル不可能な状態を判定し、必要なら broker の cancel を呼ぶ。
- ブローカークライアント（kabu station）
  - KabuStationClient（src/kabusys/execution/kabu_client.py）:
    - httpx を利用した同期 REST クライアント実装。
    - トークン管理（遅延取得、401 時の再取得と1回リトライ）を内包。
    - レスポンス JSON パースの失敗やタイムアウト/ネットワークエラーを BrokerAPIError に変換。
    - 429 に対する RateLimitError の導入。
    - kabu station の状態コード → 内部ステータス文字列のマッピングを定義。
    - 将来の WebSocket/非同期化を見越した設計（httpx.Client のラップ）。
- DB / 監視連携
  - DuckDB と SQLite（監視 DB）を組み合わせたデータストア利用を導入。
  - 監視用 DB への初期化関数（init_monitoring_db）を利用して冪等にテーブル準備。
  - ExecutionEngine の発注成功/遅延情報を監視 DB にログする hook（MonitoringDB 経由、例外は無害化）。
- リスク管理との統合
  - RiskManager を利用して Gate1/Gate2/Gate3 のチェックを実施する設計を導入（発注可否、レート制限、ドローダウンによる kill）。
  - ExecutionEngine 内での再試行ロジック（Gate2 のレート制限に対する3回リトライ）と Circuit Breaker の取り扱い。
- ユーティリティ
  - .env 書込テンプレートと注意書きを含む .env 生成ロジック（config_setup）。
  - MONITOR_POLL_INTERVAL の不正値対応（0以下や非整数はデフォルトにフォールバック）。
  - process priority 設定やロギングセットアップの呼び出し箇所を統一（setup_logging, set_process_priority を利用）。

### Changed
- 初回リリースのため、既存リポジトリからの互換性変更はなし（ベースライン実装）。

### Fixed
- .env パーサーの扱いを堅牢化
  - クォート内のバックスラッシュエスケープ処理、インラインコメントの誤認防止、export プレフィックス対応等により現場での .env 記述の互換性を改善。
- Execution / Monitoring の安全性強化
  - Execution の OrderSent 〜 broker 呼び出し周りでの永続化順序を明確化し、クラッシュ時の復旧可能性（Reconciliation）を向上。

### Security
- config_setup で生成する .env のヘッダに「.env を絶対に Git にコミットしないこと」を明記。
- 環境変数読み込み時に OS 環境変数を保護（上書きを防ぐ設計）して、CI/OS レベルの機密値が .env で上書きされないよう配慮。

### Removed
- なし

---

注:
- 実装は多数のコンポーネント（リコンシリエーション、監視 DB、リスク管理、broker API 抽象）に依存する設計になっており、詳細な振る舞い（外部 API のエラー詳細や監視スキーマなど）は実行環境と結合して確認する必要があります。
- 今後のリリースで以下が想定されます: テストスイートの充実、非同期クライアント対応、さらに細かい監視メトリクス追加、設定項目の拡張。