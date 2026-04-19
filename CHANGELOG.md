# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-19

初回公開リリース。以下の主要機能とユーティリティを含みます。

### Added
- 実行／監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。起動時にプロセス優先度を "high" に設定し、BrokerClientFactory を用いて本番またはペーパートレード用クライアントを生成。エンジンはデーモンスレッドで実行され、data/stop_requested.flag を監視して安全に停止できる。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。デフォルトのポーリング間隔は 60 秒で、環境変数 MONITOR_POLL_INTERVAL により上書き可能。監視は環境にかかわらず本番用 sqlite_path を使用する仕様を実装。
- 環境設定管理
  - config.py: .env 自動読み込み（.env, .env.local）機能を追加。プロジェクトルート検出は .git / pyproject.toml を基準に行う。環境変数の厳密チェック用 Settings クラスを提供（各種デフォルト値・バリデーションを含む）。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。一般的な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パスなど）をサポート。
  - validate_config.py: .env と config/*.yaml の検証ツールを追加。必須環境変数やパス、YAML のパース可否、本番環境向けチェック（LINE 通知の有無、Kill Switch 設定など）を行う。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ロジック（純粋関数）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームでのフォールバックとログ出力を含む。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）を実装。allocation_method（risk_based / equal / score）に対応、単元株（lot_size）丸め、aggregate cap によるスケーリング、コストバッファの考慮などを含む。
- 監視・実行のための雑多ユーティリティ
  - utils.logging_setup: 共通のロギング設定を提供。コンソール出力は stdout、日次ローテートのファイルハンドラ（logs/<app>.log、30日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続する堅牢性を実装。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定を提供。権限不足や未対応 OS の場合に警告してスキップする。
- ペーパートレード検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からレポートを生成する CLI を追加。稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）などを集計し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を行う。期間フィルタ（--from / --to）および --db オプションをサポート。
- データ分析（研究）開始
  - research.factor_research: DuckDB 接続を受けてファクター（Momentum / Value / Volatility / Liquidity）を計算するモジュールを追加。モメンタムファクターの計算インターフェースを実装開始（prices_daily テーブル参照）。（実装の一部は途中まで）
- パッケージ情報
  - __init__.py: パッケージバージョンを 0.1.0 に設定し、サブパッケージをエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Behavior
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。ペーパートレードと監視 DB を完全に分離したい場合は設定を見直してください。
- ペーパートレード実行（KABUSYS_ENV=paper_trading）の場合、Execution は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離されます。
- .env の自動読み込みはデフォルトで有効。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env のパースは export プレフィックス・引用符・コメント処理を考慮した堅牢な実装になっています。
- PAPER_FILL_MODE は instant / partial / never / reject のいずれかでなければならず、不正値は例外を発生させます。
- ログはデフォルトで logs/ 配下に出力されますが、ディレクトリ作成に失敗した場合は標準出力のみで継続します。
- process_priority と CPU affinity の設定は権限や OS により失敗する可能性があり、その場合はログで警告してスキップします。

### Known issues / TODO
- research.factor_research のモメンタム関連実装が途中で切れている（未完）。今後のリリースで完成予定。
- position_sizing の価格欠損時の扱い（price==0 のフォールバック）は TODO コメントあり。前日終値等へのフォールバックを検討中。
- 単元株情報（lot_size）を将来 stocks マスタに持たせて銘柄別に扱えるよう拡張予定。

---

今後のリリースでは、ExecutionEngine / Monitoring の詳細なログやメトリクス強化、research モジュールの完成、テストカバレッジの拡充、運用用ドキュメントの追加を予定しています。