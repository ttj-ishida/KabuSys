CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" のフォーマットに準拠します。
タグ付けはセマンティックバージョニングに従います。

[Unreleased]
------------

(なし)

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アプリケーション初期リリースを追加。
- 起動スクリプト / 実行系
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッドでエンジンを実行し、data/execution.pid に PID を書き込む仕組みを想定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（data/paper_trading.db）を使用して本番 DB と完全に分離する設計。
    - BrokerClientFactory を用いて環境に応じたブローカークライアントを生成。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor を定期ポーリングで実行する監視スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ検知時のループ終了処理を実装。
    - monitoring は環境に依らず本番用 sqlite_path を使用する挙動を明示。
- 設定・環境管理
  - src/kabusys/config.py
    - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env のパース機能を強化（export プレフィックス対応、クォート値のエスケープ対応、インラインコメント処理等）。
    - Settings クラスを追加し、アプリで利用する各種設定値（J-Quants / kabuAPI / DB パス / モニタ閾値 / 環境判定等）をプロパティで提供。
    - PAPER_FILL_MODE の検証、環境判定（development/paper_trading/live）のバリデーションを実装。
    - settings = Settings() のシングルトンを提供。
  - src/kabusys/config_setup.py
    - 対話式の .env 作成ウィザードを追加（項目のプロンプト、シークレットのマスク表示、.env への書き込み）。
  - src/kabusys/validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パスの親ディレクトリ、config/*.yaml ファイル存在・パース（PyYAML が存在する場合）等を検証。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging() を追加。コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリの自動作成、既存ハンドラのクリア、ログレベル解決ロジックを実装。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（Windows と POSIX の差分吸収）を実装。
    - CPU affinity をプロセスに固定する set_cpu_affinity() を提供。
- ポートフォリオ構築ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄候補選定 select_candidates, 等重み calc_equal_weights, スコア重み calc_score_weights を追加。スコア全てが 0 の場合のフォールバックロジックを実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中制限による候補除外）を追加。売却予定コードの除外や unknown セクター扱いの扱いを明記。
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）を追加。"bull"/"neutral"/"bear" をマッピング、未知のレジームはログ警告と 1.0 フォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes を追加。allocation_method による分岐（"risk_based" / "equal" / "score"）を実装。
    - 単元株（lot_size）丸め、1銘柄上限・集計上限（aggregate cap）でのスケーリング、cost_buffer を考慮した保守的見積り、残差分配ロジックを実装。
- 監視・検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH の DB を読み、稼働率、注文成功率、送信率、レイテンシ（P95）等を計測し PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
- 研究用モジュール（雛形）
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity の設計方針と定数設定）。関数 calc_momentum の導入（実装途中の箇所あり）。

Changed
- プロジェクト構成
  - パッケージ初期バージョンとして __version__ = "0.1.0" を設定。
  - __all__ に主要サブパッケージを列挙（data, strategy, execution, monitoring）。
- .env 読み込みポリシー
  - OS 環境変数の上書きを防ぐ保護機構（protected set）を導入。読み込み順は OS 環境 > .env.local > .env。

Fixed
- 設定・堅牢性
  - MONITOR_POLL_INTERVAL の値検証（0 以下や非整数はデフォルトにフォールバック）を追加し、time.sleep に渡る不正値を回避。
  - logging_setup においてログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、標準出力のみで継続する耐障害性を強化。
  - process_priority の実行時例外（権限不足等）を警告として扱い、プロセスを停止させないように変更。
  - validate_config における YAML 検証は PyYAML が存在しない環境ではスキップし、警告を出すようにした。

Security
- 機密情報取り扱いの配慮
  - config_setup のプロンプトでシークレット項目はマスク表示。README 等に記載が必要な点を意識した設計。

Notes / Known issues
- research/factor_research.py の calc_momentum 実装は途中（ファイル末尾で未完了）であり、将来的な実装継続が必要。
- Position sizing や sector cap の一部ロジックは price が欠損（0.0）を想定した注意コメントがあり、前日終値や取得原価を用いたフォールバック等の拡張を検討する余地がある。
- 実際の本番運用では KABUSYS_ENV=live の慎重な設定、LINE 通知設定の充実、Kill Switch の取り扱い（KILL_FLAG_CLEAR_ON_START）など運用オペレーションの整備が必要。

References
- 各 CLI:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 起動スクリプト（デーモン等から利用想定）:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

（以上）