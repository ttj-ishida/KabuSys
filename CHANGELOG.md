# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」準拠です（https://keepachangelog.com/ja/）。

## [Unreleased]
- 今後の変更予定をここに記載します。

## [0.1.0] - 2026-04-18
初回リリース。本リポジトリに含まれる主要機能群を実装しました（コードから推測してまとめています）。

### Added
- 起動スクリプト / 実行環境
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を経由して本番 DB と分離。
    - 実行中の PID 管理（data/execution.pid）および停止フラグ（data/stop_requested.flag）に対応。
    - プロセス優先度を高（"high"）に設定してから起動。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する設計（コードコメントより）。

- 設定・検証・セットアップ
  - config.py
    - Settings クラスで環境変数を一元管理。J-Quants / kabuステーション / DB パス / 監視パラメータ 等をプロパティとして提供。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースはクォート・エスケープ・コメントを考慮する堅牢な実装。
    - PAPER_FILL_MODE の検証や KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実施。
  - config_setup.py
    - 対話式ウィザードで .env ファイルの作成・更新を支援する CLI（デフォルト出力: .env）。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch など主要設定項目をサポート。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、DB パス存在チェック、YAML パース（PyYAML が存在する場合）や本番環境向けガードを実装。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging(app_name, log_dir, level) を提供。stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR に依存する解決ルール、ログディレクトリ作成失敗時はファイル出力をスキップするフォールトトレランスを備える。
  - utils/process_priority.py
    - set_process_priority(level) でクロスプラットフォーム（Windows / POSIX）に優先度設定を試みる。
    - set_cpu_affinity(cpu_count) によりプロセスの CPU アフィニティを設定可能（psutil ベース、権限不足や未対応 OS では安全にスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）と候補除外ロジック。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づく発注株数算出。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer を用いた保守的なコスト見積りを実装。
    - リスクベース算出では stop_loss_pct / risk_pct を考慮。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレードの検証レポート生成スクリプト。
    - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH により上書き可）。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等を計算し、閾値（デフォルト: 稼働率 99%、成功率 90% など）に基づく PASS/FAIL 判定を出力。
    - 日付レンジ指定 --from / --to をサポート。

- リサーチ・ファクター計算（スケルトン）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity を想定したファクター計算モジュールの骨子と多数の定数を実装。
    - DuckDB 接続を受け価格・財務テーブルを参照して計算する設計。
    - （注）モメンタム計算関数の実装が途中で終了している箇所が見られる（ファイル末尾が途切れている / 未完）。

- パッケージ情報
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として設定。

### Changed
- 初回リリースのため「変更」はありません（新規実装に相当）。

### Fixed
- 初回リリースのため「修正」はありません。

### Internals / Notes / Known limitations
- run_monitoring はコメントにより「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明示されており、環境に依らない監視 DB 運用を意図している点に注意。
- config.py の .env 自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。パッケージ配布後の動作も考慮した実装。
- apply_sector_cap のエクスポージャー計算では price_map に 0.0 が含まれる場合に過少見積もりとなる旨の TODO コメントあり。将来的にフォールバック価格の導入が検討されている。
- process_priority / set_cpu_affinity は psutil のアクセス権限や OS サポート状況により実行できない場合があり、その場合は警告を出して安全にスキップする実装。
- logging_setup はログディレクトリ作成に失敗した場合でもコンソール出力のみで継続するため、運用環境によってはログファイルが生成されない可能性がある。
- research/factor_research.py は一部未実装（モメンタム計算の続きを要実装）。

### Breaking Changes
- なし（初回リリース）。

---

注: 上記は提供されたソースコードの構成とコメントから推測して作成したリリースノートです。実際のリリース履歴や変更理由については開発履歴（コミットログ）を参照してください。