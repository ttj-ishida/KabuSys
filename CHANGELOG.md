CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 基本ライブラリ構成を追加（初回リリース）。
  - パッケージ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
- 起動スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) による整然とした終了。
    - Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する旨を明記。
    - DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db、環境変数で上書き可）を使用し、MockBrokerClient を利用する設計を採用。
    - 停止フラグ / PID ファイル管理、デーモンスレッドでの実行と安全な停止処理を実装。
- 設定管理:
  - src/kabusys/config.py
    - Settings クラスを導入（環境変数経由の設定取得）。
    - .env 自動読み込み機能（プロジェクトルート判定：.git または pyproject.toml を探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env のパースを強化（export プレフィックス、クォートとバックスラッシュエスケープ、インラインコメント処理に対応）。
    - 各種デフォルト値・検証（env 値・LOG_LEVEL 等）を提供。
- 環境設定支援ツール:
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定など）と出力テンプレートを提供。
- 設定検証ツール:
  - validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 検証、ログレベル検証、ファイルパス存在チェック、YAML のパース確認（PyYAML が存在する場合）などを実行。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング・ユーティリティ:
  - utils/logging_setup.py
    - setup_logging 関数を追加。全起動スクリプトから共通で使用可能。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度ユーティリティ:
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - Windows / POSIX の差分を吸収し、アクセス権限不足や未対応 OS の場合はフォールバックして警告を出す安全な設計。
- ポートフォリオ構成モジュール:
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - calc_score_weights は全スコアが0の場合に等金額配分へフォールバックし警告ログを出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用関数 apply_sector_cap を追加（既存保有のセクターエクスポージャーを計算し上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を追加（bull/neutral/bear マッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes を追加。allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。
    - lot_size（単元株）処理、max_position_pct、max_utilization、cost_buffer を用いた aggregate cap スケーリングと再配分アルゴリズムを実装。
    - 不足データ（価格が0または未取得）の場合はスキップしてログ出力。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py
    - paper_trading DB を解析して検証レポート（稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）など）を生成する CLI を追加。
    - レポートの Pass/Fail 基準（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を実装。
    - --from/--to/--db オプションをサポート、P95 計算の実装あり。
- DuckDB / SQLite 統合:
  - 起動スクリプトや解析ツールは DuckDB および SQLite への接続設定を備える（Settings 経由でパス取得、デフォルトは data/ 以下）。
  - init_monitoring_db 呼び出しにより監視テーブルの存在を保証（冪等）。
- 研究用モジュール（着手）:
  - research/factor_research.py
    - モメンタム等のファクター計算フレームワークの骨組みを追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
    - 定数と関数シグネチャ、設計注釈を含む（部分実装）。

Changed
- （初回リリースのため該当なし）

Fixed
- .env のパースを強化してより堅牢に（クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いなど）。

Security
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化可能（テストや CI の安全性向上）。
- config_setup により .env の生成／管理を容易にして誤コミットを防ぐ注意書きを出力。

Notes / その他
- 監視・実行プロセスは起動直後にプロセス優先度を "high" に設定するようになっている（set_process_priority を使用）。権限不足や未対応 OS では警告を出し設定をスキップする。
- run_execution は paper_trading 環境向けに本番 DB と完全分離された専用 SQLite を使用する想定（PAPER_TRADING_SQLITE_PATH で上書き可能）。
- apply_sector_cap のエクスポージャー計算は価格が欠損した場合に過少評価する可能性がある旨の TODO コメントあり（将来的に前日終値等でのフォールバックを検討）。
- README やドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への参照がソース中に記載されており、設計仕様に基づいた実装になっている。

過去のバージョン
----------------
- （初回リリース）