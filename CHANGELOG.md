# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載します。  
このファイルはコードベースから推測して作成した変更履歴です。

フォーマット:
- 追加: 新機能
- 変更: 既存機能の振る舞い・内部実装の変更
- 修正: バグ修正
- セキュリティ: セキュリティに関する注意

※ バージョンはパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-22
Initial release

### 追加
- 基本パッケージ情報
  - パッケージ名: KabuSys、バージョン 0.1.0 を追加（src/kabusys/__init__.py）。
- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。環境変数から各種設定（API トークン、DB パス、LINE トークン、KABUSYS_ENV、LOG_LEVEL、閾値など）を取得するプロパティを提供。
  - .env 自動読み込み機能を導入。プロジェクトルート（.git または pyproject.toml を探索）を基準に .env と .env.local を読み込み。環境変数による自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースの強化:
    - export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、行末コメントの扱いなどを実装（_parse_env_line）。
  - 設定検証（型や値の妥当性）:
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の許容値チェックを実装し、不正値で ValueError を送出するようにした。
  - paper_trading モードの DB 分離:
    - paper_sqlite_path を用意し、KABUSYS_ENV=paper_trading 時は本番監視 DB と分離して動作するようにした。
- 設定ウィザード CLI
  - config_setup ウィザードを追加（src/kabusys/config_setup.py）。対話的に .env を生成・更新可能。シークレットは表示をマスク。生成される .env のテンプレートと注意書きを出力。
- 設定検証 CLI
  - validate_config CLI を追加（src/kabusys/validate_config.py）。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML があればパース検証を行う。--strict オプションで警告も失敗扱いにできる。
- 実行スクリプト
  - run_execution（src/kabusys/run_execution.py）を追加。ExecutionEngine 起動スクリプト。起動前にプロセス優先度設定、DB 初期化、paper_trading での専用 DB 使用、停止フラグ検出（stop_requested.flag）等を行う。
  - run_monitoring（src/kabusys/run_monitoring.py）を追加。SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能。監視は常に本番 sqlite_path を使用する。
- 発注エンジンと関連コンポーネント
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）を追加。シグナルの読み込み、Gate1/Gate2/Gate3 によるリスクチェック、発注ループ（8:50〜9:10）と push ドレインループ（9:10〜15:30）、WebSocket push の取り込み、kill_switch の実装、PID ファイル管理、起動時リコンシリエーション呼び出しなどを実装。
  - OrderRecord（src/kabusys/execution/order_record.py）を追加。注文状態の Enum（created, sent, accepted, partial, filled, closed, cancelled, rejected）と状態遷移ロジックを実装。不正遷移時に InvalidStateTransitionError を発生させる。
  - OrderManager（src/kabusys/execution/order_manager.py）を追加。OrderRecord と OrderRepository（SQLite）を組み合わせた外向き API を提供。create_order/send_order/sync_order/cancel_order 等を実装。送信時に耐クラッシュ性のための二相永続化（OrderSent を DB に保存 → broker 呼出し → broker_order_id を保存 → OrderAccepted に遷移）を採用。OrderSentPendingError 処理や DuplicateOrderError の扱いを実装。
  - 発注フローにおける各種設計:
    - send_order の例外処理: OrderRejectedError は Rejected に遷移、OrderSentPendingError は broker_order_id を保存して OrderSent のまま残し再送元へ例外伝播。
    - sync_order は broker 側のステータスに同期しつつ、部分約定の filled_qty / avg_fill_price の更新をサポート。OrderSent→Filled/Partial の遷移では OrderAccepted を経由するロジックを組み込む。
    - cancel_order はキャンセル不可状態（Closed/Cancelled/Rejected/Filled）では InvalidStateTransitionError を送出し、broker_order_id があれば API を呼んでキャンセルを実施。
  - ExecutionEngine は発注結果を DuckDB の position_entries（約定整理）に記録し、監視 DB（MonitoringDB）があれば発注イベントをログに残す処理を追加。
- ブローカークライアント（kabu station）
  - KabuStationClient（src/kabusys/execution/kabu_client.py）を追加。httpx を使用した同期 REST クライアントを実装。トークン取得（遅延初期化・自動再取得）、認証付きリクエスト、401 リトライ、429 レート制限判定（RateLimitError）、サーバーエラー判定（BrokerAPIError）等を実装。また将来的な WebSocket 対応のため stream_push（push 処理）と組み合わせる設計。
- 監視 DB 初期化と SystemMonitor 起動のための初期コードを導入（run_monitoring から呼び出し）。
- プロセス優先度設定ユーティリティ（呼び出しを行う箇所が利用）とログセットアップの呼び出しを各起動スクリプトに追加（setup_logging / set_process_priority を使用）。

### 変更
- なし（初回リリースのため既存機能の変更は無し）

### 修正
- なし（初回リリース）

### セキュリティ / 注意事項
- .env は絶対に Git にコミットしないでください（config_setup にもその旨の注意を明記）。
- 本番起動時（KABUSYS_ENV=live）の注意:
  - validate_config と config_setup のメッセージに従い、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を確認してください。KILL_FLAG_CLEAR_ON_START=1 は本番では危険（自動で Kill Flag をクリア）。
- validate_config は PyYAML が未インストールの場合 YAML のパース検証をスキップし警告を出します。YAML 内容の検証が必要な場合は PyYAML をインストールしてください。

### 既知の制限 / TODO（推測）
- KabuStationClient の実装は同期 httpx.Client を用いており、将来的な非同期化は httpx.AsyncClient への切り替えで対応可能。
- 一部ファイル（kabu_client の末尾など）がプロジェクト内で続きが存在する可能性があり、追加のエラー処理やレスポンスマッピングが存在する想定。
- テスト・エラーハンドリングの補強（統合テストや長期実行時の安定性検証）が今後の課題。

---

（この CHANGELOG はソースコードの内容から推測して作成したものであり、実際のコミット履歴に基づくものではありません。実際のリリースノート作成時はコミット単位の変更点を反映してください。）