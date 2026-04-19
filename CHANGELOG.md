# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

注: 以下の内容は提示されたコードベースから推測して記載したリリースノートです。

## [0.1.0] - Unreleased

### Added
- プロジェクト初期実装を追加。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60秒）。
    - 停止制御ファイル (data/stop_requested.flag) を検知して安全にループを終了。
    - 監視用 DB は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計。
    - duckdb 接続を確立し、init_monitoring_db を呼び出す。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper trading SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（MockBroker を含む想定）。
    - ExecutionEngine をスレッドでデーモン起動し、停止フラグ監視で安全停止。
    - PID ファイル (data/execution.pid) を取り扱う。
- 設定関連
  - config.py
    - .env の自動読み込みロジックを追加（プロジェクトルート検出: .git / pyproject.toml）。
    - .env/.env.local の優先順位制御（OS 環境変数保護付き）。
    - .env パース実装を強化（export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
    - Settings クラスを導入し、環境変数への型変換・検証ロジックを提供（KABUSYS_ENV、LOG_LEVEL 等の検証、PAPER_FILL_MODE の有効値チェックなど）。
    - 各種パス設定（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH など）を Path 型で扱う。
- 設定ユーティリティ
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス存在警告、YAML のパース検証、live 時の追加ガード）。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML 未インストール時の警告出力に対応。
  - config_setup.py
    - 対話式 .env 作成ウィザードを追加（既存 .env の読み込みと Enter による利用）。
    - .env のテンプレート書き込み機能を実装（重要値はマスク表示、秘密項目扱い）。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）実装。既存ポジションと価格情報を元に、上限超過セクターを新規候補から除外。
    - レジーム乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピング、未知値はフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジックを実装（allocation_method: "risk_based", "equal", "score"）。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer を加味したコスト推定、端数配分ロジックを実装。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的ログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順をドキュメント化し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プロセス優先度設定 API を追加（Windows/Linux/macOS を抽象化）。
    - CPU affinity 設定関数を提供（set_cpu_affinity）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定（デフォルト閾値を定義）。
    - コマンドラインで期間フィルタ（--from / --to）や DB パス指定（--db）を受け付ける。
- リサーチ
  - research/factor_research.py
    - ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity 設計方針をコメントで記載）。DuckDB を使用して prices_daily / raw_financials を参照する設計。
    - （注）ファイルは途中まで実装（モメンタム計算開始）で、未完の箇所がある。

### Changed
- ログ出力挙動の統一
  - 全起動スクリプトから setup_logging を呼ぶことでログのフォーマット・ローテーションを統一。
- .env 読み込みの挙動
  - 自動ロード時に OS 環境変数を保護し、.env.local は .env を上書きする挙動を採用。

### Fixed
- 環境変数のパース強化により、クォートやエスケープ、インラインコメントによる誤解釈を修正。
- run_execution の paper_trading 用 DB 分離により、本番 DB への誤操作リスクを軽減。

### Security
- .env 作成時の注意書きを追加（.env を絶対に Git にコミットしない旨を明示）。

### Notes / Known limitations
- research/factor_research.py はモジュール方針・一部実装が含まれるが、ファイル末尾が未完（実装途中）であり、実運用には追加実装とテストが必要。
- apply_sector_cap は price_map に 0.0 が含まれる場合の扱いに TODO コメントがあり、価格欠損時のフォールバック戦略は未実装。
- process_priority の操作は OS/権限に依存するため、権限不足時は動作しないことがある（警告でスキップ）。
- Paper Trading の検証閾値は現状の推奨値を設定しているが、運用環境に応じて調整が必要。

---

（初回リリース向けの概要として、主要な機能追加・設計上の注意点をまとめました。必要であればファイルごとの詳細変更ログや、未実装箇所の TODO リストを追加で出力します。）