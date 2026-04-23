# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。

### Added
- 全体
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、コメント、エスケープを考慮してパース。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を提供。
    - Settings クラスで主要設定（J-Quants, kabu API, DB パス, PID/KILL フラグ、閾値など）をプロパティとして提供。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）を実装。

- 設定ウィザード
  - 対話式 .env 生成・更新スクリプトを追加（src/kabusys/config_setup.py）。
    - 必須/任意/シークレット項目の定義、既存 .env 読み込み、入力プロンプト、保存機能を提供。
    - デフォルト値や選択肢、マスク表示、保存確認を実装。
    - 保存フォーマットと注意書きを含む .env ファイル書き出しを実装。

- 設定検証 CLI
  - 起動前に環境設定をチェックする CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定チェックとプレースホルダ判定。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証（許容値: development / paper_trading / live 等）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）の親ディレクトリ存在チェック。
    - config/*.yaml の存在チェックおよび PyYAML があればパース検証（未インストール時は警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL（exit(1)）として扱う機能。
    - 実行例: python -m kabusys.validate_config [--strict]

- 実行ランナー / 監視
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度設定、settings 読み込み、paper_trading 用の専用 SQLite DB 切り替え、PID/停止フラグ管理を実装。
    - ExecutionEngine をスレッドで起動し、停止フラグ検出での graceful shutdown を実装。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して DB を初期化。

- 発注/実行コア
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（発注窓: 8:50-9:10）、WebSocket push のドレインループ（9:10-15:30）を実装。
    - Gate 1（シグナルレベル）、Gate 2（実行レート制限、Circuit Breaker 対応）、Gate 3（ドローダウン監視）を統合。
    - kill_switch による全 active 注文キャンセル、PID/kill.flag の扱い、リコンシリエーション呼び出しの起動時実行を実装。
    - position_entries への書込み（buy/sell の扱い）や監視DBへのイベント記録（監視DBが指定されている場合）を実装。
    - WebSocket（push）を broker の stream_push によって受信し内部キューで処理。

  - OrderRecord（純粋ロジックの状態機械）を実装（src/kabusys/execution/order_record.py）。
    - OrderState 列挙型と遷移可能性テーブルを実装。
    - transition_to による遷移検証、updated_at 自動更新、補助フィールド更新を実装。
    - InvalidStateTransitionError を定義。

  - OrderManager（DB 永続化と外向き API）を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id の重複チェック（部分ユニークインデックス / DuplicateOrderError）。
    - send_order: クラッシュ耐性を考慮した手順（OrderSent の永続化→ broker 呼び出し→ broker_order_id を先に永続化→ OrderAccepted へ遷移）を実装（2相永続化戦略）。
    - send_order は OrderRejectedError, OrderSentPendingError の扱いを実装（pending の場合は broker_order_id を保存して例外を伝播）。
    - sync_order: broker 側ステータス取得からローカル状態へ同期（部分約定の進行はフィールド更新で対応）。
    - cancel_order: 終端状態のキャンセル不可チェック、broker cancel 呼び出し、Cancelled への遷移を実装。

  - Broker/Kabu クライアント
    - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
      - httpx を用いた同期 REST クライアント。トークン取得（遅延初期化）と 401 時の自動再取得および 1 回リトライを実装。
      - レスポンス JSON パース失敗やネットワークエラー、429（Rate Limit）や >=500 のサーバエラーを適切に BrokerAPIError / RateLimitError として扱う。
      - WebSocket 用に websocket ラッパ（stream_push）との連携を想定。

- データベース / 監視関連
  - DuckDB（分析用）と SQLite（監視・注文履歴）を併用する設計を導入。
  - Monitoring DB 初期化ユーティリティ（init_monitoring_db）を使用して冪等にテーブルを保証。

- ユーティリティ
  - ロギング設定セットアップとプロセス優先度変更の呼び出しを各ランナーで行う（setup_logging / set_process_priority を利用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env ファイルに関する注意書きを config_setup に記載（.env を Git にコミットしないことを強調）。
- シークレット項目はウィザードでマスク表示されるように実装。

---

注意・移行メモ:
- 初期設定は python -m kabusys.config_setup で .env を生成してから、python -m kabusys.validate_config で検証することを推奨します。
- 本番実行時は KABUSYS_ENV=live を設定すると追加の警告チェックが有効になります（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認等）。
- paper_trading モードでは監視用の SQLite DB は paper_trading 用に分離されます（PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE を利用可能）。
- auto .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

このリリースについての問合せ・不具合報告は issue を立ててください。