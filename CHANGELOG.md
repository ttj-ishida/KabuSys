Keep a Changelog に準拠した形式で、コードベースから推測した変更履歴を日本語で作成しました。

# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-23
初回リリース

### Added
- 基本パッケージ情報
  - パッケージバージョンを 0.1.0 に設定 (src/kabusys/__init__.py)。

- 環境設定管理
  - Settings クラスによる環境変数ベースの設定管理を追加 (src/kabusys/config.py)。
    - 必須変数取得用の _require() を提供し、未設定時に ValueError を送出。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH 等のパスプロパティを提供。
    - PAPER_FILL_MODE, CPU/MEMORY/DISK 閾値など各種設定の取得・検証ロジックを提供。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェック。
    - 自動 .env 読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。

  - .env ファイルのパース機能（クォート、エスケープ、インラインコメントの扱いを考慮）を実装。

- 設定ウィザード CLI
  - 対話式ウィザードで .env を作成/更新するコマンドを追加 (src/kabusys/config_setup.py)。
    - 設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン等）。
    - 既存 .env 読み込み、シークレット表示のマスク、選択肢チェック、保存の確認を実装。
    - .env を生成する際のテンプレート出力（.env に関する注意コメントを含む）。
    - 中断時の安全処理（EOF/KeyboardInterrupt を適切に扱う）。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加 (src/kabusys/validate_config.py)。
    - 必須環境変数の未設定検出、プレースホルダ値（"_here" / "your_value"）の警告検出。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（有効値セットの検査）。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在確認と（PyYAML がインストールされていれば）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を失敗扱いにできる。

- 実行スクリプト
  - 監視ループ起動スクリプトを追加 (src/kabusys/run_monitoring.py)。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動。
    - プロセス優先度設定、監視 DB 初期化、DuckDB 接続、停止フラグ検知、例外ハンドリングを実装。

  - ExecutionEngine 起動スクリプトを追加 (src/kabusys/run_execution.py)。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - プロセス優先度設定、監視 DB 初期化、停止フラグ検知、エンジンスレッド制御を実装。

- Execution エンジンと関連コンポーネント
  - ExecutionEngine の実装を追加 (src/kabusys/execution/execution_engine.py)。
    - シグナル処理（signal_send_start 〜 signal_send_end）と push ドレイン（market_close まで）の実装。
    - Gate1 (シグナルレベル)、Gate2 (エグゼキューションレベル、レート制限とサーキットブレーカー)、Gate3 (ドローダウン監視) を導入。
    - size_multiplier の適用（BUY のみ、100 株単位に丸め）や position_entries への書き込みロジック。
    - WebSocket push 処理（broker 側の stream_push を利用）と push による同期・Gate3 評価。
    - PID ファイルの書き出しと kill.flag の検査／自動クリア (KILL_FLAG_CLEAR_ON_START)。

  - OrderRecord（状態遷移モデル）を追加 (src/kabusys/execution/order_record.py)。
    - 厳格な状態遷移の定義（許可される遷移マップ）と InvalidStateTransitionError。
    - transition_to による更新と更新日時の自動セット、オプションフィールドの更新。

  - OrderManager を追加 (src/kabusys/execution/order_manager.py)。
    - create_order: signal_id ごとの active 注文の重複検出（DuplicateOrderError）、UUID を client_order_id として採番し DB に保存。
    - send_order: 2 相永続化戦略を採用（OrderSent を先にコミット → broker 呼び出し → broker_order_id を保存 → OrderAccepted に遷移）
      - OrderRejectedError / OrderSentPendingError の扱いを実装（pending の場合は broker_order_id を保存したまま OrderSent の状態を残す）。
      - 送信前に OrderSent に永続化することでクラッシュ発生時に照合可能な状態を保証する設計。
    - sync_order: broker 側ステータス取得と状態同期（部分約定時は filled_qty / avg_fill_price の更新を反映）。OrderSent→Filled 等の特殊ケースで OrderAccepted を経由する回復ロジック。
    - cancel_order: 終端状態はキャンセル不可としてエラーにし、broker_order_id がある場合は broker 側キャンセル API を呼ぶ。

  - Reconciler / RiskManager 等（参照により ExecutionEngine と連携。コード内での利用ロジックが含まれる）。

  - OrderRepository との組み合わせによる DB 永続化（SQLite）との連携（SQL 制約を用いた重複検出の扱いを含む）。

- Broker クライアント実装（kabu station）
  - KabuStationClient を追加 (src/kabusys/execution/kabu_client.py)。
    - httpx を使った同期 REST クライアント実装。
    - トークン取得の遅延初期化と、401 時のトークン再取得 + 1 回リトライの実装。
    - 429 をレート制限エラーとして特殊扱い（RateLimitError を送出）、HTTP 5xx をサーバーエラーとして扱う。
    - kabu station の状態コードから内部ステータス文字列へのマッピング実装。
    - WebSocket 経路 (websocket ライブラリ) を通じた push 受信のための基盤を用意（stream_push に依存）。

- 監視関連
  - monitoring_db 初期化と SystemMonitor を利用するためのランナー（run_monitoring/run_execution で利用）。

- ロギング・プロセス制御ユーティリティ
  - setup_logging、set_process_priority 等を利用する起動スクリプトを提供（ユーティリティ自体は参照される）。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- .env ファイルを Git にコミットしないよう明示的に注意書きを .env 生成テンプレートに追加。
- 秘密情報を対話表示時にマスク (config_setup) することで誤表示のリスクを軽減。

### Notes / Implementation details
- .env のパースはシェル互換の細かいケース（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い）に配慮した実装になっているため、既存の .env 形式との互換性を高く保つ設計。
- validate_config は PyYAML が無い環境でも動作する（YAML パース検証をスキップし、警告を出す）。
- ExecutionEngine および OrderManager の設計はクラッシュ耐性を重視しており、OrderSent の先行永続化と broker_order_id の永続化により Reconciliation 処理での回復を可能にしている。
- paper_trading モードでは paper_trading 用の SQLite を使い、本番データベースと完全に分離することで安全な検証が可能。

---

今後リリースでは、テストケース追加、ドキュメント強化、非同期クライアント対応（httpx.AsyncClient）、およびさらに詳細な監視／メトリクス出力の追加などを予定できます。必要であれば、上記の各項目をさらに分割して詳細な変更ログを作成します。