# Changelog

すべての notable な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、安定したリリースごとにエントリを追加してください。

現在のバージョン: 0.1.0

## [Unreleased]

（今後の変更はここに記載）

## [0.1.0] - 2026-04-23

初回公開リリース。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 環境設定・管理
  - Settings クラス（`src/kabusys/config.py`）を追加。
    - 環境変数からアプリケーション設定を取得するプロパティを提供（J-Quants トークン、kabu API パスワード / ベース URL、LINE 設定、DB パス、PID / Kill flag 関連、しきい値など）。
    - `PAPER_FILL_MODE` / `KABUSYS_ENV` / `LOG_LEVEL` 等の値検証（不正値は例外を送出）。
  - .env 自動読み込み機能
    - プロジェクトルートを `.git` または `pyproject.toml` で検出して `.env` / `.env.local` を自動読み込み（OS 環境変数を上書きしない保護機構あり）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 高機能な .env パーサー（`_parse_env_line`）
    - `export KEY=val` 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - `.env` 読み書きユーティリティ（`_load_env_file` / `_write_env` 等）。
- 対話式設定ウィザード
  - `src/kabusys/config_setup.py` に CLI ウィザードを追加。
    - `.env` の初期作成・更新を対話式で支援。選択肢・デフォルト値・シークレット項目の扱いをサポート。
    - 生成される `.env` にテンプレートと注記を出力（Git へのコミット禁止の注意喚起含む）。
- 設定検証ツール
  - `src/kabusys/validate_config.py` に設定検証 CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在と（PyYAML があれば）パース検証を実施。
    - プレースホルダ値検出、`--strict` モード（警告をエラー扱い）をサポート。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告など）。
- 実行スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動するエントリポイント。プロセス優先度設定、DB 接続（paper_trading 時は専用 SQLite を使用）等を行う。
  - `run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプト。`MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能。Monitoring は実行環境にかかわらず本番の sqlite_path を使用。
- 発注エンジン関連
  - ExecutionEngine（`execution_engine.py`）
    - シグナル読み込み、Gate 1/2/3 を用いたリスクチェック、発注ループ（シグナル処理 + WebSocket push ドレイン）を実装。
    - kill.flag / PID ファイルの取り扱い、WebSocket push のドレイン、position_entries 更新、監視 DB へのログ記録をサポート。
  - OrderRecord（`order_record.py`）
    - 注文状態の State Machine と遷移検証を実装。`InvalidStateTransitionError` を導入。
  - OrderManager（`order_manager.py`）
    - OrderRecord と OrderRepository を組み合わせた外向き API を提供（create/send/sync/cancel）。
    - send_order における 2 相永続化パターン（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted へ遷移）を採用し、クラッシュに対する回復性を強化。
    - OrderSentPendingError（発注保留）や OrderRejectedError などのハンドリングを実装。
    - DuplicateOrderError（同一 signal_id の active 注文重複を防止）。
  - Reconciler / RiskManager 等との統合ポイント（ExecutionEngine 内の組み立てロジック）。
- ブローカークライアント（kabu station）
  - `KabuStationClient`（`kabu_client.py`）
    - httpx ベースの同期 REST クライアントを実装。トークン取得の遅延初期化、自動再取得（401 時にリトライ）を提供。
    - レスポンス JSON パース失敗やネットワークエラーを BrokerAPIError 等に変換。
    - HTTP 429 を RateLimitError にマッピング。
    - WebSocket push を受けるための stream_push（存在すれば WebSocket スレッドを起動）を想定。
    - kabu station の内部状態コードを内部ステータス文字列にマッピング。
- データベース・分析
  - DuckDB と SQLite の組み合わせを利用（DuckDB は分析、SQLite は監視・履歴用）。
  - Paper Trading と本番の SQLite DB を分離（`paper_sqlite_path`）。
- 監視・運用機能
  - kill_switch の実装（全 active 注文のキャンセル）。
  - Gate 3（ポートフォリオ評価に基づくドローダウンチェック）で kill_switch を発動。
  - PID / stop flag / stop_requested.flag の検出処理をサポート。
- ロギング・実行環境
  - 起動時にプロセス優先度設定（utils 側の処理を利用）。
  - ログレベルの検証と取得ロジックを提供。

### Changed
- （初回リリースのため変更点は特になし。上記は初期導入機能群です。）

### Fixed
- 耐障害性・整合性の改善
  - send_order の 2 段階永続化により、broker 呼び出し中や直後のクラッシュ時にも Reconciliation で状態回復が可能。
  - sync_order にて同一状態でも部分約定の進行（filled_qty / avg_fill_price）を反映するよう修正。
  - `.env` パーサーの改善により、クォートやエスケープを含む値やインラインコメントの誤解析を防止。
- 実行時安全策
  - 起動時の kill.flag 処理に `KILL_FLAG_CLEAR_ON_START` オプションを追加（本番環境での誤起動防止／開発時のクリア許容）。
  - run_monitoring のポーリング間隔の不正値（0 以下や非整数）に対するフォールバックを追加。

### Security
- .env ファイルの取り扱いに関する注意書きを生成（config_setup の出力）。`.env` を Git にコミットしないように明示。
- シークレット項目（J-Quants トークン、kabu API パスワード、LINE トークン）は対話ウィザードでマスク表示。

### Notes / Misc
- 一部の機能は外部ライブラリ（PyYAML、httpx 等）に依存します。PyYAML 未インストール時は validate_config の YAML 内容検証がスキップされ、該当部分が警告になります。
- このリリースはアーキテクチャ/主要ワークフローの基盤を提供します。今後、テストカバレッジの強化、非同期化（httpx.AsyncClient）等の改良が予定されています。