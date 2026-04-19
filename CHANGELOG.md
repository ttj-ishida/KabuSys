# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース

### Added
- 全体
  - パッケージ初期バージョンを追加。パッケージバージョンは src/kabusys/__init__.py にて `0.1.0` を定義。
- 実行 / 運用
  - 監視プロセス起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループを終了。
    - 監視は環境に関わらず本番の sqlite_path を使用する旨を明記。
    - SQLite（監視 DB）および DuckDB への接続と初期化処理を組み込み。
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）を使用する旨をサポート（BrokerClientFactory によりモックブローカー実装を生成）。
    - 停止フラグ (data/stop_requested.flag) を検知して実行エンジンを安全停止。
    - PID ファイル管理（data/execution.pid）対応。
- 設定管理 / 初期化
  - Settings クラス: src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルート検出）、環境変数読み取りと各種プロパティ（DB パス、ログレベル、しきい値、paper モード設定等）を提供。
    - PAPER_FILL_MODE（instant／partial／never／reject）など Paper Trading に関する設定を検証。
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）。
    - デフォルトパス（DuckDB/SQLite/PID ファイル 等）を明示。
  - .env ウィザード: src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 秘匿項目のマスク表示、選択肢・デフォルト値のサポート、保存確認機能を実装。
  - .env 及びその他設定検証ツール: src/kabusys/validate_config.py
    - 必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml ファイルの存在・本番環境向けガードチェック等を行う CLI を追加。
    - `--strict` オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み付け: src/kabusys/portfolio/portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を追加。スコアが全て 0 の場合は等金額配分にフォールバック。
  - セクター制限・レジーム乗数: src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中上限適用）、calc_regime_multiplier（レジームに応じた投下資金乗数）を追加。未知レジーム・未知セクターのフォールバック動作を定義。
  - 発注株数算出・リスク制限: src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes を追加。allocation_method（risk_based / equal / score）に応じた株数計算、lot_size（単元）対応、aggregate cap によるスケールダウンと端数処理（lot 単位での再配分）を実装。
- ユーティリティ
  - ロギング設定ユーティリティ: src/kabusys/utils/logging_setup.py
    - stdout 出力（StreamHandler）と日次ローテート（TimedRotatingFileHandler）をルートロガーに統一的に設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル・出力ディレクトリの解決ルールを実装。
  - プロセス優先度 / CPU affinity ユーティリティ: src/kabusys/utils/process_priority.py
    - set_process_priority（Windows / POSIX 対応、権限不足などで安全にフォールバック）と set_cpu_affinity（最初 N コアに固定）を提供。
- ツール
  - Paper Trading 検証レポート: src/kabusys/tools/paper_verification_report.py
    - ペーパートレード DB を集計して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出し PASS/FAIL 判定を行うレポート生成 CLI を追加。
    - P95 計算、期間フィルタ、しきい値（デフォルト）を備える。
- リサーチ
  - ファクター計算モジュール（初期実装途中）: src/kabusys/research/factor_research.py
    - DuckDB の prices_daily / raw_financials を用いたモメンタム等の定量ファクター計算枠組みを追加（calc_momentum 等を実装予定、途中実装あり）。
- DB 初期化
  - 監視用テーブルの冪等な初期化呼び出し（init_monitoring_db）を run_monitoring/run_execution 起動経路で保証。

### Changed
- 設計 / 実行方針
  - 監視プロセスは KABUSYS_ENV に依存せず、常に production 相当の sqlite_path を参照する設計とした（安定監視のため）。
  - ExecutionEngine は paper_trading モード時に本番 DB と分離された専用 SQLite を使用することで本番発注とペーパートレードを完全分離。

### Fixed
- .env パースの堅牢化: src/kabusys/config.py
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応して .env 解析を改善。
  - プロジェクトルート探索を __file__ 起点の親ディレクトリ列挙で行うようにし、配布後も CWD に依存しない読み込みを実現。
- ログ設定の安全化: src/kabusys/utils/logging_setup.py
  - ログディレクトリ作成に失敗した場合にファイルハンドラ生成をスキップし、コンソール出力のみで継続するよう安定化。

### Known issues / Notes
- position_sizing.calc_position_sizes
  - price が欠損（0.0 等）の場合に保守的にスキップするが、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
  - lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map へ拡張する予定。
- research/factor_research.py はモジュールの途中実装を含む（calc_momentum の実装が途中で切れている）。以降のリリースで完成予定。
- run_monitoring/run_execution の動作は環境（権限や OS）に依存する処理（プロセス優先度設定、CPU affinity 等）があり、権限不足時は警告を出してスキップする設計。

### Security
- 特にセキュリティ修正は含まれません。

----

参考: 主要な CLI
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証:     python -m kabusys.validate_config [--strict]
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 監視プロセス起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時は追加の変更・修正点を反映してください。）