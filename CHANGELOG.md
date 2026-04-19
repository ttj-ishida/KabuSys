# CHANGELOG

すべての変更は Keep a Changelog の慣例に従い記載します。日付はこのコードベースを確認した日付（2026-04-19）を使用しています。

## [Unreleased]

なし

## [0.1.0] - 2026-04-19

導入: 初期リリース。自動売買システム KabuSys の基礎となる実行・監視・設定・ポートフォリオ・ユーティリティ群を提供します。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - 停止用フラグファイル (data/stop_requested.flag) の検出と PID ファイル (data/execution.pid) 管理に対応。
    - エンジンを別スレッドで実行し、停止フラグ検知で安全に停止するループを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）では環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検出、例外ハンドリング、リソースクローズ処理を実装。

- 設定管理
  - config.py
    - Settings クラスによるアプリケーション設定読み取りを実装（環境変数 / .env / .env.local の自動読み込み、無効化オプションあり）。
    - .env の自動ロードはプロジェクトルート検出（.git または pyproject.toml 基準）に依存し、CWD に依存しない実装。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - 各種設定プロパティを提供（J-Quants, kabuAPI, LINE, DuckDB/SQLite パス, Paper Trading 設定, 監視閾値, 環境 / ログレベル判定 等）。
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - シークレットのマスク表示、選択肢サポート、既存 .env の読み込み・再利用、保存テンプレート出力を提供。

  - validate_config.py
    - 起動前に .env や config/*.yaml の設定不備を検知するバリデータ CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す。
    - --strict オプションで警告を FAIL 扱いにできる。exit code を返す CLI として実装。

- ポートフォリオ構築関連（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順（同点時 signal_rank 昇順）で候補抽出。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックと候補除外。unknown セクターは除外対象外にする挙動。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear、未知は 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate 上限、手数料・スリッページ見積り用 cost_buffer、available_cash によるスケールダウン、端数配分ロジックを実装。
    - 価格未取得時のスキップやログ出力も含む。

- 研究/分析
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨子（モメンタム等の計算を目的、prices_daily/raw_financials を参照）を追加（実装はモジュールに依存）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなど指標の集計と PASS/FAIL 判定（閾値はソース内に定義）。
    - 日付範囲フィルタ、DB パス指定オプション、P95 計算の実装を含む。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の解決ルール、ディレクトリ作成失敗時のフォールバック（ファイルハンドラをスキップ）を実装。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（Windows の優先度クラス / POSIX の nice 値）を設定するヘルパー。
    - CPU affinity 固定関数 set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

### Changed
- （初期リリースにつき該当なし）

### Fixed
- .env 自動ロードの挙動を安定化
  - プロジェクトルート検出を __file__ から辿る実装にし、CWD に依存しないようにしたため、パッケージ配布後の挙動が安定。
- ロギングまわりの堅牢化
  - ログディレクトリ作成に失敗してもコンソールログは出続けるようにし、例外で起動が止まらないようにした。

### Security
- （該当なし）

注記
- 監視プロセスは「環境にかかわらず」monitoring 用 DB（Settings.sqlite_path）を使用する設計になっています。環境分離が必要な場合は設定（SQLite_PATH 等）で明示的に分けてください。
- Paper Trading の DB（paper_trading.db）や挙動は本番 DB と明確に分離されることを前提としています。
- config/.env 関連ファイルは機密情報を含むため、README および生成スクリプトのコメントにもある通り、絶対に Git にコミットしないでください。

----- 

開発や運用で確認したい差分・挙動があれば、対象ファイルや機能を指定していただければ詳細な変更点（実装意図・利用例・注意点）を追記します。