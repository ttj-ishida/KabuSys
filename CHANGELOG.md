# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

既知の互換性に関する情報や重要な注意点は各リリースの説明を参照してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

### Added
- 初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
  - 環境設定
    - .env 自動ロード機構を実装（src/kabusys/config.py）。
      - プロジェクトルートの検出は .git または pyproject.toml を基準に探索。
      - 読み込み順: OS 環境変数 > .env.local > .env。
      - OS 環境変数を保護する protected 機構を備えた .env 読み込み（上書き制御）。
      - .env の行解析は export 構文、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理に対応。
    - 対話式ウィザードで .env を生成・更新する CLI を追加（src/kabusys/config_setup.py）。
      - 各種設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 等）を対話的に設定可能。
      - シークレット項目はマスクして表示、保存前に内容確認を行う。
  - 設定 API
    - Settings クラスを実装（src/kabusys/config.py）。
      - 環境変数の取得ラッパー（必須項目は _require で未設定時に ValueError）。
      - Paper Trading 用パスや flag パス、リソース閾値などのプロパティを提供。
      - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の入力検証（不正値は ValueError）。
  - 設定検証ツール
    - 起動前に .env および config/*.yaml の不備を検出する CLI を追加（src/kabusys/validate_config.py）。
      - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パース確認（PyYAML がない場合はスキップ）。
      - --strict オプションで警告も FAIL として扱える。
  - 実行 / 監視 起動スクリプト
    - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
      - プロセス優先度設定、PID ファイル管理、stop flag 検知など。
    - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）。
      - MONITOR_POLL_INTERVAL によるポーリング間隔制御（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用。
  - 注文システム（Execution）
    - OrderRecord（状態マシンの純粋なデータモデル）を実装（src/kabusys/execution/order_record.py）。
      - 明示的な状態列挙 OrderState と許可遷移テーブル。InvalidStateTransitionError 定義。
      - transition_to により更新時刻自動更新とオプションフィールド更新をサポート。
    - OrderManager（外向き API）を実装（src/kabusys/execution/order_manager.py）。
      - create_order: signal_id 一意チェック（DuplicateOrderError）。
      - send_order: 2相永続化の設計でクラッシュ耐性を向上（OrderSent を先に永続化、broker_order_id をコミットしてから Accepted に遷移）。
      - sync_order: broker 側の状態照合と部分約定の差分更新処理。
      - cancel_order: キャンセル不可能な状態判定と API 呼び出し。
    - ExecutionEngine（シグナルプル型発注エンジン）を実装（src/kabusys/execution/execution_engine.py）。
      - シグナル処理（8:50-9:10）と WebSocket push ドレインループ（9:10-15:30）を含むセッション制御。
      - Gate 1/2/3 によるリスクチェックフローの実装（RiskManager と連携）。
      - size_multiplier に基づく発注量調整、DuplicateOrder 回避、API レイテーションのリトライ/回避、発注遅延（latency）を監視 DB に記録。
      - kill_switch による全 Active 注文のキャンセル処理とセッション停止機構。
      - WebSocket からの push を受け取り _push_queue 経由で処理、push によるポートフォリオ評価と Gate3 判定を実行。
  - ブローカークライアント
    - KabuStation REST クライアントを実装（src/kabusys/execution/kabu_client.py）。
      - httpx を用いた同期クライアント。トークン取得・キャッシュ、401 時のトークン再取得とリトライ処理、HTTP エラーの専用例外化（RateLimitError / BrokerAPIError 等）。
      - push（WebSocket）受信用の stream_push を想定した構造。
  - その他
    - DuckDB / SQLite の併用を想定した DB 接続箇所（監視・分析用途）。
    - 実行時のプロセス優先度設定ユーティリティ呼び出し（set_process_priority）。
    - logging 設定ユーティリティを利用したロギング初期化。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env の解析を堅牢化
  - export プレフィックス、クォート内のエスケープ、インラインコメントの扱いを改善（src/kabusys/config.py）。
- 発注フローのクラッシュ耐性を改善
  - send_order で broker_order_id を先に永続化するなど、クラッシュ時に状態復旧可能な二相的永続化設計を導入（src/kabusys/execution/order_manager.py）。
- sync_order で同一状態だが約定数量／平均価格のみ変化した場合に差分更新することで部分約定の進捗を正しく反映（src/kabusys/execution/order_manager.py）。

### Security
- .env ファイルの生成時に「.env を絶対に Git にコミットしないこと」を明示（src/kabusys/config_setup.py）。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Migration
- Settings のプロパティは未設定時に ValueError を投げることがあるため、起動前に `python -m kabusys.validate_config` を実行して設定検証することを推奨します。
- Paper Trading 実行時は DB が分離されるため、本番データと混在しない点に注意してください（settings.paper_sqlite_path を使用）。
- 本番環境（KABUSYS_ENV=live）では LINE API の設定や KILL_FLAG_CLEAR_ON_START の値に注意してください。validate_config が警告を出します。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や変更差分に基づく正式な履歴は git ログ等を参照してください。）