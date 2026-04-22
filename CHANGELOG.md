CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" のスタイルに準拠します。

Unreleased
----------
- なし

0.1.0 - 2026-04-22
------------------
初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装しました。

Added
- 環境設定 / ロード関連
  - Settings クラスを追加。環境変数から各種設定（API トークン・DB パス・監視閾値・PID / kill flag パス 等）を取得・検証するプロパティを提供。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサー実装: export プレフィックス対応、クォート文字（シングル/ダブル）とバックスラッシュエスケープ、インラインコメント処理に対応。
  - _load_env_file に override / protected オプションを実装し、OS 環境変数を保護しつつ .env.local による上書きを可能に。

- 設定ウィザード
  - config_setup CLI を追加。対話式で .env を初期作成 / 更新するウィザードを提供。
  - 標準的な設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 設定など）を用意。
  - .env の読み書きロジックとテンプレート出力、シークレット項目の表示マスク、保存前確認を実装。
  - .env ファイルの生成後に validate_config での検証を促すメッセージを追加。

- 設定検証 CLI
  - validate_config CLI を追加。環境変数と config/*.yaml の不足や不整合を起動前に検出するコマンドを実装。
  - 必須 / 任意環境変数チェック、KABUSYS_ENV の許容値チェック、LOG_LEVEL の妥当性チェック、DB パス（親ディレクトリ存在）チェック、config/*.yaml 存在と YAML パース検証（PyYAML 未インストール時はスキップ）などを実施。
  - --strict オプションを実装（警告を FAIL として exit(1)）。
  - プレースホルダ値（*_here, your_value）検出で警告を出力。
  - live 環境向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。

- 実行 / 監視スクリプト
  - run_execution と run_monitoring を追加。各々 ExecutionEngine / SystemMonitor の起動、DB 接続、プロセス優先度設定、PID / 停止フラグの扱いを行う起動スクリプトを提供。
  - MONITOR_POLL_INTERVAL 環境変数による監視ポーリング間隔の上書き（デフォルト 60 秒）を実装。値不正時はデフォルトにフォールバックして警告。
  - 監視は KABUSYS_ENV にかかわらず "本番" sqlite_path を使用する旨を明記。実行は停止フラグ検出で安全に終了し、DB 接続をクローズする。

- Execution エンジン・発注フロー
  - ExecutionEngine を実装。シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を扱うセッション駆動の発注ループを提供。
  - EngineConfig で target_date / 時間帯を指定可能。
  - シグナル取得は DuckDB を利用し、portfolio_targets と結合して発注数量・価格を決定。
  - size_multiplier の適用（BUY のみ）や 100 株単位切り捨て等のロジックを実装。
  - Gate1（シグナルレベル）/ Gate2（エグゼキューションレベル、レート制限・サーキットブレーカー）/ Gate3（ドローダウン監視）のリスクゲートを実装し、Gate2 はリトライ（最大 3 回）や CB オープン時の動作を考慮。
  - kill_switch の実装: 全ループ停止と全 active 注文のキャンセル（リトライ・例外ハンドリング含む）。
  - WebSocket push を受ける worker を実装。broker が stream_push を持たない場合はスキップする。

- 注文モデル & 注文管理
  - OrderRecord と OrderState（状態機械）を実装。許可される状態遷移を列挙し、不正遷移は InvalidStateTransitionError を送出。
  - OrderManager を実装し、create_order / send_order / sync_order / cancel_order を提供。
  - send_order ではクラッシュ耐性を考えた段階的永続化フローを採用（OrderCreated → OrderSent を先に永続化、broker 呼び出し後に broker_order_id を保存し、その後 OrderAccepted に遷移して保存する等）。OrderSent 状態のままクラッシュしたケースに対するリコンシリエーション設計を反映。
  - OrderSentPendingError を扱い、broker_order_id を保存して OrderSent のまま残す動作を実装（後続でリコンシリエーション対象とする）。
  - DuplicateOrderError を導入し、同一 signal_id の active 注文重複を防止。DB の部分ユニークインデックス違反を DuplicateOrderError に変換。
  - sync_order は broker のステータス取得に基づき、状態遷移（必要に応じて OrderAccepted を経由）や filled_qty / avg_fill_price の更新を行う。見つからない（None）応答は無処理。
  - cancel_order は終端状態ではキャンセル不可として InvalidStateTransitionError を返し、broker_order_id が存在すれば broker 側キャンセル API を呼ぶ。

- Broker / KabuStation クライアント
  - KabuStationClient を実装（httpx クライアント使用、同期 API）。
  - トークン取得ロジックを内蔵し、401 時はトークン再取得して 1 回リトライする処理を実装。
  - JSON パース失敗やタイムアウト、ネットワークエラーを BrokerAPIError に変換。429 は RateLimitError として扱う。
  - kabu ステータスコードと内部ステータスのマッピングを定義（open/partial/filled/cancelled/rejected）。
  - WebSocket (push) は websocket ライブラリを使って別スレッドで受信し、ExecutionEngine の _push_queue に投入する想定（stream_push の存在検査あり）。

- データベース / 監視連携
  - DuckDB / SQLite 接続を利用。paper_trading モードでは paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を利用して監視テーブルを確保。
  - 発注後に position_entries を書き込むロジックを実装（fill_date は next_trading_day を使って当日翌営業日で記録、BUY pending も記録、SELL は pending でなければ売却日を入れる）。
  - 発注のメトリクス（Sent イベント・遅延 ms 等）を監視 DB に記録するフックを用意（監視 DB が与えられている場合）。

Changed
- ログ / プロセス制御
  - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを導入（run_execution / run_monitoring）。
  - setup_logging を呼び出してアプリ名ごとのログ設定を行う。

Fixed
- 環境変数 / 設定の堅牢化
  - PAPER_FILL_MODE の妥当性チェックを追加（有効値: instant / partial / never / reject）。不正値は ValueError。
  - Settings.env / log_level の不正値に対する ValueError を導入して早期検出。
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）時にデフォルトへフォールバックする挙動を実装。

Security
- .env に関する注意喚起を config_setup の出力に含め、.env を Git にコミットしないよう明示。

Notes / その他
- YAML 内容検証は PyYAML のインストール有無に依存。未インストール時は検証をスキップして警告を出す。
- 多くの外部依存（httpx, websocket, duckdb, PyYAML 等）に依存する箇所があるため、実運用前に依存パッケージの整備が必要。
- いくつかの動作（リコンシリエーション、監視 DB への書き込み、外部ブローカー API とのやり取り）は実際の外部環境によるため、十分なテストを推奨。

ライセンスや既知の制限、今後の改善点（例えば async 化、より詳細なエラーメトリクス、より多様なブローカ対応など）は別途ドキュメント化する予定です。