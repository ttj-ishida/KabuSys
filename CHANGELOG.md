# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新更新: 2026-04-23

## [Unreleased]

## [0.1.0] - 2026-04-23
### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装。
- パッケージ情報
  - バージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として設定。

- 設定管理
  - src/kabusys/config.py
    - .env ファイルと OS 環境変数からの設定読み込み機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env の自動ロード順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションをサポート。
    - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
    - Settings クラスを追加し、各種設定（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、閾値など）をプロパティとして提供。
    - 環境変数値の検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）の例外処理を実装。

- 設定作成ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を新規作成・更新する CLI を追加（python -m kabusys.config_setup）。
    - 主要設定項目（環境、API トークン、DB パス、LINE 設定、ログレベル、Kill Flag の自動クリア有無など）を網羅。
    - 既存 .env 読み込み、入力補助、シークレットマスク表示、確認プロンプト、.env 書き込み機能を実装。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の起動前チェック用 CLI を追加（python -m kabusys.validate_config）。
    - 必須/任意環境変数チェック、プレースホルダ検出（"_here"/"your_value" 等）、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ検査を実装。
    - config/*.yaml の存在チェックと PyYAML が利用可能な場合の YAML パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL と扱う。

- 実行ユーティリティ
  - src/kabusys/run_execution.py
    - ExecutionEngine を使った実運用起動スクリプトを追加。
    - paper_trading 環境向けに専用 SQLite（paper_trading.db）を使用して本番 DB から分離。
    - 停止フラグ（data/stop_requested.flag）検知、PID ファイル管理、プロセス優先度設定、DB 接続の確立を実装。

  - src/kabusys/run_monitoring.py
    - SystemMonitor をポーリング起動する監視用スクリプトを追加。
    - 環境にかかわらず本番 sqlite_path を使用（監視は常に本番 DB を参照）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。

- 実行エンジンと関連コンポーネント
  - src/kabusys/execution/execution_engine.py
    - Signal Queue ベースの発注エンジンを実装（シグナル処理ウィンドウ／push ドレインループ、WebSocket push 処理、kill switch 等）。
    - Gate1（シグナル単位検査）・Gate2（エグゼキューション／レート制限）・Gate3（ドローダウン監視）を導入。NG の場合は適切に処理（スキップ／kill_switch）。
    - Signal 読み出しは DuckDB を利用し、position_entries の更新（エントリー/クローズ日付）を行う。
    - WebSocket push の受信を別スレッドで行い、_push_queue 経由で同期処理。
    - PID ファイル書き込み・kill.flag 起動阻止・KILL_FLAG_CLEAR_ON_START による自動クリア挙動を実装。
    - セッションライフサイクル（8:50 発注処理 → 9:10 発注締切 → 15:30 セッション終了）を実装。

  - src/kabusys/execution/order_record.py
    - 注文状態を表す OrderState 列挙型と OrderRecord データモデルを実装。
    - 許可遷移テーブルと transition_to() による状態遷移検証、更新時刻の自動更新、関連フィールド更新を提供。
    - 不正遷移時に InvalidStateTransitionError を送出。

  - src/kabusys/execution/order_manager.py
    - OrderRecord と OrderRepository を組み合わせた外向け API を実装（create/send/sync/cancel）。
    - 重複注文検出（signal_id による部分ユニーク制約）と DuplicateOrderError。
    - send_order の堅牢化: OrderSent への永続化（クラッシュ安全性のため broker 呼び出し前に保存）、broker_order_id の先行永続化、OrderAccepted への遷移、OrderRejected / OrderSentPending の扱いを明確化（2相永続化と Reconciliation を想定）。
    - sync_order による broker 側状態取得と DB への同期（部分約定や avg_fill_price の更新を含む）。
    - cancel_order のキャンセル不可能状態判定と broker 呼び出し、状態遷移処理。

  - src/kabusys/execution/kabu_client.py
    - kabuステーション REST API クライアント実装（同期 httpx、token 管理、401 リトライ、429 の RateLimitError、各種 HTTP エラーを BrokerAPIError に変換）。
    - トークン遅延初期化と自動再取得の実装。
    - stream_push（WebSocket）連携のフックを想定した設計。

- ブローカープロトコル & リスク管理（インターフェース）
  - BrokerAPIProtocol など（参照実装や工場クラスは別モジュールで実装）。
  - RiskManager、Reconciler、OrderRepository、MonitoringDB などの統合ポイントを ExecutionEngine / run_* スクリプトが利用。

- 監視・DB 初期化
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を利用して監視テーブルを確実に準備する処理を run_execution/run_monitoring に追加。

- ロギング・プロセス制御
  - setup_logging、set_process_priority を呼び出して運用向けのログ設定およびプロセス優先度設定を行うフローを追加。

### Changed
- n/a（初回リリースのため履歴なし）

### Fixed
- n/a（初回リリースのため履歴なし）

### Security
- 環境変数ファイル（.env）を Git にコミットしない旨をウィザードの出力に明記。

---

備考:
- 本 CHANGELOG はコード内容から推測して作成しています。実際のリリースノートと差分がある場合は適宜編集してください。