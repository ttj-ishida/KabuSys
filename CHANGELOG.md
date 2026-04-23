# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
このファイルはコードベース（src/kabusys 以下）から推測して作成した初期リリース向けの変更履歴です。

全般的な注意:
- CLI スクリプト: python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.run_execution, python -m kabusys.run_monitoring
- 環境変数の自動読み込み: プロジェクトルート（.git または pyproject.toml）を起点に .env, .env.local を読み込み（OS 環境変数を優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Unreleased
---------

0.1.0 - 2026-04-23
------------------

Added
- 初期公開: KabuSys 日本株自動売買システムの基本コンポーネント群を追加。
  - src/kabusys/__init__.py にバージョン定義（__version__ = "0.1.0"）。
- 環境設定まわり
  - config.Settings クラスを追加。環境変数から各種設定（API トークン、DB パス、監視閾値、PID/Kill Flag パス等）を取得するプロパティを提供。
  - .env ファイル自動読み込み機構を実装（プロジェクトルートを探索して .env → .env.local の順で読み込み。.env.local は上書き）。既存 OS 環境変数は保護。
  - .env ファイルパーサー: export プレフィックス対応、クォート/エスケープ、インラインコメント処理などの堅牢なパース処理を実装。
  - run-time における各種設定のバリデーション（enum 値、数値変換など）を Settings のプロパティで行う（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- 設定ウィザード
  - src/kabusys/config_setup.py: 対話式ウィザードを追加。.env の初期作成・更新を支援。
  - よく使う設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン等）をプロンプト表示して .env を生成。
  - 既存 .env 読み込み、機密値はマスク表示、確認プロンプト付きで書き込み。
- 設定検証 CLI
  - src/kabusys/validate_config.py: 起動前に .env と config/*.yaml の問題を検出する検証ツールを追加。
  - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証、本番環境時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START）を実施。
  - --strict オプションで警告を FAIL として扱い exit(1) を返す。
- Execution 系実装
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナルプル方式の発注エンジンを実装。時間帯（8:50-9:10 シグナル処理、9:10-15:30 push ドレイン）に沿ったセッション実行フローを提供。
    - Gate ベースのリスクチェック（Gate1: シグナル、Gate2: エグゼキューション/レート制御、Gate3: ドローダウン）を組み込み、Gate3 failure 時に kill_switch を発動。
    - WebSocket push を受けての同期（_websocket_worker）や _push_queue のドレイン処理を実装。
    - position_entries（DuckDB）への書き込みにより最低保有日数や再エントリー制御をサポート。
    - PID ファイル作成、kill.flag チェック、KILL_FLAG_CLEAR_ON_START の挙動をサポート。
  - Execution 起動スクリプト（src/kabusys/run_execution.py）
    - paper_trading 環境では paper_sqlite_path（data/paper_trading.db）を使用し本番 DB と分離。
    - プロセス優先度設定、DB 接続、Engine 実行と停止監視を提供。
  - Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を利用。
- 注文と状態管理
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙 OrderState と許可遷移定義を実装。状態遷移検証および更新（updated_at 自動更新）を提供。InvalidStateTransitionError を定義。
  - OrderRepository（注: ファイルはコードベースに存在）と組み合わせる OrderManager（src/kabusys/execution/order_manager.py）
    - create_order: signal_id ごとの重複検出（DB 制約・レポジトリ参照）と OrderRecord の生成。
    - send_order: クラッシュ耐性を意識した二相的永続化フロー（OrderSent の永続化→broker 呼び出し→broker_order_id 永続化→OrderAccepted 更新）。OrderRejectedError / OrderSentPendingError の扱いを明示。
    - sync_order: broker 側状態照合による状態同期。partial 進展時のフィールド更新処理を含む。
    - cancel_order: キャンセル不可状態の判定と broker cancel 呼び出し後の Cancelled 遷移。
    - DuplicateOrderError の定義。
  - Reconciliation（参照や呼び出し箇所あり）との連携設計（クラッシュ後の整合回復を考慮）。
- Broker API クライアント
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx を使用した同期 REST クライアントを実装。トークン取得（/token）を内部で遅延初期化。401 受信時はトークン再取得して 1 回リトライする仕組みを提供。
    - レスポンス JSON パースのエラーハンドリング、タイムアウト/ネットワーク例外の BrokerAPIError への変換、429 の RateLimitError 変換、サーバーエラー判定などを実装。
    - kabu station の状態コード → 内部ステータス変換マップを定義。
- 監視・ログ・ユーティリティ
  - setup_logging, set_process_priority などユーティリティを使用する起動スクリプトを提供（monitoring / execution）。
  - MonitoringDB（インタフェース）経由で発注イベントのログを記録する仕組みを一部のフローに組み込み。

Changed
- （初回リリースのため過去変更なし。設計上の注意点をドキュメントに反映。）

Fixed
- （初回リリースのため過去修正なし。クラッシュ時の整合性を考慮した OrderManager の設計により既知リスクを低減。）

Security
- 機密値（J-Quants トークン、kabu API パスワード、LINE トークン）は .env として取り扱い、config_setup の出力ヘッダで .env を絶対に Git にコミットしないよう注意喚起を追加。
- .env 読み込み時に OS 環境変数を保護するため protected set を導入（.env.local で OS 環境を上書きしない）。

Notes / Known behaviors
- .env の自動読み込みはプロジェクトルートが検出できない場合スキップされる（パッケージ配布後の安全対策）。
- validate_config は PyYAML が未インストールの場合、YAML 内容検証をスキップして警告を出す。
- ExecutionEngine は時間帯に依存する挙動（シグナル処理ウィンドウ、push ドレイン）を持ち、テスト用途では内部メソッド（_process_signals / _drain_push_queue）を直接呼べる設計。
- OrderManager.send_order は二相永続化を採用し、クラッシュ後の再照合（Reconciler）で状態回復が可能になるよう設計されている。
- PAPER_FILL_MODE の許容値チェックや LOG_LEVEL/KABUSYS_ENV の厳密チェックが Settings に実装されており、不正値は ValueError を送出する。

貢献・開発のヒント
- CI やデプロイ前に python -m kabusys.validate_config を実行して設定チェックを行ってください（--strict を使うと警告も FAIL として扱えます）。
- 本番起動時は KABUSYS_ENV=live の設定に注意（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値等を確認）。
- KabuStationClient は同期実装ですが、将来的に非同期化する場合は httpx.AsyncClient へ置き換えることで対応可能です。

--- 

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートや変更履歴はプロジェクト運用ルールに合わせて適宜更新してください。）