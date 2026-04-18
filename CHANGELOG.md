# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
現在のリリースは 0.1.0（初期リリース）です。

## [Unreleased]

### Added
- （今後の変更履歴をここに記載）

---

## [0.1.0] - 2026-04-18

初期リリース。以下の主要機能とユーティリティを追加しました。

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。設定に応じて本番または Paper Trading 用ブローカークライアントを生成し、専用の SQLite（Paper Trading の場合は data/paper_trading.db）および DuckDB を利用してセッションを実行します。
    - 起動時にプロセス優先度を "high" に設定します（set_process_priority を呼び出し）。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を用いた安全な起動・停止制御を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループ終了、例外発生時はログ出力して次ポーリングへ回復する構造。

- 設定管理・CLI
  - config.py
    - .env 自動読み込み機能をプロジェクトルート（.git または pyproject.toml）から実施。OS 環境変数を保護しつつ .env / .env.local を適切な順序で読み込みます。
    - .env の行パースロジックを強化（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの判定など）。
    - アプリ設定を Settings クラスで提供（DB パス、Paper Trading 関連設定、監視閾値、KABUSYS_ENV/LOG_LEVEL 判定など）。
    - Paper Trading 向けの PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。必須項目・デフォルト・説明を表示して安全に .env を作成可能。
  - validate_config.py
    - 起動前の設定チェック CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML が存在する場合）などを実施。
    - --strict オプションで警告も失敗扱いにできる。

- モニタリング関連
  - monitoring_db 初期化処理（init_monitoring_db）を導入し、run_* スクリプト起動時に監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等金額配分にフォールバックする挙動を保持。
  - portfolio/position_sizing.py
    - 発注株数算出ロジック（risk_based / equal / score）を実装。lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積）対応、aggregate cap によるスケールダウンと残差配分ロジックを導入。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有と当日売却予定を考慮して候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマップ、未知レジームはフォールバック）。

- 研究系 / データ処理
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Volatility / Liquidity 等のファクター計算を行うモジュールを追加。prices_daily テーブルを参照してモメンタム（1M/3M/6M、MA200乖離）、ATR 等を計算する関数群を提供。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。指定期間の system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・P95 レイテンシなどを計算して PASS/FAIL を判定します。複数の閾値はスクリプト内で定義（例: 稼働率 >= 99%）。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度および CPU affinity を設定するユーティリティを実装。psutil を利用し、失敗時は警告を出してフォールバック。
  - パッケージメタ情報
    - __version__ = "0.1.0" を追加。

### Changed
- N/A（初期リリースのため既存機能の変更なし）

### Fixed
- N/A（初期リリース）

### Security
- 環境変数取り扱い
  - config_setup で生成される .env に関する注意書きを記載（.env を Git にコミットしないことを明示）。

### Notes / Behaviors
- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、run_execution は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データベースと完全分離して動作します。
- 監視ループの堅牢性
  - run_monitoring は停止フラグ / KeyboardInterrupt / check_once() 内の例外を適切にハンドリングし、DB コネクションを必ずクローズします。
- .env 自動ロード
  - OS 環境変数を優先しつつ、プロジェクトルートから .env/.env.local を読み込む自動ロード機能を提供。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。
- ロギング
  - 多くのモジュールで logging を利用し、重要な操作やフォールバック時に警告・デバッグ情報を出力します。

---

（今後の変更は Unreleased セクションに追記してください）