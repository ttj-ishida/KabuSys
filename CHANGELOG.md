# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このプロジェクトの初回公開リリースノートをコードベースから推測して日本語でまとめています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-23

### 追加 (Added)
- パッケージ初版リリース（KabuSys 0.1.0）
  - 自動売買システムの実行基盤・ユーティリティを実装。
- 環境・設定管理
  - 環境変数の自動読み込み機能を実装（.env, .env.local）。プロジェクトルートの探索は .git または pyproject.toml を基準に行う（src/kabusys/config.py）。
  - .env ファイルのパーサーを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応（src/kabusys/config.py::_parse_env_line）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、アプリケーション設定を型付きで提供（各種パス、トークン、環境種別、しきい値など）（src/kabusys/config.py）。
  - 必須環境変数取得時は未設定で ValueError を投げる _require 実装（J-Quants / kabu API パスワード等）。

- 設定ウィザード CLI
  - .env の初期作成・更新を対話式に支援する config_setup CLI を追加。各項目の説明、選択肢、シークレットマスク表示などを提供（src/kabusys/config_setup.py）。
  - .env の読み書きロジックを実装。生成テンプレートに注意書き（Gitにコミットしない等）を含む。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml の設定不備を検出する validate_config CLI を追加（src/kabusys/validate_config.py）。
    - 必須/任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検査（PyYAML が無ければスキップ）などを実装。
    - --strict オプションで警告を FAIL として扱う機能を追加。
    - 実行例: python -m kabusys.validate_config

- 実行スクリプト
  - ExecutionEngine 起動スクリプト run_execution を追加（src/kabusys/run_execution.py）。
    - Paper trading 時には専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - 高プロセス優先度設定、PID ファイル管理、停止フラグ検出（stop_requested.flag / kill.flag）などの起動周辺処理を実装。
  - Monitoring ポーリングスクリプト run_monitoring を追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関係なく本番 sqlite_path を使用する設計。

- 注文管理コア
  - OrderRecord: 注文状態列挙と状態遷移ロジックを純粋ロジックとして実装（状態遷移検証、タイムスタンプ自動更新、オプションフィールド更新）（src/kabusys/execution/order_record.py）。
  - OrderManager: OrderRecord と OrderRepository を組み合わせた外向け API を実装（作成、送信、同期、キャンセル）（src/kabusys/execution/order_manager.py）。
    - send_order のクラッシュ耐性を考慮した2相永続化パターン（OrderSent を先にコミット、broker_order_id を先に保存、次に Accepted へ遷移）を実装。
    - OrderSentPendingError（注文番号は発行されたが約定しない等）や OrderRejectedError の取り扱いを実装。
    - DuplicateOrderError を導入（同一 signal_id の active 注文重複防止）。
    - sync_order によりブローカー側ステータスを DB と同期する機能を実装（部分約定の増分更新ロジック含む）。

- 発注エンジン（ExecutionEngine）
  - シグナルプル方式の発注ループを実装（シグナル処理ウィンドウ、WebSocket push ドレインループ、セッション終了制御）（src/kabusys/execution/execution_engine.py）。
  - 複数のリスクゲートを導入:
    - Gate 1: シグナルレベル検査（シグナル単位のスキップ等）
    - Gate 2: エグゼキューションレベル（レート制限・サーキットブレーカー） — 最大3回リトライ
    - Gate 3: ドローダウン監視（重大なドローダウンで kill_switch を発動）
  - kill_switch による全 active 注文のキャンセル処理を実装（停止イベント設定、キャンセル時にエラー耐性を持たせる）。
  - WebSocket スレッドで kabu push を受信して同期処理を行う設計（broker が stream_push を提供しない場合はスキップ）。
  - 発注成功時に position_entries への記録（入場日の記録、売却での更新）や監視 DB へのトレードイベントログ等を試みる（失敗しても発注フローを継続）。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（同期 httpx クライアント、トークン自動管理、再試行ロジック）（src/kabusys/execution/kabu_client.py）。
    - トークン取得 (/token) とリクエスト時の 401 による自動再取得 + 1回リトライを実装。
    - HTTP エラー（タイムアウト、ネットワーク、429 レート制限、5xx）を専用例外へ変換。
    - kabu station の状態コードと内部状態のマッピングを実装（open/partial/filled/cancelled/rejected 等）。

- 監視周り
  - monitoring_db の初期化ユーティリティを利用して監視 DB を準備（run_monitoring, run_execution で使用）。
  - run_monitoring/run_execution で DuckDB / SQLite 接続を確立。

### 変更 (Changed)
- デフォルト設定・挙動
  - 環境変数の既定値を統一（DUCKDB_PATH, SQLITE_PATH, KABU_API_BASE_URL, LOG_LEVEL 等のデフォルト）。
  - Settings.env / Settings.log_level で不正値は ValueError による明示的エラーに変更（起動時の早期検出）。

### 修正 (Fixed)
- 初版リリースにつき、明示的なバグ修正履歴は無し（コードから推測される安定化・例外処理の追加を含む）。

### セキュリティ (Security)
- .env を生成するテンプレートで「.env を絶対に Git にコミットしないこと」を明記。
- シークレット入力はウィザード上でマスク表示（出力時は **** 表示）。

---

補足:
- 使い方の例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン: python -m kabusys.run_execution
  - 監視ループ: python -m kabusys.run_monitoring
- 本 CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴やプロジェクト管理情報に基づく正式な変更履歴がある場合はそちらを優先してください。