CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__（0.1.0）に合わせています。

Unreleased
----------

(なし)

0.1.0 - 2026-04-21
------------------

Added
- 初回リリース: KabuSys の基本モジュール群を追加。
  - 環境設定と起動支援
    - config.py: 環境変数の読み込み・管理を実装。プロジェクトルート（.git または pyproject.toml）を自動検出して .env / .env.local を読み込む自動ロード機能を提供。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - config_setup.py: .env を対話式に作成/更新するウィザードを追加。シークレット項目は表示時にマスク。生成ファイルのテンプレートを出力。
    - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検証する CLI を実装。--strict オプションで警告を FAIL 扱いにできる。PyYAML 未インストール時は YAML 検証をスキップして警告出力。
  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、スレッドでのエンジン実行と停止フラグ（data/stop_requested.flag）による制御を実装。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。Monitoring は環境に関わらず本番 sqlite_path を使用する仕様を明示。
  - ユーティリティ
    - utils/logging_setup.py: 統一されたロギング設定ユーティリティを実装。StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。ログディレクトリ自動作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU アフィニティ設定関数を実装。権限不足や未サポート環境では警告を出してスキップ。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等金額配分へフォールバック（警告ログ）。
    - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を実装。unknown セクターはセクター上限の対象外。未知のレジームは警告を出して 1.0 でフォールバック。
    - portfolio/position_sizing.py: 各銘柄の発注株数計算を実装。allocation_method に応じた計算（risk_based / equal / score）をサポート。単元株（lot_size）丸め、1 銘柄上限、投下資金合計の aggregate cap を実装。資金不足時はスケールダウンと残差分の優先配分を行う。手数料/スリッページ想定の cost_buffer を考慮。
  - 研究モジュール（部分実装）
    - research/factor_research.py: Momentum / Value / Volatility / Liquidity などのファクターを DuckDB の prices_daily / raw_financials を使って計算する設計。モメンタム等の定数や P95 等の計算ユーティリティが含まれる。（一部実装がファイル末尾で途切れている）
  - ツール
    - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を参照（デフォルト data/paper_trading.db）。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し、基準値と比較して PASS/FAIL を判定。閾値（稼働率 99%、成功率 90% 等）はスクリプト内の定数で管理。
  - パッケージ初期化
    - __init__.py: パッケージ名と __version__（0.1.0）を追加。公開モジュール一覧に data/strategy/execution/monitoring を含める。

Changed
- (初回リリースにつき該当なし)

Fixed
- (初回リリースにつき該当なし)

Security
- (該当なし)

Deprecated
- (該当なし)

Removed
- (該当なし)

Notes / 既知の制限と TODO
- config.py/.env パーサは引用符付き値や export プレフィックス、インラインコメントに対応しているが、極端に複雑なエスケープや改行を含むケースは未検証。
- apply_sector_cap のエクスポージャー計算は price が欠損（0.0）だと過少見積もりになる旨の TODO コメントあり。将来的に前日終値や取得原価で補完する可能性が示唆されている。
- process_priority や set_cpu_affinity は権限不足や非対応 OS で動作しない場合がある（警告ログでスキップ）。
- research/factor_research.py は設計に沿った関数群を含むが、ファイル末尾で実装が途切れている（モメンタム計算関数の続きが未収録）。実運用前に完全実装とテストが必要。
- run_monitoring は Monitoring が常に本番 sqlite_path を使用する設計（意図的）。監視データの分離が必要な場合は設計見直しが必要。
- run_execution は paper_trading 環境で paper_trading DB に記録することで本番データと分離する仕組みを持つ。BrokerClientFactory と MockBrokerClient の実装詳細に依存する。

開発者向けメモ
- ログ設定は setup_logging でアプリ名を渡して使う（例: setup_logging(app_name="execution")）。既存ハンドラの二重登録を防ぐために、設定時に既存ハンドラを flush/close して削除する。
- 環境変数のロード順は OS 環境変数 > .env.local > .env。OS の既存環境変数は保護され自動上書きされない。
- validate_config の --strict モードは CI 前段のチェックに便利（警告もエラー扱いにすることで安全性を高める）。

お問い合わせ
- 不明点や追加の変更履歴要望があればお知らせください。ソースコードの意図に基づき追記・修正します。