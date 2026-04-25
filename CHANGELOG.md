# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-25

### Added
- 初回公開（0.1.0）。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（既定: data/paper_trading.db）へ完全分離して記録する動作をサポート。
    - 監視テーブルの冪等初期化（init_monitoring_db）と DuckDB 接続を行う。
    - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。
    - stop フラグ（data/stop_requested.flag）検知で安全にエンジンを停止する仕組み。
    - エンジンはデーモンスレッドで run_session を実行し、PID ファイル管理を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。0 以下や不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する挙動を明示。
    - stop フラグ（data/stop_requested.flag）検知でループ終了、例外はログに出力して次ポーリングへ継続。

- 設定管理
  - config.py
    - .env/.env.local の自動読み込み機構を追加（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - .env パース実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理）。
    - Settings クラスを追加し、環境変数の取得・妥当性チェックを提供（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
    - paper_trading 用の paper_sqlite_path 等のプロパティ提供。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - シークレット項目はマスク表示、デフォルト・選択肢をサポートし、最終確認後に .env を書き出す。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml の存在・パース（PyYAML 利用可の場合）等を検査。
    - --strict オプションで警告を FAIL 扱いにできる（exit code 1）。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプト向けの統一ロギング設定を提供。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定。
    - LOG_LEVEL / LOG_DIR 引数・環境変数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - StreamHandler は stdout を使用（cron/Task Scheduler でのログ取り扱いを考慮）。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（"high"/"normal"/"low"）を追加。Windows / POSIX (Linux, Darwin, FreeBSD) に対応。
    - CPU affinity 設定用の set_cpu_affinity を提供。アクセス権限や未対応環境では警告でスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順に選別。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額へフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）に基づき候補を除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（不明なレジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数の計算。
    - 単元（lot_size）丸め、1 銘柄上限や aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り、端数再配分ロジックを実装。
    - 価格欠損時のスキップやログ出力、将来的拡張の TODO コメントを含む実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し、PASS/FAIL 判定を出力。
    - --from/--to/--db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。
    - P95 算出ロジック、閾値定数（稼働率 99%、成功率 90% 等）を定義。

- リサーチ
  - research/factor_research.py
    - DuckDB を使ったファクター算出モジュール（モメンタム、ボラティリティ、Value などの設計と一部実装）。prices_daily / raw_financials を参照する設計。

- パッケージ情報
  - __init__.py にてパッケージバージョンを 0.1.0 に設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

注意:
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視 DB として常に Settings.sqlite_path（通常は本番用）を使用します。ペーパートレード用の分離 DB を使いたい場合は run_execution 側で paper_sqlite_path を利用してください。