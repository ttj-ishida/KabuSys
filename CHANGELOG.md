# CHANGELOG

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]


## [0.1.0] - 2026-04-18
初回リリース。主要な機能群と CLI / ユーティリティを実装しました。

### Added
- 全体
  - パッケージの初期バージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - DuckDB と SQLite を併用するデータ基盤を採用（設定でパスを指定可能）。
  - ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / app_name に応じた柔軟な設定をサポートし、ハンドラの二重登録を防止。
- 実行用スクリプト
  - 実行エンジン起動スクリプト (run_execution.py)
    - Process 優先度を起動時に "high" に設定する仕組みを導入。
    - 環境に応じて paper_trading 用 DB を分離（KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。
    - BrokerClientFactory を利用したブローカークライアントの生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててデーモン的に実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う制御ループを実装。
  - 監視ポーリング起動スクリプト (run_monitoring.py)
    - SystemMonitor を用いたポーリングループを実装。
    - 環境にかかわらず本番用 sqlite_path を監視 DB として使用（監視は本番 DB を参照する仕様）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は安全にデフォルトにフォールバック）。
    - 停止用フラグ検知と例外ハンドリングにより監視ループの安定稼働を図る。
- 設定管理
  - Settings クラスを実装（kabusys.config）
    - .env の自動ロード機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - .env/.env.local 読み込み順（OS 環境 > .env.local > .env）、OS 環境変数保護の仕組み。
    - 各種設定プロパティの提供（J-Quants トークン、kabu API パスワード、DB パス、Paper Trading 設定、閾値など）。
    - env 値・log level の妥当性検証、paper_fill_mode のバリデーション。
  - 設定ウィザード CLI（kabusys.config_setup）
    - 対話式で .env ファイルを作成・更新するウィザードを提供。
    - シークレット入力のマスク表示、デフォルト値や選択肢の提示、確認後の .env 書き出しを実装。
  - 設定検証 CLI（kabusys.validate_config）
    - .env および config/*.yaml の存在と簡易検証を行う CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、PyYAML があれば YAML のパース検証を実施。
    - --strict オプションで警告を失敗扱いにできる。
- ユーティリティ
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX の差を吸収して nice 値や HIGH_PRIORITY_CLASS 相当を設定。
    - CPU affinity を最初の N コアに固定する関数を提供（権限がない場合は警告を出してスキップ）。
  - ロギング設定ユーティリティ（上記）。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - 候補選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順かつタイブレークに signal_rank を用いる。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分、全スコアが 0 の場合は等分配へフォールバック（警告ログ）。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有のセクター露出が閾値超過のセクターを新規候補から除外。unknown セクターは除外の対象外。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数（デフォルト 1.0、未知のレジームは警告のうえ 1.0 でフォールバック）。
  - 株数決定・単元丸め（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method("risk_based","equal","score") に対応した株数算出ロジックを実装。
    - risk_based: リスク・ストップロスを用いた株数算出と per-stock 上限（max_position_pct）適用。
    - equal/score: ウェイトに基づく割当て、lot_size（単元）で丸め。
    - aggregate cap: 全体投資額が available_cash を超える場合にスケーリングし、端数は残差順で lot 単位の追加配分を行う。
    - cost_buffer を考慮した保守的なコスト見積り。
- Execution 周辺（リスク設定）
  - RiskManager の初期化に用いるデフォルト RiskConfig を実装（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - 初期ポートフォリオ値として broker.get_available_cash() を使用。
- 監視 DB 初期化
  - init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等に初期化）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を読み、稼働率・注文成功率・送信率・レイテンシ（P95 含む）などを集計してレポート出力。
    - 判定基準（稼働率 >= 99%、注文成功率 >= 90% 等）に基づく PASS/FAIL 判定を実装。
    - P95 パーセンタイル算出ロジックを実装（存在しない場合は N/A 表示）。
    - コマンドライン引数で期間（--from/--to）や DB パス（--db）を指定可能。

### Changed
- N/A（初回リリースのため過去変更なし）

### Fixed
- N/A（初回リリースのため過去修正なし）

### Security
- 環境変数読み込み:
  - .env 自動読み込み時に OS 環境変数を保護（既存値は上書きしない / .env.local は override=True だが protected により OS 環境は保護）する設計により、意図しない上書きを防止。

---

注:
- リリースに含まれる各モジュールは、テストや実行環境での動作確認を前提としています（例: psutil 権限やファイルシステムの書き込み許可など）。
- 一部モジュール（例: research/factor_research.calc_momentum）は長大な実装を含む設計になっており、今後の追加改善・テストを推奨します。