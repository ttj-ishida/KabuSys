# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  
このファイルはリポジトリのソースコードから推測して作成した要約です。

すべてのリリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 初回リリース
公開日: 不明

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）
  - パッケージバージョンは src/kabusys/__init__.py にて `__version__ = "0.1.0"` を設定。

- 起動スクリプト / 実行環境
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 実行中の停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の扱いを実装。
    - スレッドベースでエンジンを実行し、停止フラグ検出で安全に停止。

  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視用 DB の初期化（init_monitoring_db）を実行。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) によるループ終了、KeyboardInterrupt のハンドリング、接続クローズ処理を実装。

- 環境・設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルートを `.git` または `pyproject.toml` から検出）を実装。OS 環境変数を上書きしない動作や .env.local の優先ロード対応。
    - 複数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス /監視しきい値 / システム設定など）。
    - 環境変数の必須チェック用 _require を提供。
    - PAPER_FILL_MODE の妥当性チェック、パスの Path 変換、環境種別チェック（development / paper_trading / live）を実装。
    - settings = Settings() のインスタンスをエクスポート。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を実装。
    - デフォルト値・選択肢・シークレット入力の扱い、既存 .env の読み込みと Enter による既存値継承、最終確認とファイル出力機能を提供。
    - .env のテンプレート出力（コメント付き）を実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な妥当性をチェックする CLI を実装。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が存在する場合）を実施。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築コンポーネント（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全てが 0 の場合は等配分へフォールバック（警告出力）。

  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を実装。既存保有のセクター別時価を計算して上限を超えるセクターの新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear -> 1.0/0.7/0.3、未知レジームは警告の上 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）や cost_buffer の考慮、残差処理の実装。
    - 価格欠損時のスキップやログ出力を考慮。

  - portfolio/__init__.py による公開関数のエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング初期化ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップし、コンソール出力のみで継続。
    - ログレベル / ログディレクトリの解決順（引数 / 環境変数 / デフォルト）を実装。
    - 既存ハンドラのクリーンアップ処理による二重設定防止。

  - utils/process_priority.py
    - Windows と POSIX を吸収するプロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を提供。
    - 権限不足や未対応環境では警告を出して安全にスキップする実装。

- モニタリング / DB 初期化
  - monitoring.monitoring_db.init_monitoring_db 呼び出しにより監視用テーブルの冪等な初期化を実行（スクリプト側で利用）。

- リサーチ / ファクター計算
  - research/factor_research.py（ファクター計算の骨子を追加）
    - Momentum / Value / Volatility / Liquidity 等の計算方針を記載。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。
    - calc_momentum の実装開始（関数定義、定数）、一部ロジックは未完（ソース末尾で切れているため続きが必要）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）から SQLite を読み、システム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して判定（PASS/FAIL）を出力。
    - P95 計算、期間フィルタ、N/A 表示、閾値判定ロジックを実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数のシークレット扱い（config_setup の表示マスク等）を導入。ただし .env を絶対に Git にコミットしない注記を README 相当のテンプレートに記載。

### Notes / 補足事項（実装上の留意点）
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされるため、パッケージ配布後の挙動に配慮済み（CWD に依存しない）。
- run_monitoring は監視 DB に常に本番 sqlite_path を使う設計。紙トレードと監視 DB が分離されていない点に注意（意図的な設計）。
- process_priority の設定は権限や OS に依存するため、失敗時はログ警告でスキップする安全設計。
- position_sizing の aggregate スケーリングや残差配分は lot_size（現状共通 100）前提。将来的に銘柄別単元サイズ対応を想定した TODO が含まれている。
- research/factor_research.py は一部未完の関数が存在（実装継続が必要）。

---

この CHANGELOG はソースコードから推測して作成した概要です。詳細な挙動や追加の変更履歴はコミット履歴／レビュー情報を参照してください。