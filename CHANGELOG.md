# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
タグ付けやリリース履歴管理に利用してください。

## [Unreleased]

（現時点では未リリースの差分はありません）

## [0.1.0] - 2026-04-18

初期リリース。KabuSys の基盤機能群を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` に `__version__ = "0.1.0"` として追加。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 停止制御にプロジェクト配下 `data/stop_requested.flag` を使用。
    - sqlite（監視 DB）および DuckDB への接続を確立して監視データを記録。
    - プロセス優先度を高（"high"）に設定する処理を起動時に実行。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper_trading DB を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderManager / Reconciler / RiskManager 組み立てと ExecutionEngine 起動を実装。
    - 停止フラグ（data/stop_requested.flag）検知でセッションを安全に停止。
    - 実行 PID ファイル（data/execution.pid）に対応。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順と上書きポリシー（OS 環境変数保護）を実装。
    - .env パースはシングル/ダブルクォートや export プレフィックス、インラインコメントを考慮して安全に処理。
    - Settings クラスを実装し、各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）をプロパティとして提供。
    - 環境（KABUSYS_ENV）、ログレベル（LOG_LEVEL）などの検証とデフォルト値を実装。
    - 自動 .env 読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）と入力プロンプト、既存値の読み込み・マスク表示、確認・保存処理を提供。
    - .env を標準的なテンプレート形式で書き出す `_write_env` を実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須/任意環境変数確認、パスの親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML があれば構文チェック）などを実施。
    - `--strict` オプションで警告を失敗扱いにできるように実装。
    - 本番（KABUSYS_ENV=live）に対する追加ガード（LINE 通知設定のチェックや KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ユーティリティ
  - logging_setup.py
    - ルートロガーの統一的セットアップ関数 `setup_logging` を追加。
    - stdout 出力用 StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（<log_dir>/<app_name>.log）を設定する。
    - LOG_DIR 環境変数、LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時はファイル出力を無効化してフォールバック。
  - process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（`set_process_priority`）を実装。psutil を使用し、失敗時は警告を出してスキップ。
    - CPU affinity 固定用の `set_cpu_affinity` を提供（利用可能コア数より多い指定時の挙動や権限不足時のフォールバックを実装）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - `select_candidates`（スコア降順で候補選定）を実装。
    - `calc_equal_weights`（等金額配分）、`calc_score_weights`（スコア比率に基づく配分、全スコア 0 の場合はフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - `apply_sector_cap`（セクター集中上限チェック、当日売却予定銘柄を除外、unknown セクターは除外対象外）を実装。
    - `calc_regime_multiplier`（market regime による投下資金乗数、'bull'/'neutral'/'bear' をマッピング、未知レジームはフォールバック）を実装。
  - portfolio/position_sizing.py
    - `calc_position_sizes` を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer による保守的な見積り、残差処理による追加配分ロジックなどを実装。

- Execution / Risk defaults
  - run_execution.py 内で RiskManager のデフォルト設定を定義（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。初期ポートフォリオ値は broker.get_available_cash() を使用。

- 監視・モニタリング DB
  - init_monitoring_db が監視用テーブル存在を保証して起動時に呼び出される（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から統計を集計して検証レポートを標準出力に生成する CLI を提供。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）等。
    - P95 計算、日付フィルタ（--from / --to）、閾値判定（稼働率 >= 99%。等）に基づく PASS/FAIL 判定を実装。
    - DB が存在しない場合のエラーメッセージを提供。

- 研究用モジュール
  - research/factor_research.py（ファクター計算の骨子を追加）
    - モメンタム / MA / ATR / 流動性系ファクターの計算方針と定数を定義。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計方針を実装（関数テンプレートや計算定数を含む）。

### Changed
- ロギングの一貫化
  - 全起動スクリプトから `setup_logging(app_name=...)` を呼ぶことでログ出力形式とローテーションを統一。

- DB パスの分離
  - 実運用/ペーパートレードで SQLite DB を分離（`Settings.paper_sqlite_path` を用意、run_execution で `settings.is_paper` に応じて切り替え）。

### Fixed
- .env のパース頑健化
  - クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いなどに対応し、不正行をスキップする実装により .env 読み込みの堅牢性を向上。

### Security / Safety
- 本番起動時のガード
  - validate_config により本番（KABUSYS_ENV=live）での注意喚起（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START 等）を行う。
- Kill/Stop フラグ
  - 実行プロセスはプロジェクト配下の `data/stop_requested.flag` を監視して安全にシャットダウンする仕組みを採用。

### Notes / Known limitations
- research/factor_research.py はファクター計算の設計と一部実装（定数・インターフェイス）を含みますが、完全実装の詳細は今後の作業対象です（ソース途中で関数が続く可能性があります）。
- process_priority や CPU affinity の設定は権限や OS に依存するため、失敗時は警告を出して処理をスキップする設計です。
- position_sizing の lot_size は現状共通値（デフォルト 100）を想定。将来的に銘柄別単元対応への拡張を想定する注釈あり。

---
開発・運用にあたっては .env.example を参照して環境変数を設定し、`python -m kabusys.validate_config` で事前検証することを推奨します。