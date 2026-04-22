# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-04-22
初回リリース。KabuSys の基盤となる環境設定・起動スクリプト・発注エンジン・モニタリング周りの主要コンポーネントを実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 環境変数 / 設定管理
  - .env 自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。OS 環境変数を保護した上で `.env` / `.env.local` を読み込む（src/kabusys/config.py）。
  - .env の行パーサーは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応（src/kabusys/config.py）。
  - Settings クラスを実装し、アプリ全体で使用する設定プロパティ（J-Quants トークン、kabu API パスワード、DB パス、各種閾値やフラグなど）を提供。値の簡易検証（許容値チェック）を行う（src/kabusys/config.py）。
  - Paper Trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）や PAPER_FILL_MODE の検証を実装。

- 環境設定ウィザード CLI
  - 対話式ウィザードで .env の作成・更新を支援する CLI を追加。デフォルト値、選択肢、シークレットマスク表示、既存 .env の読み込み・再利用に対応（src/kabusys/config_setup.py）。
  - 書き込まれる .env に注意書きを付与（Git へのコミット禁止等）。

- 設定検証ツール
  - 起動前に環境変数や config/*.yaml の不備を検出する CLI を実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DUCKDB_PATH/SQLITE_PATH の親ディレクトリ存在確認。
    - config/*.yaml の存在確認と（PyYAML インストール時）パース検証。PyYAML 未インストール時は警告を出してパースをスキップ。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険値チェック）。
    - --strict フラグで警告を失敗扱いにできる。

- 実行用スクリプト
  - 実行エンジン起動スクリプト（run_execution）を追加：
    - ExecutionEngine の初期化、DB 接続（paper_trading 時は分離 DB を使用）、PID/stop フラグ管理、スレッドでのエンジン実行、停止ハンドリングを実装（src/kabusys/run_execution.py）。
  - 監視ループ起動スクリプト（run_monitoring）を追加：
    - SystemMonitor のポーリングループ、MONITOR_POLL_INTERVAL による間隔指定、停止フラグ検知、DB 初期化処理を実装（src/kabusys/run_monitoring.py）。

- 発注エンジン / 実行ロジック
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）：
    - シグナル読み込み（DuckDB）→ Gate1/Gate2 を通すシグナル処理ループ（発注期間）、WebSocket (push) ドレインループ（9:10-15:30）を設計。
    - kill.flag の検査と KILL_FLAG_CLEAR_ON_START の挙動（起動時）を実装。
    - PID ファイル管理、WebSocket スレッド（broker 側に stream_push がある場合のみ起動）を実装。
    - 発注時のレート制限リトライ、発注遅延計測、position_entries への書き込み、監視 DB へのイベント記録を実装。
    - kill_switch による全 active 注文のキャンセルと停止フローを実装。

- 注文状態管理
  - OrderRecord（状態遷移ロジック）を実装（src/kabusys/execution/order_record.py）：
    - 状態列挙 OrderState と許可遷移テーブル、transition_to による遷移検証（不正遷移時は InvalidStateTransitionError を raise）。
    - 更新時刻の自動更新、オプションフィールドの差分更新をサポート。

  - OrderManager を実装（src/kabusys/execution/order_manager.py）：
    - create_order（signal_id の重複検出: DuplicateOrderError）、send_order（2相永続化: OrderSent の永続化 → ブローカー呼び出し → broker_order_id 永続化 → OrderAccepted など）、sync_order（broker との状態同期）、cancel_order（終端状態チェック）を実装。
    - OrderSentPendingError の扱い（ブローカーが注文番号を返すが約定しないケース）に対応。
    - DB の部分ユニーク制約違反（signal_id）を DuplicateOrderError に変換。

- ブローカークライアント（kabu）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）：
    - httpx を用いた同期 REST クライアント。トークン取得（/token）と遅延初期化、自動再取得機構を実装。
    - 401 発生時にトークン再取得して一回リトライするロジック。
    - 429（レート制限）や 5xx のエラーを専用例外へ変換、タイムアウト・ネットワークエラーの扱いを明確化。
    - kabu station の状態コードを内部ステータスにマッピング。

- リスク管理・リコンシリエーション連携
  - ExecutionEngine から RiskManager, Reconciler と連携する設計を実装（src/kabusys/execution/* 参照）。Gate1/Gate2/Gate3 による発注制御、リコンシリエーションによるクラッシュ後の回復を想定。

- 監視DB連携
  - monitoring DB 初期化関数の呼び出し、イベントログ記録フローを組み込み（run_monitoring / ExecutionEngine 発注時の監視書き込み）。

- ユーティリティ連携
  - process_priority（優先度設定）や logging_setup との統合ポイントを追加（run_execution, run_monitoring）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- .env を Git にコミットしないよう警告を .env ヘッダへ記載（config_setup にて）。環境変数の保護（OS 環境変数を protected として扱う）を実装。

### Notes / Known limitations
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行われ、未インストール時は警告を出してスキップします。
- KabuStationClient は同期 HTTP クライアント（httpx.Client）実装のため、将来的に非同期対応 (httpx.AsyncClient) に置き換える余地があります。
- ExecutionEngine の時間依存ロジック（シグナル処理ウィンドウ等）は本番の取引時間に合わせて調整が必要な場合があります。
- 本リリースは機能実装が中心であり、さらなるテストや堅牢化（例: 詳細な監査ログ、より厳格な例外ハンドリング等）が今後の課題です。

----- 

（以降のリリースでは新增機能やバグ修正、内部実装の変更点をこのファイルに追記してください。）