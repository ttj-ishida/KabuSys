CHANGELOG
==========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
重要な変更（Added / Changed / Fixed 等）を日本語で要約しています。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-22
------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基本機能を追加。
- 環境設定 / ロード
  - .env ファイルの自動読み込みを実装（プロジェクトルートの .git または pyproject.toml を基準に検索）。
  - .env の行パーサを実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント（特定条件）に対応。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - _load_env_file の override/protected 機能により OS 環境変数を保護しつつ .env/.env.local を適切に適用。

- 設定管理
  - Settings クラスを導入し、アプリケーション設定を型付きプロパティ経由で取得可能に。
  - 必須環境変数取得用の _require を実装（未設定時は ValueError）。
  - PAPER_FILL_MODE 等の追加設定・検証（有効値チェックを行い不正値は例外）。
  - 本番/検証/開発を表す KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証を組み込み。
  - DB パスや PID / kill flag 等のパス管理プロパティを提供。

- CLI ツール
  - config_setup: 対話式ウィザードで .env を作成/更新する CLI を追加。
    - 複数の項目定義（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、ログレベル、Kill Switch 挙動等）を含む。
    - 既存 .env 読み込み、シークレットマスク表示、選択肢・デフォルト提示、保存確認、.env の書き出しを実装。
  - validate_config: 起動前に .env と config/*.yaml の整合性をチェックする CLI を追加。
    - 必須/任意環境変数の存在チェック、プレースホルダ値検出、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB 親ディレクトリ存在チェック等を行う。
    - PyYAML 未インストール時は YAML 内容検証をスキップして警告を出す。
    - --strict オプションで警告も FAIL として exit(1) を返す。

- 実行/監視プロセス
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - paper_trading 環境時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - プロセス優先度を高く設定するユーティリティ呼び出し、ログ設定を行う。
    - 停止フラグ検出（data/stop_requested.flag）による優雅な終了処理と PID 管理を実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。

- Execution / 発注エンジン
  - ExecutionEngine を実装
    - シグナルの取得（DuckDB）→ Gate 1/2 のリスクチェック → 発注 → push ドレイン（Gate 3）というフローを実装。
    - シグナル処理時間帯（デフォルト 8:50–9:10）とセッション終了時刻（デフォルト 15:30）に基づく制御。
    - WebSocket push を受けて同期処理を行うワーカースレッド（broker が stream_push を提供する場合）。
    - PID ファイルの書き出し / 削除、kill.flag の存在チェックと KILL_FLAG_CLEAR_ON_START の挙動を実装。
    - 発注後に position_entries を DuckDB に書き込む処理（BUY/Sell の扱いの違い、pending の扱い）を追加。
    - 発注時のレート制限リトライ、Circuit Breaker 検出時の挙動、API レイテンシ記録と監視 DB へのロギングを実装。
    - kill_switch による全 active 注文のキャンセル処理を実装（外部停止 alias stop()）。

- 注文管理
  - OrderRecord: 注文状態マシン（OrderState）と状態遷移の検証を実装（InvalidStateTransitionError を投げる）。
    - 状態遷移テーブル（許可される遷移）を定義。
    - transition_to による updated_at 自動更新とオプションフィールド更新。
  - OrderManager: DB（OrderRepository）と OrderRecord を組み合わせた外向き API を実装。
    - create_order: signal_id の重複検知（DB 部分ユニーク制約違反を DuplicateOrderError に変換）。
    - send_order: クラッシュ安全性を考慮した 2 相永続化戦略（OrderSent を先にコミット、broker_order_id を保存 → OrderAccepted 更新など）。
      - OrderRejectedError, OrderSentPendingError の扱いを明確化（pending 時は broker_order_id を残して例外伝播）。
    - sync_order: broker の最新状態と同期し、必要に応じて状態遷移・フィールド更新を行う（Filled などへの直接遷移不可を補正）。
    - cancel_order: キャンセル不可状態のチェック、broker cancel 呼び出し、Cancelled への遷移を実装。

- Broker (kabu station) クライアント
  - KabuStationClient を実装（同期 httpx ベース）。
    - トークン取得の遅延初期化、自動再取得（401 時 1 回リトライ）を実装。
    - レスポンス JSON パース失敗やタイムアウト/ネットワークエラーを BrokerAPIError に変換。
    - ステータスコード 429 は RateLimitError にマップし、5xx はサーバーエラーとして扱う。
    - 内部で kabu の注文状態コードを内部ステータス ("open"/"partial"/"filled"/...) にマッピング。

- 監視 / DB 初期化
  - monitoring_db.init_monitoring_db 呼び出しにより SQLite 側の監視テーブルを起動時に冪等に初期化する仕組みを導入。
  - 監視ループや発注フローから監視 DB へイベントを記録するポイントを追加。

Changed
- なし（初回リリースのため特記なし）

Fixed
- なし（初回リリースのため特記なし）

Notes / 注意事項
- .env は絶対に Git にコミットしないこと（config_setup のヘッダにも注意書きあり）。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップし警告を出します。YAML の構文チェックを有効にするには PyYAML をインストールしてください。
- ExecutionEngine と Monitoring はそれぞれ別プロセスとして運用することを想定しています。paper_trading 時の DB 分離（paper_trading 用 SQLite）により実運用データとテストデータが混ざらないように注意してください。
- kill.flag の残留により起動が拒否されることがあります。KILL_FLAG_CLEAR_ON_START を 1 に設定すると自動クリアして起動しますが、本番では 0 を推奨します。

---

今後の予定（例）
- 非同期 httpx.AsyncClient への移行検討（KabuStationClient の async 対応）。
- より詳細な監視メトリクスとアラート連携（LINE 通知等）の強化。
- OrderRepository / Broker API の詳細なテストケース追加。