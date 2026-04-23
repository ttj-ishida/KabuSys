CHANGELOG
=========

すべての注目すべき変更点を時系列で記録します。これは "Keep a Changelog" の形式に準拠しています。

注: 以下の履歴は提示されたコードベースから推測して作成したものです。実際のコミット粒度や日付とは異なる場合があります。

## [Unreleased]

### 追加予定
- 軽微なドキュメント整備やテストの追加
- Broker クライアント群の追加実装（現状は kabu station 実装が中心）
- 監視・メトリクス周りの強化（アラートやダッシュボード連携）

---

## [0.1.0] - 2026-04-23

初期リリース。日本株自動売買システム「KabuSys」の基盤的機能を実装しました。

### 追加
- CLI / 設定管理
  - config_setup: 対話式 .env 作成ウィザードを実装。多くの設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、データベースパス、LINE トークン、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）をサポート。
  - validate_config: 起動前チェック用 CLI を実装。必須環境変数の存在チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性検証、データベースパスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証を行う。--strict オプションで警告を FAIL 扱いにできる。
  - .env の自動ロード: プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env/.env.local を自動で読み込む（OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- 環境変数パーサー / 設定オブジェクト
  - .env 行パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応を実装。
  - Settings クラスによりアプリケーション設定をプロパティ経由で提供。型変換・既定値・バリデーションを実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。未設定必須値は ValueError を送出。

- 実行エントリ（スクリプト）
  - run_execution: ExecutionEngine 起動スクリプトを実装。プロセス優先度設定、PID ファイル管理、kill.flag による起動制御、paper_trading モード時の専用 SQLite DB 使用などをサポート。
  - run_monitoring: SystemMonitor ポーリングループの起動スクリプトを実装。MONITOR_POLL_INTERVAL によるポーリング間隔設定、常に本番用 sqlite_path を使用する仕様。

- 発注エンジン / 注文ライフサイクル
  - ExecutionEngine: シグナル処理（signal queue pull モデル）と WebSocket push ドレインループを実装。セッション時間（デフォルト 8:50–9:10 発注、9:10–15:30 ドレイン）をサポート。kill_switch、PID ファイル管理、WebSocket スレッド、push キュー処理、position_entries の DuckDB 書き込み等を実装。
  - EngineConfig により target_date 等を設定可能。
  - OrderRecord: 注文状態マシン（OrderState）を実装。許容遷移テーブルと transition_to による遷移検証、updated_at の自動更新、オプションフィールド更新を実装。InvalidStateTransitionError を定義。
  - OrderManager: 高レベルの発注 API を提供（create_order、send_order、sync_order、cancel_order）。重複注文検出（signal_id ベース）、SQLite の整合性違反からの DuplicateOrderError 変換、送信の「2 相永続化」（OrderSent 前に永続化 → broker 呼出し → broker_order_id 永続化 → OrderAccepted に遷移）によるクラッシュ時回復性向上、OrderSentPendingError の取り扱い、Reconciliation を考慮した実装。

- ブローカー API / kabu station クライアント
  - KabuStationClient: httpx を用いた kabu station REST API クライアントを実装。トークン取得（遅延初期化）、401 時の自動トークン再取得とリトライ、HTTP ステータスに基づく例外 (RateLimitError, BrokerAPIError 等) マッピング、JSON パース例外の変換、WebSocket push（stream_push）を想定した設計を実装。
  - API 応答の状態コードを内部状態 ("open","partial","filled","cancelled","rejected") にマッピングするロジックを導入。

- リスク管理・Gate（実行前検査）
  - ExecutionEngine 側で Gate 1（シグナルレベル）、Gate 2（実行レベル：レート制限・サーキットブレーカー）、Gate 3（ポートフォリオメトリクス・ドローダウン監視）を通じた発注ガードを実装。Gate 2 はリトライロジック、Circuit Breaker 判定でシグナルループ停止を可能にする設計。
  - Gate 3 NG 時に kill_switch を発動して全 active 注文をキャンセルする処理を実装。

- 監視 / メトリクス
  - monitoring_db 初期化ユーティリティを使用した監視 DB セットアップ。ExecutionEngine から発注イベント（Sent 等）を監視 DB に記録するフックを実装（監視 DB 書き込み失敗時はログ出力でフォールバック）。

- データベース連携
  - DuckDB を利用してシグナル・portfolio_targets からシグナル抽出や position_entries の管理を行う実装。
  - paper_trading 用の sqlite（PAPER_TRADING_SQLITE_PATH）を本番 DB から分離して利用可能に。

- ユーティリティ統合
  - setup_logging、set_process_priority などのユーティリティ呼び出しを組み込み、プロセス優先度・ログ初期化を標準化。

### 変更（設計上の改善 / 安全性向上）
- 発注処理の耐障害性を改善
  - send_order の永続化順序を工夫し、途中クラッシュした場合でも broker_order_id が残れば Reconciliation で回復可能に。
  - OrderSentPendingError の明確な扱いにより、pending ケースを Reconciliation の対象として扱う。
- .env パーサーの堅牢化
  - クォート内のエスケープ、export プレフィックス、コメント扱いの改善により幅広い .env 記述をサポート。
- 設定バリデーションを厳格化
  - Settings プロパティによる早期検出（無効な KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE は ValueError）。

### 修正（バグ修正 / 想定問題対応）
- config/*.yaml の検証は PyYAML が存在しない環境ではスキップし、適切に警告を出すように変更（YAML の未導入環境でも CLI が致命的に停止しないように対応）。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値（0 以下や文字列）に対して警告を出し、デフォルト値へフォールバックするように修正。

### 注意事項 / 既知の制約
- KabuStationClient は同期 httpx.Client を使用しており、将来的に非同期化（httpx.AsyncClient）へ移行可能な設計を想定しているが現状は同期実装。
- .env はセキュリティ上 Git にコミットしないことを README 等で周知する必要あり（config_setup はその旨を .env ファイルヘッダに記載）。
- 一部のユーティリティ（setup_logging, set_process_priority, monitoring_db 初期化等）は別ファイルで提供される前提（present code はそれらを import して利用）。

---

メンテナ向け追記
- バージョン番号はパッケージ __init__.py の __version__ = "0.1.0" に基づく。
- 今後のリリースでは機能別に細かく分割した CHANGELOG を作成することを推奨します（例: Execution Engine の改良、Broker クライアントの追加、監視機能の拡張など）。