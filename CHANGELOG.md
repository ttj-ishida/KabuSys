CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

0.1.0 - 2026-04-22
-----------------

Added
- 初回リリース: KabuSys 基本コンポーネントを追加。
  - settings / config
    - Settings クラスを導入し、環境変数からアプリケーション設定を一元取得可能にしました（J-Quants トークン、kabu API パスワード、DB パス、PID/Kill フラグなど）。
    - env 値（KABUSYS_ENV / LOG_LEVEL 等）の検証ロジックを実装。無効値は例外を送出します。
    - paper_trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE の検証を追加。
  - 自動 .env ロード
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします（OS 環境変数を保護して上書きしない）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の読み込みは overwrite と protected キー機構により OS 環境を保護します。
  - .env ウィザード CLI
    - python -m kabusys.config_setup で対話式に .env を作成/更新するウィザードを提供。シークレット、選択肢、デフォルト値、既存値の再利用に対応。
  - 設定検証 CLI
    - python -m kabusys.validate_config による起動前チェックを追加。
      - 必須/任意の環境変数確認、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向け追加警告など。
      - --strict オプションで警告をFAIL扱いにできます。
  - 実行スクリプト
    - run_execution: ExecutionEngine を起動する CLI。paper_trading 時は専用 DB に記録し本番 DB と分離。
    - run_monitoring: SystemMonitor のポーリングループを起動する CLI。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
  - Execution / Order 系
    - ExecutionEngine: シグナル取得（DuckDB）→ Gate チェック → 発注ループ + WebSocket push のドレインを行うセッション実装（発注時間帯・市場終了時刻の設定を含む）。
    - OrderRecord: 注文状態遷移（状態遷移表）を持つ純粋ロジックのデータモデルを実装。遷移検証とタイムスタンプ更新を行います。
    - OrderManager: OrderRecord と OrderRepository を組み合わせた外向き API を提供（create/send/sync/cancel）。DuplicateOrder 検出、二相永続化（OrderSent 前後の安全性）、OrderSentPending の扱い、sync による状態回復などを実装。
    - Reconciler, RiskManager, OrderRepository と連携する設計により、リコンシリエーション・レート制限・ドローダウン監視（Gate3）等の実装を想定したフローを提供。
    - kill_switch 実装: 全 active 注文のキャンセルとループ停止を行う仕組み。
    - position_entries への書き込み（約定予定日の記録）を ExecutionEngine に実装（発注成功時に DuckDB に反映）。
  - Broker クライアント
    - KabuStationClient: kabu ステーション REST API クライアント（httpx 同期版）。トークン管理（遅延取得／401 自動再取得）、JSON パースエラーの整形、HTTP ステータス（401/429/5xx）に応じた例外マッピングを実装。
    - stream_push（WebSocket）により push 通知を受け取り ExecutionEngine 側で処理可能（push は _push_queue に投入）。
  - 監視用 DB 初期化
    - monitoring 側の DB 初期化ユーティリティ（init_monitoring_db）を利用し、実行時に監視テーブルを保証する仕組みを採用。
  - ロギング / プロセス優先度
    - setup_logging と set_process_priority を呼び出して、実行プロセスのログ初期化と優先度設定を行うようにしました。

Changed
- 設計上の注意点／挙動
  - ExecutionEngine はセッション起動時に kill.flag を検査し、KILL_FLAG_CLEAR_ON_START に応じて自動クリアを行うか起動を拒否します（安全性を優先）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計になっています（監視は常に本番 DB を見る想定）。
  - .env のパース処理は export 形式やクォート・エスケープ、インラインコメントの扱いを改善し、よりシェルに近い挙動で読み込みます。

Fixed / Robustness
- 発注ワークフローの耐障害性を強化
  - send_order における永続化順序と OrderSentPending の扱いにより、クラッシュ時でもリコンシリエーションで復元可能な情報（broker_order_id）を保持します。
  - sync_order は部分約定の進行を検出して filled_qty / avg_fill_price の更新を行います。OrderSent→Filled のような直接遷移が来た場合は OrderAccepted を経由して正しく遷移させます。
- ネットワーク/API エラーの扱いを明確化
  - KabuStationClient はタイムアウト／ネットワークエラーを BrokerAPIError に変換し、401 時はトークン再取得と1回リトライを行います。429（レート制限）は専用例外にマッピング。
- .env ファイルの読み込み障害は warnings.warn で通知し、起動を妨げないようにしました。
- Run スクリプト（execution/monitoring）は停止フラグ検出や例外時の後片付け（DB 接続クローズ、PID ファイル削除など）を適切に行うようにしました。

Notes / 備考
- 使い方の例:
  - .env を作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行: python -m kabusys.run_execution / python -m kabusys.run_monitoring
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- config/*.yaml（system_config.yaml 等）はプロジェクトの設定ファイル群です。存在しない場合は警告が出ます（python scripts/generate_config.py での生成を想定）。
- 今後の予定（未実装／改善候補）:
  - 非同期 httpx.AsyncClient への移行（将来的な async 対応）
  - さらに詳細な監視ログ（監視 DB への書き込み強化）
  - Broker API 抽象層の拡張とテストダブルの整備

ライセンスや貢献方法などは別途ドキュメントを参照してください。