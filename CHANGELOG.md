CHANGELOG
=========

すべての注目すべき変更点はここに記載します。フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-04-18

### Added
- 初回リリースを追加。
- 実行エントリ/ユーティリティ:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient による分離された検証が可能。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag によるフラグ検知で行う。監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
- 設定関連 CLI / ウィザード:
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH 等）をサポート。
  - validate_config.py: 起動前設定検証ツールを追加。必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス、config/*.yaml の存在・パースチェック（PyYAML がある場合）などを検査。--strict オプションで警告を失敗扱いにできる。
- 環境変数読み込み:
  - config.py: .env / .env.local の自動ロードを実装（OS 環境変数優先、.env.local は .env を上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化と、読み込み時の上書き保護（protected set）をサポート。export 形式やクォート、インラインコメントの取り扱いに対応するパーサ実装を追加。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を root ロガーに設定。LOG_LEVEL / LOG_DIR / 引数による解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
  - utils/process_priority.py: プロセス優先度（high/normal/low）をクロスプラットフォームで設定するユーティリティを追加。Windows の優先度クラス、POSIX の nice 値に対応。CPU affinity 設定関数 set_cpu_affinity() も実装し、アクセス権限がない場合は警告を出してスキップする。
- ポートフォリオ構築関連（純粋関数群）:
  - portfolio/portfolio_builder.py: 銘柄選定（select_candidates）および重み算出（calc_equal_weights, calc_score_weights）を追加。score が全て 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知レジームはフォールバック（1.0）し警告を出す。
  - portfolio/position_sizing.py: 発注株数算出 calc_position_sizes を追加。allocation_method（"risk_based" / "equal" / "score"）に対応し、単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリングロジックを実装。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- ツール:
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。期間指定 (--from / --to) と DB パス指定 (--db / 環境変数 PAPER_TRADING_SQLITE_PATH) を受け付け、稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL を判定する標準出力レポートを提供。
- 研究用モジュール（骨組み）:
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加。モメンタム、移動平均、ATR、出来高等の指標を DuckDB 上の prices_daily / raw_financials テーブルから計算する設計。計算定数（短期/中期/長期窓、MA200、ATR 期間等）と P95 等ユーティリティを実装済み（一部実装途中）。

### Changed
- - （初回リリースのため該当なし）

### Fixed
- - （初回リリースのため該当なし）

### Notes / Implementation details
- .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮しており、既存 OS 環境変数は保護する設計です。
- run_monitoring は monitoring 用 DB 初期化（init_monitoring_db）を行い、duckdb も接続します。MONITOR_POLL_INTERVAL の不正値は警告してデフォルトにフォールバックします。
- run_execution は起動時にプロセス優先度を "high" に設定し、ExecutionEngine を別スレッドで実行。停止フラグ検知で安全に停止する制御を持ちます。RiskManager の初期設定、Reconciler、OrderManager、OrderRepository 組み立てを行う初期構成が含まれます。
- logging_setup は既存ハンドラのクリーンアップを行ってから再設定するため、複数回のセットアップ呼び出しでもハンドラ重複が起きません。
- position_sizing の aggregate cap スケールダウンでは、lot_size 単位での丸めと端数分配（fractional remainder に基づく追加配分）を実装しており、再現性を保つためソートの安定化を行っています。
- validate_config は PyYAML がない環境でも動作可能で、その場合は YAML のパース検証をスキップして警告を出します。

### Known limitations / Todo
- research/factor_research.py はファクター計算ロジックの実装が途中で、完全実装には更なる SQL/ロジック実装が必要です。
- position_sizing の lot_size は現状全銘柄共通の想定（通常 100）。将来的には銘柄別単元対応を検討（stocks マスタからの参照）。
- apply_sector_cap の価格欠損時（price が 0.0）にエクスポージャーが過少見積りされ得る旨の TODO コメントあり。フォールバック価格の導入を検討すべき。

----------------

（以降のリリースでは変更点を上に追加してください。）