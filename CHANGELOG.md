CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

掲載日時: 2026-04-22

Unreleased
----------

（なし）

0.1.0 - 2026-04-22
-----------------

Added
- 初回リリース。KabuSys の基本機能を提供する多数のモジュールと CLI を追加。
- 起動スクリプト・プロセス
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。別スレッドでエンジンを実行し、data/stop_requested.flag による安全停止、PID ファイル出力、プロセス優先度設定をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視用 DB は環境に関係なく本番 sqlite_path を使用。
- 設定管理・CLI
  - config.py: Settings クラスを導入。環境変数の取得ラッパー、各種パス・閾値・モード（paper_trading/live/development）や paper_trading 用パス/モードの判定ロジックを提供。自動 .env ロード（.env / .env.local）機能を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（--env-file オプション対応）。入力項目にはシークレットマスクや選択肢をサポート。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。PyYAML が無い場合は YAML 検証をスキップして警告を出力。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。stdout 出力と日次ローテート（TimedRotatingFileHandler）を組み合わせ、ログディレクトリ作成に失敗した場合はファイル出力を自動で無効化。既存ハンドラの二重設定を防止。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を追加（psutil を利用）。Windows / POSIX の違いを吸収し、権限不足や未対応 OS は警告でスキップ。
- 取引・実行関連
  - execution/*: BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager などの組み立てロジックを導入。paper_trading 環境では MockBrokerClient と専用 DB（data/paper_trading.db）を使用し、本番 DB と分離。
  - Monitoring 初期化: 監視テーブルが存在することを保証する init_monitoring_db を起動前に実行（冪等）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights / calc_score_weights）を追加。スコアが全て 0 の場合のフォールバック動作を含む。
  - portfolio/risk_adjustment.py: セクター上限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。未知レジームや unknown セクターのフォールバック挙動を定義。
  - portfolio/position_sizing.py: 発注株数決定ロジックを追加。allocation_method（risk_based, equal, score）に対応し、単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮したスケーリング（aggregate cap）を実装。残余キャッシュを用いた端数再配分アルゴリズムを実装。
- 研究・ファクター計算
  - research/factor_research.py: DuckDB を用いた定量ファクター計算基盤（モメンタム / ボラティリティ / Value / Liquidity 計算の方針とユーティリティ）を追加（prices_daily / raw_financials を参照する設計）。（※ ファイルは一部実装途中の箇所あり。）
- ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH を参照し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）を集計して PASS/FAIL 判定を行う。各種閾値はコード内で定義（例: 稼働率 >= 99%、P95 <= 200 ms）。
- パッケージ情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を追加。

Changed
- ログ設計方針:
  - コンソール出力は stderr ではなく stdout を使用するように変更（Task Scheduler / cron でのリダイレクトを考慮）。
  - 既存ハンドラを明示的に flush/close してから削除することで、複数回 setup_logging を呼んでも冪等に動作するように改善。

Fixed
- 環境変数の取り扱いを堅牢化:
  - .env パーサーで export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱いなどを正しく処理するように実装。不正な行はスキップし、読み込み失敗時は警告を出す。
  - MONITOR_POLL_INTERVAL に不正な値（非整数・0 以下）が設定された場合にデフォルトにフォールバックして警告を出す処理を追加。
- process_priority や CPU affinity の失敗（権限不足、未実装 API）を例外で落とさずログ警告に変換するよう修正。

Security
- .env の取扱いに関する注意文言を対話ウィザードのヘッダに追加（.env を絶対に Git にコミットしないことを明示）。

Notes / Breaking changes
- paper trading と本番 DB を明確に分離:
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用。これにより paper_trading 実行時に本番の monitoring.db が上書き・汚染されないように設計されています。運用時は環境変数の設定を確認してください。
- 自動 .env ロードの副作用:
  - デフォルトでプロジェクトルートの .env / .env.local を自動読み込みします。テスト等で自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 一部実装途上:
  - research/factor_research.py の一部（ファイル末尾付近）は実装途中と思われます。ファクター計算を完全に利用する前に該当関数の完成度を確認してください。

今後の予定（想定）
- research/factor_research の完成・テストカバレッジ追加
- ExecutionEngine / RiskManager 周りのユニットテストおよびフェイルオーバーの強化
- ロギングの構造化出力（JSON 等）オプション追加
- 銘柄ごとの lot_size を考慮した拡張（stocks マスタの導入）

最後に
- 本 CHANGELOG はソースツリーの現状から推測して作成しています。実際のリリースノートとして使用する場合は、加えられた変更や既知の未完成点を開発チームで確認のうえ、追記・修正してください。