CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

バージョン付けルールは SemVer に準拠しています。

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-23
-----------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの基本機能群を追加。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動と停止処理（stop flag / PID 管理）を実装。
- 監視用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関わらず本番用 sqlite_path を使用する旨を明示。
- 設定管理
  - config.py: 環境設定管理を追加。  
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み（.env, .env.local の読み込み順、OS 環境変数は保護）。
    - .env のパースロジックを実装（export 形式、シングル/ダブルクォート、エスケープ、行内コメントの扱いに対応）。
    - Settings クラスを提供し、各種設定プロパティと妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
  - config_setup.py: .env を対話式に生成・更新するウィザードを追加（既存値読み込み、シークレットマスク、保存機能）。
  - validate_config.py: 起動前に .env / config/*.yaml の設定不備を検出する CLI を追加（--strict オプションあり）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全体が 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックして警告を出力。
  - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）を実装。  
    - risk_based / equal / score の割当方式をサポート。単元（lot_size）丸め、1銘柄上限・全体利用上限・コストバッファを考慮したスケーリングロジックを実装。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。  
    - コンソール出力は stdout に出力、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をサポート、ログディレクトリ作成失敗時はファイル出力を無効化して継続。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収し、安全に処理。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。  
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定するコマンドラインツール。
- 研究（未完）
  - research/factor_research.py: ファクター計算モジュール（モメンタム／Value／Volatility／Liquidity）を追加。DuckDB を用いた prices_daily/raw_financials 参照による計算方針を実装（モジュールは一部実装に留まる）。
- パッケージ初期化
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- None（初回リリースのため差分履歴なし）。

Fixed
- 設定・起動時の堅牢性向上
  - .env パースでクォート／エスケープ／インラインコメントを正しく扱うように改善（config._parse_env_line）。
  - .env 自動読み込み時に OS 環境変数を保護する仕組みを導入（既存 OS 環境変数を上書きしない / .env.local は override=True だが protected で保護）。
  - run_monitoring.py の MONITOR_POLL_INTERVAL が不正な値のときに明確な警告を出してデフォルトへフォールバック。
  - logging_setup: ログディレクトリ作成に失敗してもアプリが落ちないようにし、ファイル出力を無効化してコンソールのみで継続。
  - init_monitoring_db 呼び出しは冪等で監視テーブルの存在を保証する（起動順に安全）。
  - process_priority の実行は権限不足や未対応 OS に対して例外を抑制して警告ログを出力。

Security
- 特になし。

Deprecated
- なし。

Removed
- なし。

Notes / 注意事項
- run_monitoring は説明にある通り「監視」用で、KABUSYS_ENV に関係なく monitoring 用の本番 sqlite_path を使用する実装になっています。環境分離の運用を期待する場合は設定の見直しを行ってください。
- PAPER_FILL_MODE の値検証が厳格化されており、無効な値は ValueError を送出します（有効値: instant|partial|never|reject）。
- position_sizing 等の数理ロジックは設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に基づいており、将来的な拡張（銘柄ごとの lot_size、価格フォールバックなど）を想定した TODO コメントが残されています。

参考
- コードベースの起動スクリプト:
  - python -m kabusys.run_execution もしくは実行ファイル相当で ExecutionEngine を起動
  - python -m kabusys.run_monitoring で SystemMonitor をポーリング実行
- 設定関連:
  - python -m kabusys.config_setup で .env を対話的に作成
  - python -m kabusys.validate_config で設定の検証
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

もし特定の変更点について詳細なリリースノートや、追加で記載してほしい項目（例えば API 仕様や CLI 出力例など）があれば指示してください。