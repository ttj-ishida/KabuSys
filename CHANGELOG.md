# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

## [Unreleased]

- なし（初期リリースは 0.1.0）

## [0.1.0] - 2026-04-20

初期リリース。以下の主要機能・ユーティリティを実装しました。

### Added
- コア実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - スレッドで engine.run_session を実行し、停止フラグ（data/stop_requested.flag）を検知したら安全に停止。
    - プロセス優先度を最初に "high" に設定する処理を追加（utils.process_priority）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path（data/monitoring.db 等）を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。check_once() の例外はログ出力して次回ポーリングへ継続。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルートの .env → .env.local、OS 環境変数を保護する優先度・上書き制御）。
    - 複雑な .env パース実装（export プレフィックス対応、クォート中のバックスラッシュエスケープ、インラインコメント処理）。
    - Settings クラスで環境変数をラップし、必須チェック・型変換（パス、フラグ、閾値等）を提供。
    - PAPER_FILL_MODE の妥当性検証、KABUSYS_ENV / LOG_LEVEL の検証等。

  - config_setup.py
    - .env 初期作成・更新の対話式ウィザード。
    - 既存 .env の読み込みと既存値の再利用、シークレット項目のマスク表示、保存時の確認プロンプト。

  - validate_config.py
    - 起動前に .env および config/*.yaml の基本検証を行う CLI。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML パース確認（PyYAML 未インストール時は警告）。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を追加。
    - stdout への StreamHandler（stdout を使用）、日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続するフェイルセーフを実装。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の優先度クラス、POSIX の nice 値）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限・未サポート環境では警告を出してスキップ）。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナルの選定（スコア降順）select_candidates。
    - 等ウェイト calc_equal_weights、スコア加重 calc_score_weights（スコア全てが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有比率が上限を超えるセクターは新規候補を除外）。
    - マーケットレジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出 calc_position_sizes（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）での丸め、ポジション上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的コスト見積り。
    - 各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization 等）を引数で柔軟に指定可能。

- research/factor_research.py
  - DuckDB 接続を受けてファクタ計算を行う設計を追加（Momentum / Value / Volatility / Liquidity 等を想定）。（ファイルは一部実装）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI（PAPER_TRADING_SQLITE_PATH / --db 指定で DB を指定）。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出して Pass/Fail 判定を行う。
    - P95 計算、期間フィルタ、データ欠損時の N/A 表示、閾値はソース中定数で定義（稼働率 99% など）。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Notes / Implementation details
- DB 関連
  - monitoring / execution でそれぞれ sqlite3（監視・orders 等）と duckdb（分析用）を併用。init_monitoring_db を実行して監視テーブルの存在を保証する。
- フェイルセーフ設計
  - ログ出力先やプロセス優先度、CPU affinity 設定、.env 読み込みなどで失敗した場合は警告を出して処理を継続するように設計（運用中に致命的な停止を起こさない目的）。
- 環境変数の扱い
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。OS 環境変数は上書きされないよう保護。
- Paper Trading の分離
  - paper_trading モードでは専用 DB を使い、本番 DB と完全分離することでテストと本番の混同を防止。

---

今後のリリースでは、research/factor_research の完全実装、ExecutionEngine / SystemMonitor の詳細なログ・メトリクス強化、単体テスト追加、戦略設定の YAML 取り込み機能拡充などを予定しています。