# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-17

初回リリース。

### 追加
- 基本アプリケーション情報
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。

- 実行・デーモン起動スクリプト
  - run_execution:
    - ExecutionEngine を起動するメインスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止。
    - execution.pid（デフォルト data/execution.pid）をサポート。
  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB の分離方針）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ検知・KeyboardInterrupt による終了処理を実装。

- 設定・環境変数管理
  - config.Settings クラスを追加し、アプリケーション設定を環境変数から取得するラッパーを提供。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、各種閾値（CPU/MEM/DISK）、PID/KILL フラグパス、ログレベル、環境種別（development/paper_trading/live）などのプロパティを定義。
    - PAPER_FILL_MODE（paper trading のフィルモード）を検証（instant/partial/never/reject）。
  - .env 自動ロード機能を追加
    - プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env/.env.local を自動で読み込む（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env の行パーサは export プレフィックス対応、引用符付き値のエスケープ対応、インラインコメントの扱い等を考慮した堅牢な実装。
  
- 設定ヘルプ・検証ツール
  - config_setup:
    - 対話式ウィザードで .env を初期作成／更新する CLI を追加。
    - デフォルト値、選択肢、シークレット表示（マスク）等に対応。生成する .env には注意書きを挿入。
  - validate_config:
    - .env と config/*.yaml の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - --strict モードで警告を FAIL 扱いにできる。
    - 本番（KABUSYS_ENV=live）向けに追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

- ポートフォリオ構築ロジック
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供（スコア全ゼロ時は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中（セクター別エクスポージャ）に応じて候補を除外するロジックを追加（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返すユーティリティ（未知レジームは 1.0 にフォールバックし警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: weights/candidates/ポートフォリオ情報から発注株数を計算する純関数を実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - lot_size 単位で丸め、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）を考慮した aggregate cap（スケールダウン）を実装。
      - 不正価格（<=0）やデータ欠損時のスキップ処理を実装。

- 研究・ファクター計算
  - research.factor_research:
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してファクターを計算する関数群を追加。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、volume_ratio 等を計算（ファイル内で SQL ウィンドウ関数利用）。
    - 設計方針として DuckDB 上で完結し、本番 API にアクセスしない純粋な解析モジュール。

- モニタリング・検証ツール
  - tools.paper_verification_report:
    - ペーパートレード用 SQLite を読みレポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ (avg/max/P95) を集計し PASS/FAIL 判定を行う。
    - デフォルト基準値（稼働率 99.0%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - --from/--to/--db オプションをサポート。

- ユーティリティ
  - utils.process_priority:
    - プロセス優先度設定と CPU affinity 設定関数を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）間の差を吸収し、psutil を用いて優先度や affinity を設定。
    - 権限不足や非対応 OS 時は警告を出してスキップする安全仕様。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db（参照）を呼び出して、監視用テーブルが存在することを起動時に保証（冪等）。

### 変更
- 起動時の既定動作
  - run_monitoring / run_execution ともに起動時にプロセス優先度を high に設定するようにした（set_process_priority を呼び出す）。
- DB 運用方針
  - 監視（monitoring）は環境に依らず本番の sqlite_path を使用する方針をコード上に明示。
  - エンジン実行は paper_trading 時に専用 DB を使用して本番と分離。

### 修正（バグ・堅牢性）
- 環境変数パーサの強化
  - .env パーサが export プレフィックス、引用符付き文字列、バックスラッシュエスケープ、インラインコメントの扱いに対応。より実運用での互換性を向上。
- 停止制御
  - run_execution / run_monitoring で共通して stop flag（data/stop_requested.flag）を監視し、安全に停止するフローを実装。
- エラー耐性
  - ポーリングループ内 check_once() が例外を吐いてもループを継続するよう try/except で保護（ログ出力）。

### 既知の制限・注意点
- research.factor_research は DuckDB 上の prices_daily / raw_financials に依存しており、入力データの欠落は None を返す設計。必要に応じて前日の価格等を使ったフォールバックは未実装。
- position_sizing の lot_size は現状全銘柄共通の引数として扱う。将来的に銘柄別 lot_size を参照する拡張を想定。
- process_priority の設定は権限不足（一般ユーザ）だと失敗する場合があり、その場合は警告を出してスキップする。

### ドキュメント
- 各モジュール内に docstring・使用例を追加しているため、CLI の使い方や関数の引数/挙動はファイル内コメントを参照してください。

-----------------------------------------
今後の予定（例）
- ファクター計算の追加指標実装（Value, Liquidity 等の完全化）
- 発注エンジンの詳細なログ・メトリクス追加
- 銘柄別 lot_size 管理、手数料モデルの強化
- ユニットテスト・CI の整備

(以上)