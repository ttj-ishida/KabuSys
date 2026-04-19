# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

### Added
- 実行用エントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、PID ファイル管理、停止フラグ検出、スレッドでのエンジン実行ループを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグの検出、DB 初期化、例外ハンドリングを備える。

- 設定管理
  - config.py: Settings クラスを実装。環境変数から各種設定値（API トークン、DB パス、ログレベル、運用モード等）を取得し、値検証を行う。自動 .env ロード機能を実装（プロジェクトルート検出に .git / pyproject.toml を使用）。PAPER_FILL_MODE などの列挙的設定は検証済み。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。既存値の読み込み、シークレット項目のマスク表示、保存確認を実装。

- 設定検証ツール
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、YAML パース（PyYAML を利用可能な場合）や本番環境用のガード（LINE 通知設定や Kill Switch の設定確認）を行う。--strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築ライブラリ
  - portfolio.module を追加:
    - portfolio_builder.py: シグナルの選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合に等金額へフォールバック。
    - risk_adjustment.py: セクター集中上限チェック (apply_sector_cap) と市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。未知レジーム時のフォールバックと警告出力を追加。
    - position_sizing.py: position sizing ロジックを実装（risk_based / equal / score の各方式）、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積）対応、端数配分ロジックを実装。最大ポジション比率・利用率等のパラメータにより上限制御を実施。
  - portfolio/__init__.py により上記関数群を公開。

- 監視・ペーパートレード用ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ(P95) を集計し PASS/FAIL を判定。日付フィルタ、DB パス上書きオプションを提供。閾値は定数化（稼働率、成功率、P95 等）。
  - Execution 起動時に Paper Trading 環境（KABUSYS_ENV=paper_trading）の場合は Mock 用 DB（data/paper_trading.db）への記録を行う設計が反映されている（設定分離）。

- 汎用ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。コンソール stdout 出力と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR / LOG_LEVEL 等の解決順を実装。ディレクトリ作成失敗時のフォールバック処理を備える。
  - utils/process_priority.py: プロセス優先度設定（Windows / POSIX 差分吸収）と CPU affinity 設定を追加。psutil を利用し、アクセス拒否や未対応環境では警告を出してスキップ。
  - utils パッケージにて上記ユーティリティを提供。

- DB 初期化/接続
  - run_* スクリプトや各モジュールで sqlite3 / duckdb 接続を統一的に扱う実装を追加。監視用テーブルの冪等な初期化（init_monitoring_db）フローを導入。

- パッケージ基礎
  - __init__.py にパッケージバージョン __version__ = "0.1.0" を追加。

### Changed
- なし（初期リリースに相当するため、破壊的変更なし）

### Fixed
- なし（初期リリース）

### Security
- なし

---

## [0.1.0] - 2026-04-19

初回公開リリース。上記「Added」に記載の機能群をまとめてリリース。

- 監視 (monitoring) と実行 (execution) の起動スクリプト、設定管理、ウィザード、検証ツールを提供。
- ポートフォリオ構築、リスク調整、ポジションサイズ計算の純粋関数群を提供（DB に依存しない設計）。
- Paper Trading 向けの検証レポート生成ツールを提供。
- ロギング・プロセス優先度など運用面のユーティリティを整備。
- DuckDB / SQLite を用いた分析/監視データパイプラインの基礎を実装。

### Notes / Known issues / TODO
- risk_adjustment.apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価の利用）は TODO コメントとして残してあります。
- position_sizing は現状全銘柄で共通の lot_size（単元株）を想定している。将来的に銘柄毎の lot_map 対応を検討中（TODO コメントあり）。
- research/factor_research.py はファクター計算の骨組みを含むが、一部実装が継続中（ファイル末尾が未完）。今後のリリースで補完予定。

---

(参考)
- デフォルトのファイルパスや閾値はソース中のデフォルト値に従います（例: MONITOR_POLL_INTERVAL=60, DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db 等）。