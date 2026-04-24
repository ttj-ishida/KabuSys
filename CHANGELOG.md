# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリースバージョンはパッケージの __version__ に合わせています。

※ 本ファイルは、リポジトリ内のソースコードを解析して推測した機能・仕様に基づき作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-24

### Added
- 初回リリース: KabuSys 自動売買フレームワーク（日本語ドキュメント風説明に基づく機能群）。
- エントリポイント / 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用分離 DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する想定。
    - duckdb と SQLite の両方に接続（duckdb は分析用、sqlite は監視/発注履歴用）。
    - 停止制御: data/stop_requested.flag を監視し、停止時に Engine.stop() を呼び出す。実行中の PID を data/execution.pid に記録する設計（pid_file を使用）。
    - スレッドで実行されるセッションの監視・安全なシャットダウン処理を実装。
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告の上デフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path（デフォルト: data/monitoring.db）を使用。
    - 停止フラグファイル検出による安全終了、check_once() 内の例外を捕捉してログに残し次回ポーリングへ継続。
- 設定管理
  - config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env のパースは export プレフィックス、引用符付き値、インラインコメント等に対応する堅牢な実装。
    - Settings クラスを導入し、各種設定をプロパティとして提供（J-Quants, kabu API, LINE, DB パス, 監視閾値、実行環境判定等）。
    - 環境変数の必須チェック用 _require ユーティリティを提供。
    - PAPER_FILL_MODE 等のバリデーションを追加（有効値チェック）。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を実装。
    - JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD 等の必須項目を含む項目定義と入力・確認・書き出し機能を提供。
    - 既存 .env の読み込み、シークレットのマスク表示、保存確認を実装。
  - validate_config.py
    - 起動前の設定検証 CLI を実装（--strict モードあり）。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML があれば検証）を行う。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート&上位選抜（スコア降順、タイブレークに signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づく新規候補の除外ロジック。sell_codes を考慮して当日売却予定銘柄は除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。
    - risk_based のリスク計算、max_position_pct/lot_size の考慮、aggregate cap によるスケーリングと残差配分ロジックを実装。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的なコスト見積。
- ユーティリティ
  - utils.logging_setup
    - 統一的なログ設定ユーティリティを追加。StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_LEVEL/LOG_DIR の解決順、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils.process_priority
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。Windows / POSIX (Linux/Mac/FreeBSD) の差分を吸収し、psutil を使って優先度・CPU affinity を設定。権限不足や未対応 OS は警告でスキップ。
- ツール
  - tools.paper_verification_report.py
    - ペーパートレード検証レポート生成ツールを追加。
    - 指標: 稼働率 (uptime), 注文成功率 (fill_rate), 送信率 (send_rate), P95 レイテンシ等を計算し PASS/FAIL 判定を出力。
    - コマンドライン引数 --from/--to/--db と PAPER_TRADING_SQLITE_PATH 環境変数対応。
    - P95 算出、SQL による集計、データ欠損時の N/A ハンドリングを実装。
- 研究用モジュール（途中実装）
  - research.factor_research
    - Momentum 等のファクター計算方針を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計（モメンタム計算ロジックの一部が実装済み）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / Known limitations
- apply_sector_cap:
  - price_map に価格が欠損した場合（0.0 等）、エクスポージャーが過少見積りされる可能性があり、該当箇所に TODO コメントでフォールバック価格導入の検討が示されている。
- process_priority / set_cpu_affinity:
  - 権限不足や一部プラットフォームでは設定が失敗する可能性があり、その場合は警告を出してスキップする実装。
- logging_setup:
  - ログディレクトリの作成に失敗した場合はファイル出力を無効化してコンソール出力のみ継続する仕様。
- .env 自動読み込み:
  - プロジェクトルートの検出に失敗した場合（.git / pyproject.toml が見つからない場合）は自動ロードをスキップする。
  - OS 環境変数は保護（上書き抑止）される挙動。
- paper_verification_report:
  - DB テーブルが存在しない場合（sqlite3.OperationalError）に備え、各クエリを try/except で保護し N/A 等にフォールバックする実装。

---

（以降は将来的なリリースノートの雛形として Unreleased を利用してください）