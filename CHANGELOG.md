# Changelog

すべての notable な変更点はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
このプロジェクトはセマンティック バージョニングを採用しています。

## [0.1.0] - 2026-04-23

Added
- プロジェクト初版リリース。
- パッケージエントリポイントとバージョン:
  - kabusys.__version__ = 0.1.0 を設定。
- 環境設定管理:
  - kabusys.config: 環境変数 / .env ファイルの自動読み込み機能を実装。
    - プロジェクトルートの検出（.git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化できる。
    - _load_env_file による既存 OS 環境変数の保護（protected）。
  - 高度な .env パーサー実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理。
    - クォートなし行での inline コメント処理（直前が空白/タブの場合にコメントとして扱う）。
- Settings クラス（kabusys.config.Settings）:
  - J-Quants / kabu API / LINE / DB /監視 /システム関連設定プロパティを提供。
  - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など）を定義。
  - バリデーションを行い、不正値は ValueError を発生させる（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - is_live / is_paper / is_dev のユーティリティプロパティを提供。
- .env 初期化ウィザード CLI:
  - kabusys.config_setup: 対話式で .env の作成・更新を支援。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）。
  - secret 項目は表示をマスク、選択肢・デフォルトサポート、保存前の確認プロンプト。
  - --env-file で保存先を指定可能。
  - .env 書き込みテンプレートを提供（Git へコミットしない旨の注意を含む）。
- 設定検証ツール:
  - kabusys.validate_config: .env と config/*.yaml の起動前検証 CLI。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV, LOG_LEVEL, DB パスの基本検証。
    - config/*.yaml の存在確認および PyYAML があればパース検証（未インストール時は警告スキップ）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL（exit(1)）扱いにできる。
- 実行スクリプト / プロセス管理:
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - paper_trading 環境向けに分離された paper_trading DB を使用。
    - PID / stop flag / kill flag の取り扱い（PID ファイル書き込み、停止フラグ検出、KILL_FLAG_CLEAR_ON_START の考慮）。
    - プロセス優先度設定（set_process_priority("high")）。
    - Logging の初期化フロー（setup_logging）。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様を明示。
- Execution / 発注フロー:
  - execution.execution_engine.ExecutionEngine:
    - Signal Queue によるバッチ発注（シグナル処理ウィンドウ、push ドレインループ、セッション時間管理）。
    - kill_switch の実装（全 active 注文キャンセル、停止フラグセット）。
    - WebSocket push の受信と _push_queue による非同期処理（broker が stream_push を持たない場合はスキップ）。
    - Gate チェック（Gate1: シグナル、Gate2: エグゼキューション/レート制限、Gate3: ドローダウン監視）とそれに基づく発注制御。
    - 発注後の position_entries への書き込み（買いはエントリー登録、売りは売却日更新）。
    - 発注に関する監視 DB へのイベント記録（MonitoringDB が与えられた場合）。
  - execution.order_record.OrderRecord:
    - 注文状態を列挙した状態遷移モデル（OrderState）と遷移検証ロジック（InvalidStateTransitionError）。
    - transition_to による更新と updated_at 自動更新、オプションフィールド更新サポート。
    - 許可遷移テーブルを明確化。
  - execution.order_manager.OrderManager:
    - OrderRecord と OrderRepository を用いた外向き API（create_order, send_order, sync_order, cancel_order）。
    - DuplicateOrderError の導入（同一 signal_id の active 注文重複検出）。
    - send_order における「2相永続化」戦略:
      1) OrderSent に遷移して永続化（クラッシュ安全性）
      2) broker API 呼び出し
      3a) broker_order_id を先に永続化（state は Sent のまま）
      3b) OrderAccepted に遷移して永続化
      - OrderRejectedError は Rejected 状態に遷移して保存。
      - OrderSentPendingError（注文番号は発行されたが約定しない）は broker_order_id を永続化した上で例外を再送出し、Reconciliation の対象とする。
    - sync_order による broker 側ステータス同期（部分約定の進展は直接フィールド更新）。
    - cancel_order は終端状態ではエラーを返し、それ以外は broker にキャンセル要求を出して Cancelled に遷移。
- Broker / API クライアント:
  - execution.kabu_client.KabuStationClient:
    - httpx を用いた同期 REST API クライアントを実装（将来的に async への置き換えが容易）。
    - トークン取得ロジック（遅延初期化、401 時の再取得とリトライ）。
    - レスポンス JSON パース失敗やネットワーク/タイムアウトを BrokerAPIError に変換。
    - HTTP ステータスに応じた例外マッピング（401/429/5xx 等 → BrokerAPIError / RateLimitError）。
    - kabu station のステータスコードを内部状態文字列にマップ。
- モニタリング / DB:
  - monitoring 起動時に sqlite3 接続と DuckDB 接続を行い、init_monitoring_db を呼んでテーブルを保証。
  - SystemMonitor のループで stop flag 検知により優雅な終了処理を実装。
- リスク制御 / レート制限:
  - Execution 側でのレート制限チェックと再試行（最大 3 回）を実装。Circuit breaker 発生時はシグナルループを停止。
  - API 成功/失敗の記録（risk_manager.record_api_success / record_api_error）。

Changed
- n/a（初版のため既存機能の変更はなし）。

Fixed
- n/a（初版のためバグ修正履歴なし）。

Security
- 環境変数ファイル (.env) の取り扱いに関する注意を明示（.env を Git にコミットしないこと）。  
- シークレット値は対話ウィザードでマスク表示。

Notes / 注意事項
- config/*.yaml の内容検証は PyYAML の存在に依存する（未インストール時は警告を出してスキップ）。
- Settings の一部プロパティは不正値で ValueError を送出するため、起動前に kabusys.validate_config を実行して設定を確認することを推奨します。
- run_monitoring は説明どおり KABUSYS_ENV に依存せず production sqlite_path を使用します（監視データを常に同じ DB に保つ意図）。
- ExecutionEngine は kill.flag の存在を起動拒否条件とする（KILL_FLAG_CLEAR_ON_START=1 の場合のみ起動時にクリアして開始可能）。
- 発注フローはクラッシュ耐性を考慮して設計されていますが、運用では定期的な Reconciliation と監視が重要です。

Repository / CLI
- 実行可能モジュールとして下記が利用可能:
  - python -m kabusys.config_setup   (.env ウィザード)
  - python -m kabusys.validate_config (設定検証 CLI)
  - python -m kabusys.run_execution  (ExecutionEngine 起動スクリプト)
  - python -m kabusys.run_monitoring (SystemMonitor 起動スクリプト)

---

今後の予定（参考）
- BrokerAPI の追加 / テスト用モックの強化。
- async 対応や WebSocket のより堅牢な実装。
- 詳細なモニタリング / メトリクス出力の拡張。
- ドキュメントと運用ガイドの充実。