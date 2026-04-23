# Changelog

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-23

### Added（追加）
- 設定検証 CLI: `kabusys.validate_config` モジュールを追加。
  - .env と config/*.yaml の存在・基本整合性を起動前に検出。
  - --strict オプションで警告を FAIL（exit(1)）扱いにできる。
  - 必須環境変数の未設定チェック、プレースホルダ値チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、PyYAML がない場合の YAML 検証スキップ等を実装。
  - KABUSYS_ENV=live のときに追加のガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）を実行。

- 環境設定ウィザード CLI: `kabusys.config_setup` を追加。
  - 対話式で .env を初期作成/更新するウィザード。
  - シークレット値は表示時にマスク、選択肢・デフォルト表示、既存値の読み込み、キャンセル時の挙動を実装。
  - .env 書き込みテンプレート（コメント付き）を生成。

- 環境変数/設定管理: `kabusys.config.Settings` と自動ロード機能を追加。
  - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env のパーサは export 形式対応、クォート文字内のエスケープ処理、インラインコメント処理等をサポート。
  - .env 読み込み時の override/protected（OS 環境変数の保護）挙動を実装。
  - 各種プロパティを提供（J-Quants トークン、kabu API パスワード、DB パス、paper_trading 用 SQLite パス、PID/kill flag パス、閾値、env/log_level の厳密チェックなど）。

- 実行系と監視のエントリスクリプトを追加:
  - `kabusys.run_execution` — ExecutionEngine の起動スクリプト（プロセス優先度設定、PID/stop フラグ、DB 接続、paper_trading 時の DB 分離など）。
  - `kabusys.run_monitoring` — SystemMonitor のポーリングループ用スクリプト（MONITOR_POLL_INTERVAL で間隔指定、監視は常に本番 sqlite_path を使用）。

- 発注周りのコアロジックを追加（execution パッケージ）:
  - OrderRecord（状態機械モデル）: 状態列挙 OrderState、許可遷移定義、InvalidStateTransitionError、transition_to メソッド（更新時刻の自動更新、オプションフィールド更新）を実装。
  - OrderManager: create/send/sync/cancel の外向け API を実装。DuplicateOrder のチェック、2相永続化を意識した send_order のフロー、OrderSentPending の取扱い、sync_order による broker 照合ロジック等を実装。
  - OrderRepository（呼び出し元で使用）と組み合わせる設計。
  - ExecutionEngine: シグナル処理（8:50–9:10）と push ドレイン（9:10–15:30）を含むセッション実行フロー。Gate1/2/3 によるリスクチェック、kill_switch による全 active 注文キャンセル、WebSocket push の受信→同期処理、position_entries への書き込み、監視 DB へのイベント記録連携などを実装。

- ブローカークライアント: `kabusys.execution.kabu_client.KabuStationClient` を追加。
  - httpx を用いた同期 REST クライアント。
  - トークン取得の遅延初期化・401 リトライ機構、HTTP エラーやタイムアウトを BrokerAPIError / RateLimitError 等に変換。
  - JSON パース失敗のハンドリング。
  - WebSocket(push) を受けるための流れ（stream_push を持つ broker に依存）に対応するための基盤を提供。

- 監視 DB 初期化 / SystemMonitor 等の連携コード追加（run_monitoring/run_execution から利用）。

### Changed（変更）
- .env パース挙動の強化:
  - クォート内のエスケープ解釈や export プレフィックス対応、インラインコメントの扱いなどをより現実の .env スタイルに近づけている。

- Settings の挙動:
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の無効値に対して ValueError を投げるようにして入力検証を厳格化。
  - auto-load の挙動説明を追加（OS 環境変数優先、.env.local は override する）。

- 実行スクリプト共通動作:
  - プロセス優先度の設定（set_process_priority("high")）を起動時に適用。
  - PID ファイルの生成/削除、stop_requested.flag による外部停止検出の標準化。

### Fixed（修正）
- DB/発注フローのクラッシュ耐性向上:
  - send_order における「OrderSent」を先に永続化してから broker 呼び出しを行い、broker_order_id を受け取ったら先に保存するなど、クラッシュ時に状態を復旧しやすくする 2 相的永続化パターンを採用。
  - sync_order により broker_order_id だけが残ったケースや OrderSent のまま残るケースを reconciliation により回復可能にする。

### Security（セキュリティ）
- config_setup の設定表示でシークレット値をマスク表示（"****"）。.env ファイルに関する注意書きを出力（.env は絶対に Git にコミットしないことを明記）。

### Notes（補足）
- 本リリースでは多くの主要コンポーネント（設定管理、対話式ウィザード、設定検証、監視／実行エントリ、発注ロジック、kabu API クライアント）を導入しました。以降のリリースで各コンポーネントの細部（エラーハンドリングの追加の粒度、ユニットテスト、ドキュメント強化、非同期対応など）を継続的に改善予定です。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config 実行後は警告・エラー内容に従って設定を見直してください（--strict を CI 等に使うと警告でも失敗にできます）。

（初回リリース: バージョン 0.1.0）