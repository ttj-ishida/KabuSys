CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/

[Unreleased]
------------

- （なし）

0.1.0 - 2026-04-21
------------------

Added
- 初期リリース。KabuSys の基本機能群を追加。
  - 設定関連
    - Settings クラスを追加（kabusys.config）。
      - 環境変数から各種設定値を取得するプロパティを提供（J-Quants / kabu station / LINE / DB パス /監視閾値等）。
      - KABUSYS_ENV のバリデーション、LOG_LEVEL のバリデーション、PAPER_FILL_MODE の検証などを実装。
      - paper_trading 用に専用 SQLite パス（PAPER_TRADING_SQLITE_PATH）をサポート。
      - PID / kill flag /しきい値を Path や数値で取得するユーティリティを提供。
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。
      - OS 環境変数 > .env.local > .env の優先順位で読み込み。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
      - .env のパースは引用符・エスケープ・コメントに対応。
    - 対話式設定ウィザードを追加（kabusys.config_setup）。
      - .env の作成・更新を支援する CLI（項目定義、シークレットのマスク表示、選択肢サポート、デフォルト値を提示）。
      - 生成される .env のテンプレート（書式）を定義。
  - 設定検証
    - validate_config CLI を追加（kabusys.validate_config）。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML があれば内容検証）などを実行。
      - --strict オプションで警告を FAIL として扱う。
      - 実行例: python -m kabusys.validate_config
  - 実行・監視スクリプト
    - run_execution（kabusys.run_execution）を追加。
      - ExecutionEngine を起動するエントリポイント。プロセス優先度設定、DB 接続（paper_trading では専用 DB を使用）、停止フラグ検知、PID ファイル管理をサポート。
    - run_monitoring（kabusys.run_monitoring）を追加。
      - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔上書き可能。監視は環境にかかわらず本番 sqlite を使用。
  - 発注関連（Execution）
    - ExecutionEngine（kabusys.execution.execution_engine）を追加。
      - シグナル読み込み（DuckDB）→ Gate1/Gate2 によるリスクチェック→発注 → WebSocket push ドレイン のワークフローを実装。
      - kill.flag による kill_switch の実装、PID ファイル書き出し、Reconciler による起動時リコンシリエーション呼び出しをサポート。
      - WebSocket プッシュ受信を別スレッドで処理し、push に対応する注文を同期（sync_order）した上で Gate3（ドローダウン監視）を実行。
      - 発注フローにおける監視DBへのログ書き込みに対応（遅延やエラーは発注自体を妨げない）。
    - OrderRecord（kabusys.execution.order_record）
      - 注文状態を表す OrderState 列挙と状態遷移ロジックを実装。許可される遷移テーブルを定義し、不正遷移で例外を投げる。
      - DB とは無関係な純粋ビジネスロジックとして実装。
    - OrderManager（kabusys.execution.order_manager）
      - DB（OrderRepository）と OrderRecord を組み合わせた外向き API を実装。
      - create_order（signal_id の重複検査、UUID 発番）、send_order（2相永続化パターンで OrderSent を先に永続化→ブローカー呼び出し→broker_order_id 保存→OrderAccepted へ遷移、OrderSentPendingError の扱い）、sync_order（ブローカー照合による状態同期）、cancel_order（キャンセル不可状態の判定と API 呼び出し）を提供。
      - DuplicateOrderError, InvalidStateTransitionError などの明示的な例外を定義。
    - Broker API 抽象（kabusys.execution.broker_api, 参照あり）
      - OrderRequest/OrderResponse/エラー型を前提に設計（実装ファイル群でのやり取りに対応）。
    - KabuStationClient（kabusys.execution.kabu_client）
      - kabuステーション REST API 用クライアント実装（httpx を使用、同期実装）。
      - トークン取得の遅延初期化と 401 時の自動再取得を実装。
      - send_order/cancel_order/get_order_status 実装（レスポンスコードに応じたエラー振る舞い、429 に対する RateLimitError、500 系は BrokerAPIError）。
      - kabu の状態コード（1..7）を内部ステータスへマッピング。
      - send_order では成行時に Price=0 を強制する等の保護を実装。
  - 監視 DB
    - monitoring_db 初期化ユーティリティを呼び出すコードを追加（run_monitoring / run_execution 側で使用）。
  - ユーティリティ
    - プロセス優先度設定ユーティリティ呼び出しを導入（起動時に High へ設定する箇所あり）。
    - ロギングセットアップ呼び出しを導入（app_name によるロガー初期化）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- （初期リリースのため該当なし）

Notes / 備考
- デフォルトのパスや環境変数名（DUCKDB_PATH, SQLITE_PATH, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が明確に定義されています。運用時は .env を生成してから validate_config を実行することが推奨されます。
- .env ファイルには機密情報が含まれるため、README に加えて .gitignore 等でコミット禁止を徹底してください（config_setup で生成される .env のヘッダにも同旨の注意書きがあります）。
- 実際のブローカー / kabu ステーションとの接続には環境依存の設定（KABU_API_BASE_URL など）や稼働中の kabu ステーションが必要です。paper_trading モードでは Mock クライアントを使用し、本番 DB と分離する設計になっています。

--- 
（この CHANGELOG はソースコードの構造・コメント・関数名・処理フロー等から推測して作成しています。実際のコミット履歴や意図とは差異がある場合があります。）