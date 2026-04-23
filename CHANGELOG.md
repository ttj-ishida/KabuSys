# CHANGELOG

すべての変更は Keep a Changelog に準拠して記載しています。  
安定版リリースのルールや日付は、コードベースから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-23

最初の公開リリース。本リリースでは、環境設定・起動ツール、監視/実行エンジン、発注フローのコアロジックを実装しています。

### 追加 (Added)
- 環境設定・管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートの .git または pyproject.toml を探索基準に検出）。
  - 自動読み込みは OS 環境変数を保護（上書き禁止）し、.env と .env.local の優先順で読み込む。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを強化。export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォート有無での違い）などに対応。

- 設定オブジェクト
  - Settings クラスを導入。アプリケーション設定を環境変数から取得するプロパティ群を提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE 関連、DB パス、PID/KILL フラグパス、閾値、env/log_level 等）。
  - PAPER_FILL_MODE の検証を実装（有効値: instant, partial, never, reject）。
  - 環境値（KABUSYS_ENV）や LOG_LEVEL の検証を追加。
  - settings 単一インスタンスをエクスポート。

- .env ウィザード CLI
  - 対話式に .env を生成/更新する config_setup CLI を追加。シークレットのマスク表示、選択肢・デフォルト提示、保存確認、.env のテンプレート生成機能を実装。
  - 生成される .env ファイルに注意書き（Git にコミットしない等）を含める。

- 設定検証 CLI
  - validate_config CLI を追加。.env と config/*.yaml の設定不備を起動前に検出。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）や KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAMLがあれば）パース検証を実装。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の警告など）。
  - --strict オプションを実装（警告を FAIL 扱いして exit(1) で終了）。

- 実行・監視ランナー
  - run_execution スクリプトを追加。ExecutionEngine を起動し、paper_trading の場合は専用の paper_trading SQLite を使用して本番 DB と完全分離。
  - run_monitoring スクリプトを追加。SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用。

- 発注関連コア
  - OrderRecord データモデルと状態遷移ロジックを実装。OrderState 列挙と許可遷移マップ、transition_to による遷移検証（InvalidStateTransitionError を投げる）を提供。updated_at の自動更新や関連フィールドのオプション更新に対応。
  - OrderManager を実装し、以下を実現：
    - create_order: signal_id の重複検出（アクティブな注文が存在する場合は DuplicateOrderError）。
    - send_order: クラッシュ耐性を考慮した二相永続化フロー（OrderSent に先に永続化 → broker 呼び出し → broker_order_id の先コミット → OrderAccepted に遷移）。OrderRejectedError / OrderSentPendingError の扱い。OrderSent のまま残るケースや、pending の扱いに対応。
    - sync_order: broker の状態取得に基づく同期ロジック（部分約定の進展でのフィールド更新や、OrderSent→Filled のリカバリのため OrderAccepted を経由する補正など）。
    - cancel_order: キャンセル不可状態の検出と Broker への cancel 呼び出し、結果の永続化。
  - ExecutionEngine を実装（Signal Queue Pull 型発注エンジン）。機能の一部：
    - セッション制御（発注時間帯とプッシュドレインのタイミング: 8:50-9:10 発注、9:10-15:30 ドレイン）。
    - kill.flag の検出と KILL_FLAG_CLEAR_ON_START の扱い、PID ファイルの書き出し。
    - Gate 1 / Gate 2 / Gate 3 による多段リスクチェック（signal レベル検査、エグゼキューションレベル検査（レート制限, circuit breaker）、ポートフォリオドローダウン監視）。Gate 2 は最大リトライや CB 判定時のシグナルループ停止を行う。
    - 発注フローでの DuplicateOrderError の扱い、API レイテンシ計測、監視 DB へのログ（MonitoringDB が渡された場合）。
    - push（WebSocket）処理キューの実装と push による sync_order 呼び出し、push をトリガにした Gate 3 評価。
    - kill_switch 実装（全 active 注文キャンセルループと stop イベントセット）。
    - position_entries の書き込み（next_trading_day を使った fill_date 計算）および発注フロー継続時に発生する監視/DB 書き込み失敗の耐性。

- broker クライアント
  - KabuStationClient を実装（httpx 同期クライアント）。機能:
    - トークン取得（遅延初期化）と 401 発生時のトークン再取得・1 回リトライ。
    - HTTP タイムアウト / ネットワークエラーを BrokerAPIError に変換。
    - 429 を RateLimitError にマップ。
    - JSON パース失敗のエラー変換。
    - WebSocket push の受信（stream_push が存在する場合）と on_message コールバックを想定。
    - kabu ステーションの注文状態コードから内部ステータスへのマッピングを定義。

### 変更 (Changed)
- 発注フローの設計面でクラッシュ耐性を強化（OrderSent 永続化タイミングの明確化、broker_order_id の先コミット、Reconciliation を考慮した同期設計）。
- 実行・監視プロセス起動時はプロセス優先度を set_process_priority("high") で上げる処理を追加（起動直後に実行）。

### 修正 (Fixed)
- .env のパース挙動を改善し、クォートやエスケープ、コメントの扱いに関する曖昧さを解消。これにより .env 内の複雑な値（スペースや # を含む文字列など）を安全に扱えるようになった。
- MONITOR_POLL_INTERVAL の負の値や不正値に対してデフォルトにフォールバックする処理を追加（time.sleep に渡せない値を回避）。

### 注意事項 (Notes)
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ実行します。未インストール時は検証をスキップして警告を出力します。
- .env はセキュリティ上絶対に Git にコミットしないでください（config_setup のヘッダにも同様の注意書きあり）。
- 本番環境（KABUSYS_ENV=live）では、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定に注意してください。validate_config の警告を必ず確認してください。

---

（以降のリリースでは、変更点を同様にカテゴリ分けして記載します。）