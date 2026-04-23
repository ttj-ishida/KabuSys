# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠します。  
安定版・リリース方針: ここに示す最初の公開バージョンは 0.1.0 です。

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-23
初期リリース。KabuSys のコア設定管理・発注エンジン・監視周りの実装を追加しました。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（`src/kabusys/__init__.py`: __version__ = "0.1.0"）。
- 設定管理
  - 環境変数/`.env` 自動ロード機能を追加（`src/kabusys/config.py`）。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に検出。
    - 読み込み優先度: OS 環境 > .env.local > .env。テスト時などに自動ロードを無効化するため `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。
    - `.env` のパースはシングル/ダブルクォート、エスケープ、インラインコメント（条件付き）に対応。
    - 必須環境変数取得用のヘルパー `_require()` を提供（未設定時は ValueError）。
  - Settings クラスを実装（`Settings`）し、アプリケーション設定をプロパティ経由で取得可能に。
    - J-Quants / kabu API / LINE / DB パス / paper_trading 用 DB パス / kill-flag 関連 / リソース閾値 / env/log_level 等を提供。
    - PAPER_FILL_MODE の値検証や KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
- 設定ウィザード CLI
  - `.env` を対話的に作成・更新するウィザードを追加（`src/kabusys/config_setup.py`）。
    - シークレット項目はマスク表示、選択肢・デフォルト表示、既存 .env の読み込みと再利用をサポート。
    - 保存前の確認プロンプト、生成フォーマット（コメント付きテンプレート）で `.env` を書き出す。
- 設定検証 CLI
  - 起動前に `.env` と `config/*.yaml` の不備を検出する CLI を追加（`src/kabusys/validate_config.py`）。
    - 必須環境変数チェック、プレースホルダ検出（"_here" / "your_value"）で警告。
    - KABUSYS_ENV / LOG_LEVEL の値検証。`live` での注意警告。
    - DB パスの親ディレクトリ存在チェック（存在しない場合は警告）。
    - PyYAML がない場合は YAML 内容検証をスキップし警告。YAML のパース失敗はエラー扱い。
    - `--strict` フラグで警告も FAIL（exit code 1）とする動作。
- 実行・監視スクリプト
  - Execution 起動スクリプト（`src/kabusys/run_execution.py`）
    - プロセス優先度設定、Settings 読み込み、DB 接続（paper_trading は専用 DB を使用）。
    - BrokerFactory によるブローカークライアント生成、ExecutionEngine の起動と停止フロー。
  - Monitoring 起動スクリプト（`src/kabusys/run_monitoring.py`）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知でループ終了、SQLite / DuckDB 接続管理。
- 発注周りコアコンポーネント
  - OrderRecord（状態マシン）を実装（`src/kabusys/execution/order_record.py`）。
    - 状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可遷移テーブルと遷移検証、InvalidStateTransitionError を定義。
  - OrderManager（外向き API）を実装（`src/kabusys/execution/order_manager.py`）。
    - create/send/sync/cancel の各処理を実装。
    - DuplicateOrder の検出（signal_id による部分ユニーク制約と DB 例外の変換）。
    - send_order における2相永続化パターン:
      - OrderCreated → OrderSent を先に永続化してから broker へ送信。
      - broker から受け取った broker_order_id を先に保存し、その後 OrderAccepted 等へ遷移して保存（クラッシュリカバリを考慮）。
    - OrderRejectedError / OrderSentPendingError のハンドリング（pending は OrderSent のまま broker_order_id を永続化して呼び出し元に伝播）。
    - sync_order では broker 側ステータスを内部状態へマッピングし、部分約定の進展のみフィールド更新する最適化を行う。
    - cancel_order はキャンセル不可能な状態をチェックして Broker API 呼び出し／状態遷移を行う。
  - ExecutionEngine（発注エンジン）を実装（`src/kabusys/execution/execution_engine.py`）。
    - シグナルを DuckDB から読み込み、Gate1（シグナルレベル）, Gate2（実行レベル, レート制限）, Gate3（ポートフォリオメトリクス）を導入。
    - size_multiplier の適用（BUY のみ）や発注ウィンドウ（8:50–9:10）/ドレイン（9:10–15:30）ロジック。
    - kill_flag（kill.flag）の検査と kill_switch による全 active 注文の一括キャンセル。
    - WebSocket push の受信スレッド（broker が stream_push を提供する場合）を実装し、push による同期と Gate3 チェックを行う。
    - 発注結果を position_entries に記録（発注日の翌営業日を fill_date として使用）。
    - 監視用 DB へ発注イベントを送るフック（monitoring_db が渡された場合）。
- Broker / kabu ステーションクライアント
  - KabuStationClient を追加（`src/kabusys/execution/kabu_client.py`）。
    - httpx を用いた同期 REST クライアント実装（トークン取得・自動再取得、401 リトライ）。
    - レスポンス JSON パース失敗やタイムアウト・ネットワークエラーを BrokerAPIError に変換。
    - 429 は RateLimitError として扱う。
    - kabu ステーションの注文状態コードを内部 status へマップするテーブルを実装。
- 監視周り
  - Monitoring 初期化フローを追加（Monitoring DB 初期化関数の呼び出し場所を run_monitoring / run_execution に実装）。
  - Monitoring ループは stop flag 検知で安全終了。
- ユーティリティ
  - ログ設定セットアップ・プロセス優先度設定の呼び出しを起動時に行う（各 run_*.py で実行）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / Design Decisions
- Execution と Monitoring の双方で DuckDB / SQLite を利用。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- paper_trading 動作時は SQLite を専用ファイル（PAPER_TRADING_SQLITE_PATH / default: data/paper_trading.db）に分離しており、本番 DB と完全に分離される。
- `.env` のパースは可能な限り shell ライクな記法に対応するが、極端なケースでは期待通りに動作しない可能性があります。必要に応じて .env の記述を単純に保つことを推奨します。
- validate_config は PyYAML 未導入環境でも動作するように YAML 検証をスキップするオプション的挙動を備えています（ただし YAML の存在自体は警告）。

---

今後の予定（例）
- Reconciler / Broker 実装の追加テスト強化と外部 API のモック化。
- 詳細な監視イベントスキーマ・履歴表示 UI の追加。
- async 対応（httpx.AsyncClient へ切替）などパフォーマンス改善。

もし CHANGELOG に追記してほしい点（たとえば実装の細かな差分や担当者、Issue 番号など）があれば教えてください。