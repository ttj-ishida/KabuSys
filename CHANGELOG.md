# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
安定版リリース履歴はセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-19

Initial release — KabuSys の最初の公開バージョン。

### Added
- コア実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db を想定）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）および実行 PID 管理（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番用 sqlite_path を使用して監視テーブルを初期化。

- 設定関連
  - config.py: 環境変数読み込み・設定取得モジュールを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml）を行い、.env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 複雑な .env 行のパースに対応（export 構文、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなど）。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、運用モードフラグ、閾値等）をプロパティとして取得。PAPER_FILL_MODE など妥当性チェックを実施。
  - config_setup.py: .env を対話式に生成・更新するウィザードを追加（CLI）。
  - validate_config.py: 起動前設定検証 CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
    - 必須環境変数・KABUSYS_ENV 値・DB パスの親ディレクトリ・config/*.yaml 存在と YAML パース（PyYAML がある場合）・本番ガード等を確認。

- ポートフォリオ構築モジュール（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア順ソートと上位選出。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を防ぐフィルタ（売却予定銘柄を考慮）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear を定義、未知はフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ）考慮。

- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテート FileHandler（logs/<app_name>.log、30日バックアップ）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールログのみで継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）の差分を吸収し、set_process_priority と set_cpu_affinity を提供。
    - 権限不足や未実装関数が発生した場合は警告を出して安全にスキップ。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトから呼び出し、監視用テーブルの存在を保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を計算して PASS/FAIL 判定。
    - デフォルト DB パスは data/paper_trading.db。--db, --from, --to オプションをサポート。

- リサーチ（ファクター計算）モジュール（開発中）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity の計画を記載）。関数 calc_momentum の実装開始（ファイル末尾で未完の箇所あり）。

### Changed
- パッケージ初期化
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

### Fixed
- 環境変数パースの堅牢化
  - export 構文、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等を .env パーサで適切に処理するよう改善。

### Security
- .env の生成ウィザードに注意喚起を追加
  - config_setup.py で生成される .env の先頭に「.env は絶対に Git にコミットしないこと」を明記。

### Notes / Known issues
- research/factor_research.calc_momentum はファイル終端付近で実装が途中で途切れています（今後のリリースで完成予定）。
- position_sizing の価格フォールバックについて注記あり（price が欠損した場合の過少見積り問題）。将来的に前日終値や取得原価でのフォールバックを検討する旨をドキュメントに記載。
- run_monitoring は監視用 DB として Settings.sqlite_path（本番パス）を常に使用する設計のため、テストで分離が必要な場合は環境変数で sqlite_path を明示的に変更してください。
- process_priority / set_cpu_affinity の動作は実行環境の権限や OS に依存し、設定に失敗した場合は警告でスキップされます。

もしこのリリースノートに追記したい項目（例: 実際の変更日や追加の実装メモ）があればお知らせください。