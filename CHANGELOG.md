# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルは、コードベースから推測される変更点・追加機能を基に作成しています。

現在: Unreleased

---

## [Unreleased]

### Added
- 設定検証用 CLI (kabusys.validate_config)
  - .env および config/*.yaml の有無や基本的な値チェックを行う。
  - `--strict` オプションで警告を FAIL（exit 1）として扱う。
  - 必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ確認、YAML パース（PyYAML が存在する場合）などを検査。
  - KABUSYS_ENV=live の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。

- 環境設定ウィザード CLI (kabusys.config_setup)
  - 対話式に .env を作成・更新するウィザードを提供。
  - 必須/任意/シークレット項目や選択肢を定義済み（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）。
  - 既存 .env 読み込み、入力キャンセル時の取り扱い、確認表示、ファイル保存を実装。
  - 書き出しテンプレートに注意書き（.env をコミットしない等）を追加。

- 環境設定読み込み/管理モジュール (kabusys.config)
  - プロジェクトルートの検出ロジック（.git または pyproject.toml を探索）に基づく自動 .env ロードを実装（無効化フラグあり）。
  - .env のパースを強化:
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォートのエスケープ処理対応
    - クォート無の場合のインラインコメント検出ロジック
  - .env ロード順序: OS 環境 > .env > .env.local（.env.local は上書き）。
  - 保護された OS 環境変数を考慮した上書き（protected 機構）。
  - Settings クラスを導入し、環境値をプロパティ経由で取得・検証できるように（env/log_level/PAPER_FILL_MODE 等の検証含む）。
  - paper_trading 向け DB パスや kill flag 関連設定など、運用向けプロパティを提供。

- 実行スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - paper_trading 時に専用 SQLite DB を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検知、kill flag のクリア制御を実装。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は常に本番 sqlite_path を使用する設計。

- 発注/実行コンポーネント
  - OrderRecord（状態機械のデータモデル）を導入:
    - 明示的な OrderState 列挙と許可遷移マップを定義。
    - 不正遷移時に InvalidStateTransitionError を送出。
    - broker_order_id / filled_qty / avg_fill_price / error_message の更新ロジック。
  - OrderManager を追加:
    - create_order / send_order / sync_order / cancel_order の外側 API を提供。
    - 同一 signal_id の重複注文検出（DuplicateOrderError）。
    - send_order におけるクラッシュ耐性を考慮した永続化順序（OrderSent を先に永続化、broker_order_id を先に記録してから Accepted へ遷移）を実装。
    - OrderRejectedError / OrderSentPendingError 等の細かな取り扱い。
    - sync_order による broker 状態同期（同一状態でも部分約定情報のみ更新する挙動を明記）。
    - cancel_order のキャンセル可否チェック（終端状態は不可）と broker cancel 呼び出し。

  - ExecutionEngine（Signal Queue 型発注エンジン）
    - シグナル処理ループ（8:50–9:10）と WebSocket push ドレインループ（9:10–15:30）を実装。
    - Gate1/2/3 によるリスクチェック、レート制限リトライ、Circuit Breaker の扱いを実装。
    - size_multiplier 適用（BUY のみ）や発注後の position_entries への記録（duckdb への書き込み）を実装。
    - WebSocket (push) の受け取りを _push_queue 経由で処理し、push ごとに sync と Gate3 検査を行う。
    - kill_switch を実装し、全 active 注文のキャンセルを行う（外部停止 API として stop() を公開）。
    - セッション開始時に Reconciliation を実行する仕組み（reconciler をオプションで受け取り実行）。

- ブローカークライアント実装
  - KabuStationClient を実装（httpx を使用した同期 REST クライアント）。
    - トークン取得を内部で行い、401 時の再取得と 1 回のリトライに対応。
    - JSON パース失敗やネットワーク例外を BrokerAPIError に変換。
    - 429（レート制限）や 5xx を判定して固有例外を送出する設計。
    - websocket/stream_push を利用した push 処理をサポートする設計（stream_push を持たない broker の場合はスキップ）。

- DB / 監視
  - monitoring_db 初期化ヘルパー（init_monitoring_db）を呼び出して監視用テーブルの存在を保証。
  - 発注時の監視イベントを monitoring DB に記録するフック（latency_ms や状態情報をログ）を追加（監視 DB が提供される場合）。

### Changed
- 環境変数/設定の検証ロジックを強化（Settings クラスのバリデーションと validate_config CLI が整合）。
- .env 処理の堅牢化により、配布後やテスト実行時の環境依存性を低減。

### Fixed
- send_order の永続化順序や OrderSentPending ケースの扱いを明確化し、クラッシュ時の復旧（Reconciliation）可能性を向上。

---

## [0.1.0] - 2026-04-23

初回公開リリース。上記 Unreleased に列挙されている主要機能を含む最初の安定バージョン。

### Added
- パッケージ初期バージョンとして以下を提供:
  - 環境設定管理（.env 自動読み込み、堅牢なパース）
  - 設定ウィザード CLI（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - 実行スクリプト（run_execution, run_monitoring）
  - ExecutionEngine、OrderManager、OrderRecord 等の発注実行基盤
  - KabuStationClient（kabu station REST API クライアント）
  - 監視 DB 連携、duckdb / sqlite を用いたデータ操作基盤

### Changed
- 初期公開にあたり内部 API と構成を整理（Settings による中央集権的設定取得など）。

### Fixed
- 初期リリースとして運用上想定されるクラッシュ/再起動シナリオに対応する耐障害性向上（OrderSent 永続化戦略等）。

---

該当する変更点に不明な点や追記してほしい運用上の注記があればお知らせください。コード差分（コミット履歴）があればより正確な CHANGELOG 作成が可能です。