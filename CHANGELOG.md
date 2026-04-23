# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。

## [0.1.0] - 2026-04-23

初回リリース。KabuSys の基本的な設定管理、実行エンジン、発注フロー、監視、および関連ユーティリティを追加しました。

### 追加
- 全体
  - パッケージ初期バージョンを設定（__version__ = "0.1.0"）。
  - モジュール構成を追加（data, strategy, execution, monitoring 等の主要パッケージを公開）。

- 設定管理
  - 環境変数/設定読み込みモジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して自動で .env を読み込む仕組みを実装。
    - .env ファイルの読み込みは OS 環境変数が優先。`.env.local` による上書きや KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - export KEY=val 形式・クォート・エスケープ・インラインコメント等に対応した .env パーサを実装。
    - Settings クラスを提供し、各種設定（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、KABUSYS_ENV、各種閾値等）をプロパティ経由で取得可能に。
    - PAPER_FILL_MODE の妥当性チェックや env/log_level の検証などのバリデーションを実装。
    - paper_trading 環境用の専用 SQLite パスを提供（本番 DB と分離）。

  - 対話式設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を対話形式で支援。シークレットは表示をマスク。
    - 選択肢やデフォルト、説明文を用意し、.env を安全に生成するテンプレート書き出しを実装。
    - 書き込み時に .env を Git にコミットしない旨の注意を記載。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - .env および config/*.yaml の存在・基本整合性を起動前に検出。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定検出やプレースホルダ値の警告処理。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DUCKDB/SQLite のパス存在チェック（親ディレクトリの有無警告）等を実施。
    - PyYAML がインストールされていれば config/*.yaml をパースして構文エラーを検出（未インストール時はスキップして警告）。
    - KABUSYS_ENV=live のときの追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START=1 の危険設定等）を実装。
    - --strict オプションにより警告を FAIL（exit 1）として扱える。

- 実行/監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 環境に応じて paper_trading 用 DB を分離して使用。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出（data/stop_requested.flag）に対応。
  - Monitoring ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。

- 発注フロー（Execution）
  - OrderRecord（状態マシン）を追加（src/kabusys/execution/order_record.py）。
    - 注文状態（created, sent, accepted, partial, filled, closed, cancelled, rejected）を定義。
    - 許容される状態遷移テーブルを実装し、不正遷移時は InvalidStateTransitionError を発生。
    - 状態遷移時に updated_at を UTC で自動更新し、任意フィールド（broker_order_id、filled_qty、avg_fill_price、error_message）を更新可能。

  - OrderManager を追加（src/kabusys/execution/order_manager.py）。
    - signal_id に対する重複注文検出（DuplicateOrderError）と DB レベルの部分ユニーク制約扱いを実装。
    - send_order においてクラッシュ耐性を考慮した二相的永続化フローを実装（OrderSent を事前コミット → ブローカ呼び出し → broker_order_id を保存 → OrderAccepted へ遷移等）。
    - OrderRejectedError / OrderSentPendingError の取り扱いを実装し、pending 状態と永続化の扱いに対応。
    - sync_order で broker 側の状態を取得してローカル状態と同期、部分約定の進行は個別フィールド更新で対応。
    - cancel_order ではキャンセル不可能な状態を弾き、必要に応じてブローカ API を呼んで Cancelled に遷移。

  - ExecutionEngine 本体を追加（src/kabusys/execution/execution_engine.py）。
    - シグナル読み込み（DuckDB）→ Gate1（シグナルレベル）→ Gate2（エグゼキューションレート制御）→ 発注という流れを実装。
    - size_multiplier を考慮した数量調整（BUY のみ、100 株単位切り捨て）。
    - Gate2 のリトライ（最大3回）とサーキットブレーカー検出（開の場合はシグナルループ停止）。
    - 発注成功/失敗・pending の記録、API レイテンシを監視 DB にログ（監視 DB が渡された場合）。
    - position_entries テーブルへのエントリ記録（約定日を次の営業日に設定）を実装（DuckDB 操作）。
    - WebSocket からの push を受けて _push_queue をドレイン、push による sync_order と Gate3（ポートフォリオドローダウン監視）を実装。
    - Gate3 NG の場合は kill_switch を発動し、全 active 注文のキャンセルを実行。
    - kill.flag の存在チェックと KILL_FLAG_CLEAR_ON_START 設定に基づく起動拒否/自動クリアを実装。
    - PID ファイルの書き込み/削除を実装。

  - k abu station REST クライアントを追加（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期クライアント実装（トークン取得・自動再取得、401 リトライ処理）。
    - レスポンスコードに応じた例外マッピング（401/429/5xx など）と JSON パースエラーの変換。
    - WebSocket push（stream_push）を利用する場合の受信ハンドリングに対応（optional）。

- リコンシリエーション / リスク管理 / ブローカー抽象
  - BrokerClientFactory / Reconciler / RiskManager 等のコンポーネントを統合するための呼び出し点を実装（各コンポーネントは別ファイルで定義）。

### 変更
- なし（初回リリース）

### 修正
- 追加時に堅牢性を重視した実装を多数含む:
  - 発注フローにおけるクラッシュ時の状態復元（OrderSent->broker_order_id 永続化等）や、sync/reconcile での復旧手順を明文化。
  - .env パーサのクォート/エスケープ/コメント処理を改善して実運用での誤設定を減らす。

### 非互換（BREAKING CHANGES）
- なし（初回リリース）

### セキュリティ
- なし（特記事項なし）

---

今後の予定（例）
- broker API のエラー詳細ハンドリングの強化
- async 対応（httpx.AsyncClient への移行）
- 監視メトリクスの可視化機能追加

（この CHANGELOG はコードベースから推測して自動生成しています。必要に応じてリリース日や詳細を編集してください。）