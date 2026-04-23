CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

0.1.0 - 2026-04-23
------------------

Added
- 全体
  - 初回リリース。日本株自動売買システム KabuSys の基本的な実行・監視・設定管理コンポーネントを追加。
  - パッケージバージョンを __version__ = "0.1.0" として設定。

- 設定管理 / 起動支援
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加（優先順位: OS > .env.local > .env）。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出するため CWD に依存しない読み込み。
    - .env の高度なパース実装を追加（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途向け）。
    - Settings クラスを追加し、環境変数から型付けされた設定値（トークン、パス、閾値、フラグ等）を取得・検証するプロパティ群を提供。E.g. env/log_level の値検証、PAPER_FILL_MODE 検証。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の新規作成・更新を支援する CLI を追加。
    - 多数の設定項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DBパス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を提供。
    - シークレット項目は表示をマスク、選択肢・デフォルト値、既存 .env の読み込みと Enter で既存値再利用などをサポート。
    - .env の書き出しテンプレートを提供（注意: .env を Git にコミットしない旨を明記）。

  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する検証 CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）などを実装。
    - --strict オプションで警告を FAIL（exit(1)）扱いにできる。

- 実行 / 監視ランナー
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するためのエントリスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - PID ファイル書き込み、停止フラグ検出（data/stop_requested.flag）、プロセス優先度設定（utils.process_priority 経由）をサポート。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視 DB（SQLite）と分析 DB（DuckDB）接続を行い、停止フラグ検出で安全に終了する。

- 注文管理 / 実行エンジン
  - src/kabusys/execution/order_record.py
    - OrderRecord データモデルと状態遷移ロジックを追加。OrderState 列挙（created/sent/accepted/partial/filled/closed/cancelled/rejected）と許可遷移セットを定義。
    - 不正な状態遷移で InvalidStateTransitionError を raise。

  - src/kabusys/execution/order_manager.py
    - DB（OrderRepository）と OrderRecord を組み合わせた外向き API を提供: create_order, send_order, sync_order, cancel_order。
    - create_order: 同一 signal_id の active 注文検出で DuplicateOrderError を raise。DB の部分ユニークインデックス違反（signal_id）を DuplicateOrderError に変換。
    - send_order: クラッシュ・再起動に強い二相永続化戦略を採用（OrderSent を事前コミット → broker 呼び出し → broker_order_id をコミット → OrderAccepted に遷移）。OrderRejectedError / OrderSentPendingError の扱いを実装。
    - sync_order: broker からの状態取得に基づく同期ロジック（同一状態でも filled_qty / avg_fill_price の更新を反映、必要により OrderAccepted を経由して遷移）。
    - cancel_order: 終端状態はキャンセル不可として InvalidStateTransitionError。

  - src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型の発注エンジンを実装。セッションスケジューリング（発注時間帯・ドレイン時間帯）を実装。
    - Gate 1（シグナルレベル）、Gate 2（実行レート制限、Circuit Breaker 対応）、Gate 3（ドローダウン監視）を導入し、失敗時は発注を抑止または kill_switch 発動。
    - kill_switch: 全ループ停止と全 active 注文のキャンセル処理を実装（API エラーはログに留め継続）。
    - WebSocket push の受信を非同期スレッドで行い、push をトリガに sync_order と Gate 3 評価を実施。
    - position_entries（DuckDB）への書き込みを実装し、発注の成功/保留/失敗に応じて挙動を分岐。発注遅延（latency_ms）を監視 DB に記録可能（MonitoringDB が注入された場合）。

  - src/kabusys/execution/kabu_client.py
    - kabu ステーション用 REST クライアント KabuStationClient を実装（httpx 同期クライアントを使用）。
    - トークンの遅延取得・自動再取得を実装（401 受信時に再取得してリトライ）。
    - タイムアウト/ネットワークエラーを BrokerAPIError にラップ、429 は RateLimitError に変換。
    - 将来的な async 対応に配慮して設計。

- その他ユーティリティ連携
  - 各 run_* スクリプト・エンジンで utils.logging_setup.set_up_logging, utils.process_priority.set_process_priority, monitoring_db.init_monitoring_db 等の補助を使用する設計により、起動時の初期化処理を統一。

Changed
- 設計面
  - 発注フローの頑健性を重視した設計を採用。送信処理の二相永続化（OrderSent を先に永続化し broker_order_id を別途永続化）や、Reconciliation によりクラッシュ後の状態復元を容易にする仕組みを導入。
  - Paper trading（paper_trading 環境）は本番 DB と完全分離する方針を明確化（paper_sqlite_path を使用）。

Fixed
- 信頼性/クラッシュ安全性
  - OrderManager.send_order 周りでのクラッシュによる不整合を考慮し、broker_order_id が残るケースでも sync_order により復元可能にする実装を導入。
  - ExecutionEngine で kill.flag 存在時の起動拒否や KILL_FLAG_CLEAR_ON_START=1 の挙動（クリアして起動）を明確に実装。

Security
- 機密情報の取り扱い
  - config_setup の対話式 UI でシークレット項目（API トークン / パスワード等）はマスク表示。
  - README や .env 書き出しヘッダで .env を Git にコミットしない旨を明記。

Notes / Migration
- .env の自動読み込みはデフォルトで有効。テストや特殊用途で自動読み込みを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config により起動前に設定をチェックできます: python -m kabusys.validate_config（--strict で警告をエラー扱い）。
- 実行時の停止制御は data/stop_requested.flag および kill.flag により行われます。運用時の手順に合わせてフラグファイルの扱いを確認してください。

---- End of CHANGELOG ----

（この CHANGELOG はコードベースからの推測に基づく要約です。細部仕様や実装の拡張・修正が行われた場合は適宜更新してください。）