# Changelog

すべての重要な変更点を記録します。これは Keep a Changelog の形式に準拠しています。

履歴は変更履歴として推測に基づき作成しています（コードベースの内容から抽出）。

## [Unreleased]

## [0.1.0] - 2026-04-20

### Added
- 基本パッケージ初期リリース: KabuSys 自動売買システム（__version__ = 0.1.0）。
- 環境設定・読み込み
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。OS環境変数を保護する仕組みあり（.env / .env.local の読み込み順と上書き挙動）。
  - 環境変数行パーサを詳細に実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート）。
  - Settings クラスを追加し、アプリケーション全体で利用する設定 API を提供（J-Quants / kabu API / DB パス / Paper Trading 関連 / 監視閾値 等）。
- 対話式セットアップ
  - config_setup ウィザード（python -m kabusys.config_setup）を追加。対話式に .env を作成・更新する機能、シークレットマスク表示、デフォルト/選択肢のサポート、.env の安全な書き込みを提供。
- 設定検証
  - validate_config CLI（python -m kabusys.validate_config）を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスや config/*.yaml の存在チェック、--strict オプション（警告を失敗扱い）を実装。
- ログ管理
  - setup_logging ユーティリティを追加。ルートロガーに stdout StreamHandler と日次ローテーションの TimedRotatingFileHandler を設定。LOG_DIR / LOG_LEVEL の解決順を提供し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック。
- プロセス制御ユーティリティ
  - set_process_priority(level) を追加（Windows と POSIX を吸収）。アクセス権限や未対応 OS の場合は警告を出し安全にスキップ。
  - set_cpu_affinity(cpu_count) を追加し、プロセスの CPU affinity を設定（存在しない場合や権限不足での安全なフォールバック）。
- 実行用スクリプト
  - run_execution.py を追加。ExecutionEngine の起動スクリプトを提供。起動時にプロセス優先度を高く設定、SQLite/ DuckDB 接続の確立、Broker クライアントの生成、OrderManager / RiskManager / Reconciler の組み立て、別スレッドで engine.run_session を実行、停止フラグ (data/stop_requested.flag) の監視による安全停止、paper_trading 時は専用 SQLite（data/paper_trading.db）を使用する分離を実装。
  - run_monitoring.py を追加。SystemMonitor ポーリングループを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず production 用 sqlite_path を使用する設計。停止フラグの検知、例外時のログ出力、DuckDB 接続の確立を行う。
- ポートフォリオ構築モジュール
  - portfolio モジュールを追加。純粋関数群で構成（DB に依存しない）。
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークに signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装（スコア全て 0 の場合は等配分へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有の時価を元に当日売却予定銘柄を除外する挙動）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知値は警告の上 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。リスクベース算出、単元株（lot_size）丸め、1銘柄上限・総投下資金上限・cost_buffer（手数料・スリッページ想定）を考慮した aggregate cap スケーリングを実装。使用可能現金を超える場合にスケールし、端数配分ロジックを持つ。
- 研究（Research）モジュール（部分実装）
  - research/factor_research.py：DuckDB の prices_daily / raw_financials を使ったファクター計算の骨組み（モメンタム・MA200乖離・ATR 等）を実装予定の設計。モジュール内に定数と calc_momentum の雛形が含まれる（実装途中）。
- ツール
  - tools/paper_verification_report.py を追加。ペーパートレード用 SQLite から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ P95 等）を集計して標準出力レポートを生成。閾値による PASS/FAIL 判定、期間フィルタ（--from / --to）、--db オプション / 環境変数優先解決をサポート。

### Changed / Improved
- DB 周りの安全性強化
  - run_execution/run_monitoring と共通で DuckDB + SQLite を利用する設計。monitoring の初期化は起動環境に依らず本番 sqlite_path を利用する旨を明確化。
  - init_monitoring_db 呼び出しは冪等に実行して監視テーブルの存在を保証する。
- ロギング / エラーハンドリング
  - logging_setup は既存ハンドラの flush/close と削除を行い二重ハンドラを防止。ログディレクトリ作成失敗やファイルハンドラ作成失敗をログ（警告）に落とし、コンソールのみで継続する堅牢性を実装。
- 設定検証のユーザビリティ向上
  - validate_config で PyYAML 未インストール時に YAML の検証をスキップし警告を出す。設定ファイルが存在しない場合の案内メッセージを追加。
- 実行時安全ガード
  - run_execution は起動時に既に停止フラグが立っている場合は起動を行わない。稼働中に停止フラグを検知したら engine.stop() を呼ぶ制御フローを実装。
- 環境変数処理の堅牢化
  - .env パーサはコメント・クォート内のエスケープ処理、export プレフィックス対応などを実装。読み込み失敗時は警告を出して継続。

### Fixed
- ファイル/ディレクトリ作成失敗時のフォールバックを明確化（ログディレクトリ不作成時にファイル出力をスキップし stdout のみで継続する挙動を安定化）。

### Security
- .env ファイルを絶対にコミットしない注意喚起を config_setup の生成ヘッダに明記（.env を扱うワークフローの安全性周知）。

---

注: 本 CHANGELOG は提供されたコードベースの内容を元に推測して作成しています。実際のリリースノート作成時は追加の変更点・バグ修正・マイグレーション手順等を合わせて確認してください。