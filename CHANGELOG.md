# Changelog

すべての注目すべき変更は Keep a Changelog の慣例に従って記載しています。  
この CHANGELOG は、与えられたコードベースから実装内容を推測して作成しました。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- ドキュメント化や小さなリファクタの予定メモ（コードベースの現状に基づく将来的改善点）
  - research/factor_research.py が途中で切れている箇所（関数の実装継続が必要）。
  - position_sizing の将来的拡張: 銘柄別 lot_size を受け取る設計への移行予定。
  - monitoring / execution のテスト・例外ハンドリング強化やメトリクス補完処理の追加余地。

---

## [0.1.0] - 2026-04-18

初期公開リリース。以下の主要機能とユーティリティを実装。

### Added
- 全体
  - パッケージ初期バージョンを定義 (__version__ = "0.1.0")。
  - プロジェクトルート自動検出ロジック: .git または pyproject.toml を基準にプロジェクトルートを特定する機能を追加（kabusys.config._find_project_root）。
  - .env 自動ロード機能（.env / .env.local）を実装。既存の OS 環境変数を保護して読み込みを行う仕組みを採用。
  - .env の対話式設定ウィザードを実装（kabusys.config_setup）。
    - J-Quants / kabuAPI / DB パス / LINE 設定など主要項目の対話的初期化・更新が可能。
    - .env の読み書きロジック、シークレットマスク表示、入力補助を実装。
  - 設定検証 CLI を実装（kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV 値検証、DB パス / YAML 設定ファイルの存在チェック、
      本番環境向けの追加ガード（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の確認）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行系 / 監視系
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite を使用して本番 DB と分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、バックグラウンドスレッドでのエンジン実行、停止フラグ監視を実装。
    - エンジンの PID ファイル管理・停止フラグ検知ロジックを搭載。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）を提供。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示（監視 DB の一貫性確保）。
    - 停止フラグの検知でループを終了する制御を実装。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db を利用）を起動時に呼び出し、監視テーブルの存在を保証（冪等）。

- データ・分析
  - DuckDB を使用した分析用接続を採用（Settings.duckdb_path）。実行 / 監視両方で duckdb 接続を確保。
  - research/factor_research.py: モメンタム等ファクター計算モジュール（設計方針、パラメータ定義、calc_momentum の枠組みを実装）。DuckDB の prices_daily / raw_financials を参照してファクター生成を行う想定。

- ポートフォリオ構築
  - portfolio モジュールを提供（純粋関数群・DB 参照なし）。
    - portfolio_builder.py
      - select_candidates: スコア降順＋タイブレークで候補選定。
      - calc_equal_weights / calc_score_weights: 重み計算（スコア全ゼロ時は等分配にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限の適用（当日売却予定の銘柄を除外できる）。
      - calc_regime_multiplier: レジームに応じた投下資金の乗数（bull/neutral/bear のマッピングとフォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定、単元株（lot_size）丸め、aggregate cap スケーリング、残差分配ロジックを実装。
      - cost_buffer を考慮した保守的見積り、max_per_stock（1銘柄上限）や available_cash によるスケールダウンを行う。

- ユーティリティ
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、標準出力のみで継続可能。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX の差分を吸収して nice 値や HIGH_PRIORITY_CLASS 等を設定。
    - set_process_priority("high"/"normal"/"low") と set_cpu_affinity を提供。権限不足等は警告してスキップ。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
    - CLI で期間指定（--from / --to）や DB パス（--db）により、paper_trading DB を集計してシステム安定性 / 注文成功率 / レイテンシ等の指標を出力。
    - P95 計算、閾値（稼働率 / 成功率 / P95 レイテンシ 等）による PASS/FAIL 判定を実装。
    - DB が存在しない場合のエラーメッセージ、テーブル欠如時の耐性（OperationalError を捕捉して N/A 扱い）を実装。

### Changed
- 環境変数処理
  - .env パーサーを堅牢化:
    - export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォートなしの場合のコメント扱い（# の扱いをより厳密に処理）。
    - 値の上書き制御（override / protected）により OS 環境変数を保護。
  - Settings クラスに各種 getter を集約し、型変換や検証を一元管理（env / log_level / paper_fill_mode の検証ロジック等）。
  - PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH のデフォルトと override 設計を明確化。

- 起動ハンドリング
  - run_execution/run_monitoring の起動フローで最初に set_process_priority("high") を呼び出し、安定稼働を優先。

- ロギング動作
  - stdout を標準出力に使用する設計（cron/task scheduler 環境での stdout/stderr リダイレクトを想定）。

### Fixed
- 環境変数の不正値耐性を向上
  - MONITOR_POLL_INTERVAL の不正値（非整数、0 以下）を検知してデフォルトにフォールバックする処理を実装。ログに警告を出力。
  - Settings.paper_fill_mode の不正値チェックを追加（指定可能な値を明示し、不正なら ValueError を発生させる）。
  - Settings.env / log_level の不正値チェックを強化して早期にエラーを出す。

- ファイル/ディレクトリ作成失敗の耐性
  - ログディレクトリ作成やログファイルハンドラ作成に失敗してもコンソールログのみで継続するように変更（起動時ハングやクラッシュを回避）。

### Security
- シークレット取り扱い
  - config_setup の表示や .env 書き込み時にシークレット項目は入力時にマスク表示。README 等に .env をコミットしないよう明記（.env ヘッダコメント）。

### Internal
- コード設計上の方針メモ（実装から推測）
  - portfolio モジュールは純粋関数として設計されており、テスト容易性を重視。
  - DuckDB は分析専用に分離し、実行フロー/監視フローともに副作用を最小化している。
  - risk_manager / execution_engine / order_manager の分離により責務を明確化（依存注入を活用）。

---

注: 本 CHANGELOG は提供されたソースコードの内容から機能・振る舞いを推測してまとめたものです。実際のリリースノートやコミット履歴と厳密に一致しない場合があります。必要であれば、さらにコミットログや設計文書を参照した上で修正・追記します。