# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0 - 2026-04-23

## [0.1.0] - 2026-04-23

### 追加 (Added)
- Settings クラスによる集中設定管理を追加。
  - 環境変数から値を取得するプロパティ群を提供（J-Quants, kabu API, LINE, DB パス, paper_trading 用設定, 監視閾値等）。
  - settings = Settings() をモジュールレベルで公開。
- .env の自動ロード機能を追加。
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動的に読み込み。OS 環境変数は保護され上書きされない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- 対話式環境設定ウィザード (kabusys.config_setup) を追加。
  - .env の新規作成／更新を支援する対話 UI。
  - シークレット項目のマスク表示、選択肢・デフォルト提示、既存 .env 読み込みをサポート。
  - .env を書き出すテンプレート（コメント付き）を生成。
- 設定検証ツール (kabusys.validate_config) を追加。
  - .env と config/*.yaml の存在・基本妥当性チェックを行う CLI。--strict オプションで警告も失敗扱いに可能。
  - PyYAML があれば YAML のパース検証も実施。
  - 環境変数のプレースホルダ検出（例: 値が "your_value" や "_here" で終わる場合）や重要な必須変数の未設定検出。
- 実行用スクリプトを追加。
  - run_execution.py: ExecutionEngine を起動するエントリポイント（paper_trading 環境での DB 分離をサポート）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL による間隔上書きをサポート）。
- KabuStationClient（kabu_client）を追加。
  - httpx を使った同期 REST クライアント。トークン取得の遅延初期化と 401 リトライを実装。
  - 429 の場合は RateLimitError を返す等、HTTP ステータスに基づく例外処理を実装。
- ExecutionEngine を追加（signal-queue ベースの発注エンジン）。
  - シグナル処理ループ、push ドレインループ、WebSocket ワーカー連携、PID/kill_flag 管理、kill_switch 実装を含む。
- OrderRecord（状態遷移ロジック）を追加。
  - 明示的な状態列挙、許可トランジションセット、transition_to による遷移検証。
- OrderManager を追加。
  - 注文の作成・送信・同期・キャンセルの高レベル API を提供。DB 制約や broker API の失敗形態に対応する堅牢なフローを実装（クラッシュ安全性を考慮した二相永続化など）。
  - DuplicateOrderError、OrderSentPendingError 等のハンドリング。
- 実行コンポーネント（BrokerFactory, RiskManager, Reconciler, OrderRepository 等）と監視 DB 初期化ユーティリティを追加（各モジュールの組み立てを含む）。

### 変更 (Changed)
- 監視プロセス（run_monitoring）は KABUSYS_ENV に関係なく本番用の sqlite_path を使用するように設計。
- .env パーサーの挙動を詳細化:
  - export KEY=val 形式に対応。
  - クォートありの値に対してバックスラッシュエスケープを解釈し、閉じクォートまでを正しく抽出するよう実装。
  - クォートなし値では '#' の直前が空白・タブの場合にのみコメントとして扱うことでインラインコメントの誤解釈を低減。
- Settings の値検証を厳格化:
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE などの許容値チェックを実装し、不正値は ValueError を送出。
- run_execution の DB 接続ロジック:
  - paper_trading 環境時は paper_sqlite_path を用いて本番 DB と完全分離するよう変更。
- OrderManager.send_order の発注フローを詳細化:
  - OrderSent に遷移してから broker API 呼び出しを行う二相永続化設計を採用し、クラッシュ時の復旧容易性を高めた。
  - broker_order_id を先に永続化し、その後 Accepted 等へ遷移することで Reconciliation が ID を手掛かりに状態回復できる。
- ExecutionEngine の発注ロジック:
  - Gate チェック（Gate1: シグナル単位、Gate2: レート制限・回路遮断、Gate3: ポートフォリオ指標）を実装し、NG 時の挙動（スキップ／kill_switch）を明確化。
  - BUY のみ size_multiplier を適用し、100 株単位で切り捨てる処理を導入。
  - 発注時の監視 DB ログ記録を追加（latency_ms 等）。
- kill_flag の起動時挙動:
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START が 1 なら自動クリアして起動、そうでなければ起動を拒否するロジックを追加。

### 修正 (Fixed)
- OrderRepository への保存中に発生する sqlite3.IntegrityError を部分的に解釈し、signal_id のユニーク制約違反は DuplicateOrderError に変換して扱うようにした（その他の制約違反はそのまま再スロー）。
- sync_order のロジックを堅牢化:
  - broker が返す同一状態でも filled_qty / avg_fill_price の変化を検出して更新する。
  - OrderSent → Filled/PartialFill のように直接遷移できないケースは一旦 OrderAccepted を経由して遷移させる処理を追加（ネットワーク障害後の Reconciliation 対応）。
- WebSocket push のハンドリングを改善:
  - Push に含まれる注文 ID から client_order_id を検索し sync_order を実行するフローを追加。見つからない場合でも Gate3 を評価してドローダウン監視を実行するようにした（spurious push への耐性向上）。
- MONITOR_POLL_INTERVAL のパースを改善:
  - 0 以下や不正値はデフォルト（60 秒）にフォールバックし、警告を出力するようにした。

### 削除 (Removed)
- 該当なし（初期リリースのため削除はなし）。

### セキュリティ (Security)
- API トークン取得と認証失敗時の再取得処理を実装し、401 応答時の再試行を行うことで一時的なトークン切れへの耐性を向上。

---

注記:
- この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。