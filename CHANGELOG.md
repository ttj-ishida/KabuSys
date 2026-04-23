# CHANGELOG

すべての重要な変更をここに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

すべての頻繁に変更されるプロジェクトに対して、利用者が変更点を素早く把握できるようにまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-23

### 追加 (Added)
- プロジェクト初回リリースとして、KabuSys のコア機能を実装・公開。
- 設定管理
  - Settings クラスを追加し、環境変数からアプリケーション設定を取得する API を提供（settings インスタンス）。
  - .env の自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を探索）。OS 環境変数は保護して上書きを制御可能（.env / .env.local の読み込み順: OS > .env.local > .env）。
  - 環境変数パーサを実装。export 形式の行、シングル／ダブルクォート内のエスケープ、行内コメント扱いなどを正しく処理。
  - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の妥当性チェックを Settings 側で実装（不正値は ValueError）。
- 設定ウィザード（CLI）
  - config_setup モジュールを追加。.env を対話式に作成／更新するウィザードを提供。
  - デフォルト値・選択肢・シークレットマスク・説明文付きで操作可能。生成される .env のテンプレートは Git へコミットしない旨を明記。
- 設定検証（CLI）
  - validate_config モジュールを追加。.env と config/*.yaml の設定不備を起動前に検出する CLI を提供。
  - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証。
  - --strict オプションを追加（警告があっても exit(1) で失敗扱い）。
  - KABUSYS_ENV=live のときの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
- 実行スクリプト
  - run_execution と run_monitoring のエントリスクリプトを追加。両者ともプロセス優先度を設定するユーティリティ呼び出しとログ設定を行う。
  - run_execution:
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db のデフォルト）を使用して本番 DB と分離。
    - ExecutionEngine を起動し、PID／停止フラグ管理を行う。
  - run_monitoring:
    - 監視プロセスは環境にかかわらず本番 sqlite_path を使用する設計。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告後デフォルトにフォールバック）。
- 注文周りのコアロジック
  - OrderRecord（状態機械）を実装。許可される状態遷移を定義し、不正遷移は InvalidStateTransitionError を raise。
  - OrderManager を実装し、OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせた外向け API を提供（create/send/sync/cancel）。
  - send_order においてクラッシュ耐性を考慮した二相的永続化戦略を導入（OrderSent を永続化 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted へ遷移）。
  - OrderSentPendingError（注文番号は発行されたが約定しないケース）を扱い、pending 状態を DB に保持して呼び出し元へ伝播。
  - DuplicateOrder チェック（signal_id に対するアクティブ注文の重複防止）を実装。DB の部分ユニーク制約違反を DuplicateOrderError に変換。
  - sync_order により broker 側の状態を照会してローカル状態を同期。部分約定進行時は差分更新を行う。
  - cancel_order はキャンセル不可能な状態をチェックして適切に扱う。
- ExecutionEngine（発注エンジン）
  - Signal Queue Pull 型の発注エンジンを実装。8:50-9:10 のシグナル処理と 9:10-15:30 の push ドレインを想定したセッション管理を行う。
  - Gate ベースのリスク検査（Gate1: シグナル、Gate2: 実行レート制限、Gate3: ドローダウン監視）を組み込み、NG の場合はログと kill_switch を発動。
  - kill_switch を実装し、全アクティブ注文のキャンセルを試行。外部からの停止時にも安全に停止可能。
  - WebSocket push（kabu push）を受け取り _push_queue に投入、ドレイン時に sync_order を呼び出す処理を実装。stream_push 未実装の broker はスキップして警告表示。
  - 発注後に position_entries を DuckDB に書き込み（BUY はエントリー、SELL は売却日更新。pending の扱いの違いあり）。
  - 発注時の API レイテンシを監視 DB に記録するフックを追加（監視 DB が指定されている場合）。
- ブローカークライアント
  - KabuStationClient を追加（httpx クライアントを使用する同期実装）。
  - API トークン遅延初期化と 401 時の自動再取得・1 回リトライを実装。
  - HTTP タイムアウト・ネットワークエラーを BrokerAPIError に変換、429 を RateLimitError に変換、レスポンスの JSON パース失敗は BrokerAPIError に変換。
  - 将来的な非同期化を見据えて設計（httpx.AsyncClient に差し替えることで対応可能）。
- 監視 DB 初期化ユーティリティ（init_monitoring_db）呼び出しを各スクリプトで行い、監視テーブルの存在を保証。

### 変更 (Changed)
- なし（初回リリースのため、既存機能の「変更」はありません）。

### 修正 (Fixed)
- 送信フローのクラッシュシナリオを考慮し、OrderSent と broker_order_id の保存順序を明示してリコンシリエーションで回復可能に（Issue 想定の回避）。
- MONITOR_POLL_INTERVAL に不正な値が設定された場合、time.sleep に渡して例外となるのを防ぐため無効値を検出してデフォルトにフォールバックする動作を追加。
- .env 読み込みでファイルオープンに失敗した場合に警告を出すよう改善（読み込み失敗の詳細を warnings.warn で通知）。

### 既知の制限 (Known issues)
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行われる（未インストール時は検証をスキップして警告）。
- KabuStationClient は現状同期実装のため、大量同時リクエストや高スループットへの対応は非同期化が必要。
- 一部の外部依存（kabu ステーションの稼働、外部 API の応答形式）に対する詳細な互換性テストは今後継続して行う必要あり。

---

リリースに含まれる主要なファイル:
- src/kabusys/config.py, config_setup.py, validate_config.py
- src/kabusys/run_execution.py, run_monitoring.py
- src/kabusys/execution/*.py（order_record.py, order_manager.py, execution_engine.py, kabu_client.py 等）
- src/kabusys/__init__.py（バージョン: 0.1.0）

今後の予定:
- テストカバレッジの拡充（特にクラッシュ/リコンシリエーション周り）
- KabuStationClient の async 化オプション追加
- config/*.yaml のスキーマ検証導入（PyYAML と jsonschema 等の組合せ検討）