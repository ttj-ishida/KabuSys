# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  

注: この CHANGELOG は提示されたコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。本リポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ群・起動スクリプト・ポートフォリオ構築ロジック・設定ツール等を含みます。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番用の sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。
  - run_execution.py
    - ExecutionEngine（発注実行）を起動するスクリプトを提供。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを切り替え（Mock 実装想定）。
    - 停止フラグ（data/stop_requested.flag）/ pid ファイルの取り扱いに対応。
- 設定関連
  - config.py
    - Settings クラスを実装し、環境変数をラップ（プロパティベース）。
    - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - .env の読み込み順序: OS 環境変数 > .env.local > .env。テスト用に自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env のパースはシングル/ダブルクォート、export プレフィックス、行内コメント等に対応。
    - 各種設定プロパティを提供（J-Quants / kabuAPI / DuckDB/SQLite パス / Paper Trading 設定 / 監視閾値 / 環境フラグ等）。
    - `paper_fill_mode` のバリデーション（instant/partial/never/reject）。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を提供。
    - デフォルト値・選択肢・シークレット入力対応、既存 .env の読み込み・再利用に対応。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本チェックを行う CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV の検証、ログレベル・DB パスの検証、YAML パース（PyYAML が利用可能な場合）および本番環境向けの追加ガードを実装。
    - `--strict` オプションで警告も失敗扱いにできる。
- 監視/モニタリング補助
  - monitoring.monitoring_db（参照実装を呼び出し）を初期化する仕組みを起動スクリプトから呼出し、監視テーブルの存在を保証。
- ポートフォリオ構築（純粋関数群、DB参照なし）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点は signal_rank で tiebreak）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中制限。既存ポジションと価格からセクターエクスポージャーを算出し上限を超えるセクターの新規候補を除外）。
    - calc_regime_multiplier（市場レジームに応じた資金乗数。bull/neutral/bear をサポートし未知のレジームは警告のうえフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" に対応）。
    - 単元株（lot_size）丸め、per-position および aggregate のキャップ、cost_buffer による保守的見積り、スケールダウンと残差処理を実装。
- ユーティリティ
  - utils/logging_setup.py
    - アプリ共通のログ設定ユーティリティを実装。
    - stdout 出力用 StreamHandler（stdout 使用）と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 環境変数 LOG_LEVEL / LOG_DIR に対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定ユーティリティ（Windows の priority class / POSIX の nice 値を吸収）。
    - CPU affinity を先頭 N コアに固定する set_cpu_affinity を提供（権限不足等の失敗時は警告でスキップ）。
- ツール / レポート
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等）を集計し、Pass/Fail 判定を行うレポートを生成する CLI。
    - 日付フィルタ（--from / --to）、DB 指定（--db / 環境変数）に対応。
    - P95 パーセンタイル計算、欠損データに対する安全なフォールバックを実装。
- 研究用モジュール（設計・初期実装）
  - research/factor_research.py
    - DuckDB の prices_daily/raw_financials を利用したファクター計算（Momentum / Value / Volatility / Liquidity）の設計を実装。モメンタム計算 calc_momentum の骨組み（horizon 定数など）を含む（ファイル末尾に未完の箇所あり）。

### Changed
- なし（初回リリースのため変更履歴なし）。

### Fixed
- なし（初回リリースのため修正履歴なし）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし。

---

補足 / 注意点（コードベースから推測）
- 監視プロセスは監視 DB として Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用する設計になっているため、ペーパートレード時でも監視 DB が本番用と同一になる点に注意。
- ペーパートレード時の発注データは paper_sqlite_path（デフォルト data/paper_trading.db）に保存するようエンジン側で分離されているため、発注履歴は本番 DB と分離される想定。
- Settings および .env 周りはかなり柔軟なパースを実装しているが、特殊な文字列やエスケープを含む .env のケースは実運用で十分に検証することを推奨。
- research/factor_research.py は一部未完（ファイル末尾が途中で終わっている）ため、ファクター計算の完全実装・検証は今後の作業が必要。

もし特定ファイルについてより詳細な変更点の分割（たとえばマイナーリリースを分ける、改善点と既知の問題を出す等）を希望される場合は、変更履歴の想定基準（コミット単位・機能単位 等）を教えてください。それに合わせて CHANGELOG を分割・詳細化します。