# Changelog

すべての互換性のある変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の規約に従います。
重大バージョン番号はセマンティックバージョニングに従います。

## [Unreleased]

### Added
- 初期リリース相当の主要機能を追加。
  - 実行・監視用スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite を使用する（data/paper_trading.db がデフォルト）。停止フラグと PID 管理、スレッドによるエンジン実行/停止制御をサポート。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - 設定・検証ツール
    - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス等）をサポートし、シークレット項目はマスク表示。
    - validate_config.py: .env と config/*.yaml の設定整合性を事前検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスと YAML ファイルの存在・パースチェック、本番環境向けの追加警告を実装。--strict オプションで警告を失敗扱いにできる。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して PASS/FAIL を判定。期間指定と DB パス指定が可能。
  - 設定管理
    - config.py: .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から自動検出）。読み込み優先度は OS 環境 > .env.local > .env。高度な .env パーサを導入し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスを実装し、各種設定プロパティ（duckdb/sqlite パス、paper_sqlite_path、paper_fill_mode のバリデーション、閾値設定、PID/kill flag パス、環境判定プロパティ等）を提供。
  - ロギング / プロセス制御ユーティリティ
    - utils/logging_setup.py: 一貫したログ設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテートのファイル出力（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 関数を追加。アクセス拒否時は警告を出して安全にスキップする。
  - ポートフォリオ構築ライブラリ
    - portfolio/portfolio_builder.py: 銘柄候補選定（select_candidates）と重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を実装。スコア合計が 0 の場合はフォールバック動作を提供。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。regime による乗数マップ（bull/neutral/bear）を定義し、未知レジームは警告と共にフォールバック。
    - portfolio/position_sizing.py: 発注株数計算ロジックを実装。allocation_method（risk_based / equal / score）に対応し、単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングを実装。リスクベース（risk_based）では stop_loss_pct と risk_pct に基づく計算を行う。
  - research/factor_research.py（初期実装）
    - DuckDB の prices_daily / raw_financials テーブルを参照してモメンタム等のファクターを計算するための骨組みを追加（モメンタム計算等の実装開始）。Note: ファイル末尾に未完の箇所あり（今後の実装継続を想定）。

### Changed
- なし（初回まとめての機能追加のため、後方互換性の破壊は無し）。

### Fixed
- なし（新規実装）。

### Documentation
- 各スクリプト・モジュールに詳細なモジュールドックストリング・使用例を追加。run_*、config_setup、validate_config、paper_verification_report、各 portfolio / utils モジュールに使用方法や注意点を明記。

### Security
- 環境変数やシークレットの取り扱いに注意点を追加（.env を絶対に Git にコミットしない旨を config_setup のテンプレートに明記）。

## [0.1.0] - 2026-04-24
- 本リリースを正式版として初公開（上記 Added に含まれる機能群）。

---

備考:
- run_monitoring/run_execution は停止制御にファイルベースのフラグ（data/stop_requested.flag 等）を使用します。運用時は stop/kill フラグの場所・運用手順に注意してください。
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を設定することで無効化できます（テスト用途を想定）。
- paper_trading 用 DB は本番データと完全に分離される設計（paper_sqlite_path を利用）。ペーパートレードの挙動は PAPER_FILL_MODE により制御されます（有効値: instant/partial/never/reject）。
- 今後の予定: research モジュールの未完部分の実装完了、より詳細なログ/監視メトリクスの拡充、ユニットテストの追加。