# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

※ この CHANGELOG は提示されたコードベースの内容から推測して作成しています。

## Unreleased
（なし）

## [0.1.0] - 2026-04-22
初回公開リリース

### Added
- 基本構成・設定管理機能を追加
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索し、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env/.env.local の読み込みロジック実装（.env.local は上書き、OS 環境変数は保護）。
  - .env の各行パーサを実装し、export 形式、クォート内のエスケープ、インラインコメントの扱いに対応。

- Settings クラスを追加（環境変数からの型付きアクセス）
  - J-Quants / kabuステーション / LINE / DB パス / PID/Kill Switch 等のプロパティを提供。
  - PAPER_FILL_MODE 等の列挙的な検証を実装し、不正値では ValueError を送出。
  - env/log_level の検証ロジックを実装（有効値チェック）。

- 設定ウィザード CLI を追加（kabusys.config_setup）
  - 対話式で .env を作成・更新する run_wizard を提供。
  - 必須・任意項目やシークレット値のマスク表示、選択肢チェック、既存値の再利用等に対応。
  - .env 書き出し時に注意書き（.env をコミットしない）を含めて出力。

- 設定検証 CLI を追加（kabusys.validate_config）
  - .env と config/*.yaml を起動前に検証するツール。
  - 必須環境変数の未設定チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL 値検証、DB パス（親ディレクトリ存在確認）等を実行。
  - PyYAML 未インストール時の YAML 内容検証スキップ、--strict フラグで警告を FAIL 扱いにする機能。
  - 結果を INFO/WARNING/ERROR に分類して出力し、エラーや strict モードで非ゼロ終了コードを返す。

- 実行/監視スクリプトを追加
  - run_execution: ExecutionEngine を起動するエントリポイント。
    - paper_trading 環境では paper 用 SQLite を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、stop flag 検出による停止処理を実装。
  - run_monitoring: SystemMonitor のポーリングループ実行スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数で間隔変更、停止フラグ検出による終了。

- 発注エンジン・注文管理
  - ExecutionEngine を実装（シグナル処理 + push ドレインループ）。
    - シグナル取得（DuckDB）、Gate1/2/3 によるリスクチェック、WebSocket push のドレイン処理を実装。
    - kill.flag による起動拒否/kill_switch の扱い。KILL_FLAG_CLEAR_ON_START により起動時にクリアするオプションあり。
    - 発注・送信の流れで監視 DB へのイベント記録を行えるフックを保持。
  - OrderManager を実装（OrderRecord + OrderRepository を組み合わせた外向き API）
    - create_order: signal_id 重複チェック（DB の部分ユニーク制約も考慮）と OrderRecord 作成。
    - send_order: 2 相永続化戦略を導入（OrderSent を先にコミット → broker 呼び出し → broker_order_id をコミット → OrderAccepted に遷移）。OrderSentPendingError の扱い、Rejected ハンドリング。
    - sync_order: broker 側の状態照合と遷移適用（部分約定の進行も差分更新）。
    - cancel_order: キャンセル不可状態の判定と broker キャンセル呼び出し。
  - OrderRecord と状態機械を実装
    - OrderState 列挙、許可遷移マップ、InvalidStateTransitionError、transition_to による遷移検証とタイムスタンプ更新。
    - Filled/Closed 等の端状態の扱いを明確化。

- ブローカークライアント（kabu station）実装
  - KabuStationClient を提供（httpx を使用した同期 REST クライアント）。
  - トークン取得の遅延初期化・自動再取得、401 リトライ、429 を RateLimitError として扱う等の堅牢化。
  - レスポンス JSON パースエラーやネットワーク/タイムアウトエラーを BrokerAPIError に変換して扱う。

- 監視関連
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）の利用箇所を run_monitoring/run_execution で呼び出し、監視テーブルの存在を保証。
  - ExecutionEngine 内での監視 DB への発注イベント記録処理（監視 DB 書き込み失敗時はログ警告のみでフロー継続）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- .env の取り扱いに関する注意を CLI 生成ファイル内に明記（.env を Git にコミットしないこと）。

---

補足:
- 本 CHANGELOG はコードから読み取れる設計・挙動を要約したものであり、実際のコミット履歴をそのまま反映したものではありません。もしコミット単位の履歴や細かな日付が必要であれば、実際の git 履歴を提供してください。