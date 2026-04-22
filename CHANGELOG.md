# Changelog

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

## [0.1.0] - 2026-04-22

初回公開リリース。

### 追加 (Added)
- 基本パッケージの骨組みを実装しました（kabusys 0.1.0）。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
- 環境設定管理（src/kabusys/config.py）
  - プロジェクトルートを .git / pyproject.toml から自動検出し、.env/.env.local を自動ロード。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env 読み込みの挙動:
    - `.env` を既存 OS 環境変数を上書きしない形で読み込み、`.env.local` は上書き可能（ただし OS 環境変数は保護）。
    - `_parse_env_line` による堅牢な行パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応）。
  - Settings クラスを実装し、環境変数からアプリケーション設定を取得する API を提供（例: `settings.jquants_refresh_token`）。
  - 各種検証を実装（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。無効値は ValueError を送出。
- 環境設定ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式で `.env` の初期作成・更新をサポートするウィザードを実装。
  - シークレット値は表示時にマスク、選択肢・デフォルト値の反映、キャンセル時の安全な挙動をサポート。
  - `.env` のテンプレート出力を行う `_write_env` を実装（Git にコミットしない旨のヘッダ付き）。
- 設定検証ツール（src/kabusys/validate_config.py）
  - 起動前に .env および config/*.yaml の設定不備を検出する CLI を実装。
  - 必須 / 任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がある場合）などを実施。
  - `--strict` オプションで警告も FAIL 扱いにできる。
- 実行スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - `paper_trading` 環境用に本番 DB と分離された paper_trading 用 SQLite を使用する挙動を採用。
    - プロセス優先度設定、PID ファイル、停止フラグ検出を実装。
  - Monitoring ポーリングスクリプト（src/kabusys/run_monitoring.py）
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ検出、例外発生時のロギング、DB のクローズ処理を含む安定化処理を実装。
- 注文関連コアロジック（src/kabusys/execution/*）
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態 (OrderState) を enum 化し、許可された状態遷移を定義。
    - 状態遷移検証とタイムスタンプ自動更新ロジックを実装。無効遷移では InvalidStateTransitionError を送出。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - signal_id 単位での重複発注防止（DuplicateOrderError）。
    - create / send / sync / cancel の API を提供。
    - send_order はクラッシュ耐性を考慮した 2相的永続化戦略を実装（OrderSent 前後の挙動、OrderSentPendingError の扱い、Rejected の処理など）。
    - sync_order による broker 側状態照合と部分約定の反映を実装。
    - cancel_order はキャンセル不可状態のチェックを行う。
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル読み込み → Gate1/2 のリスクチェック → 発注 → push ドレイン（Gate3）のワークフローを実装。
    - Gate1: シグナルレベル検査、Gate2: エグゼキューションレベル（レート制限・サーキットブレーカー）、Gate3: ドローダウン監視（発見時に kill_switch を発動）。
    - kill_switch は全 active 注文をキャンセルし、ループを停止する機能を提供。
    - WebSocket 用ワーカースレッド（broker が stream_push を提供する場合に有効）と、push ペイロードの処理 / client_order_id 同定 / sync_order 呼び出しを実装。
    - 発注成功時に position_entries を DuckDB に登録して最低保有日数・再エントリー制限に対応。
    - 起動時の Reconciliation 呼び出し（reconciler が提供されている場合）を実装。
- kabu station クライアント（src/kabusys/execution/kabu_client.py）
  - HTTP クライアント実装（httpx 同期クライアント）を追加。
  - トークン取得（遅延初期化・自動再取得）、401 の際の再取得リトライ、429（レート制限）や 5xx のハンドリング、JSON パースエラーの変換を実装。
  - kabu station の注文状態コード → 内部ステータスへのマッピングを実装。

### 変更 (Changed)
- 設定周りの動作設計
  - 環境変数のロード順序を OS 環境変数 > .env.local > .env として明確化。
  - .env ロード時に OS 環境変数を保護するため protected キーセットを導入（テスト時の上書き制御を容易に）。
- Reconciliation / 発注の耐障害性向上
  - send_order の実装で broker_order_id を先に永続化することで、途中クラッシュ時の状態回復（Reconciliation）を容易にした（Issue #32 に対処する意図の修正）。
- ログ・監視の扱い
  - 実行スクリプトでプロセス優先度変更、PID ファイル管理、停止フラグの標準化を行い、運用時の安定性を改善。

### 修正 (Fixed)
- 環境ファイルパーサの堅牢化
  - クォート文字内でのバックスラッシュエスケープ処理、インラインコメントの解釈などを改善し、一般的な .env フォーマットの誤読を減らすよう修正。
- state machine の安全性
  - OrderRecord.transition_to で許可されていない遷移時に明示的な例外を投げるようにして、不整合な状態変更を防止。

### セキュリティ (Security)
- .env の注意喚起
  - config_setup にて .env を絶対に Git にコミットしない旨をファイルヘッダに明記。
- シークレットの扱い
  - ウィザードで入力時にシークレット値をマスク表示。

### 内部 (Internal)
- モジュール分割と依存の整理（execution, monitoring, utils などの責務分離）。
- 追跡用のログメッセージや警告メッセージを整備し運用時のトラブルシュートを容易に。
- 一部外部依存関係（PyYAML, httpx, websocket, duckdb, sqlite3 等）を暗黙に想定し、存在しない場合は検証をスキップまたは適切に例外変換する実装。

### 既知の制限 / 注意事項
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行われます。未インストール時は検証がスキップされ、警告が出力されます。
- KabuStationClient は現状同期的な httpx.Client を使用しており、将来的に非同期化する場合は httpx.AsyncClient へ切り替える想定です。
- 一部の ValueError / RuntimeError は起動時や API 呼び出し元で適切にハンドリングする必要があります（運用向けに追加のラッピングや再試行ロジックを検討してください）。

---

今後のリリースでは、API のさらなる拡充（バックテスト周りの統合、より詳細な監視イベント、非同期処理対応など）やドキュメント・テストの強化を予定しています。