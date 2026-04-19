CHANGELOG
=========

すべてのリリースは Keep a Changelog の形式に準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- 初期リリースを追加。パッケージバージョンは __version__ = "0.1.0"。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag によるフラグ検出で行う。Monitoring は環境にかかわらず本番 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。停止フラグと PID ファイル管理、スレッドでのエンジン実行と安全停止処理を実装。
- 設定管理
  - config.py: 環境変数/.env 読み込みと Settings クラスを追加。自動 .env ロード（.env -> .env.local）を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。多くの設定プロパティ（DB パス、PID/kill フラグパス、閾値、paper_trading の挙動など）を提供し、値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を行う。
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。シークレットマスク表示、デフォルト値、.env の書き出しテンプレートを実装。
  - validate_config.py: 起動前診断 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML 未インストール時にはスキップして警告）などを実行。--strict モードで警告を FAIL として扱える。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定・等分配・スコア加重配分（score が全て 0 の場合のフォールバックを含む）を実装。
  - portfolio/position_sizing.py: position sizing（risk_based / equal / score）を実装。単元株 (lot_size) に丸め、per-position 上限、aggregate cap（available_cash）に基づくスケールダウンと端数処理（残余キャッシュで追加配分）を実装。cost_buffer による保守的見積もりをサポート。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（unknown レジームはフォールバック）。
  - portfolio/__init__.py: 上記関数をパッケージとしてエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一的ログ設定ユーティリティを追加。stdout 用 StreamHandler と 日次ローテート（TimedRotatingFileHandler、30 日保持）のファイルハンドラをルートロガーに設定。LOG_DIR/LOG_LEVEL/引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows/Linux/macOS 対応、psutil 使用）。CPU affinity 設定関数も追加。アクセス権限や未対応環境では安全にスキップして警告を出力。
- 実行系コンポーネント（スケルトン / 組立）
  - run_execution から利用する BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）などの組み立てと起動フローを実装（コードベース内の利用想定に従った依存注入）。
  - RiskConfig のデフォルトパラメータ例を追加（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - ExecutionEngine は pid_file と停止フラグを考慮して安全に起動/停止する。
- Paper Trading サポート
  - 設定で KABUSYS_ENV=paper_trading をサポート。paper_trading 時は MockBrokerClient を利用する想定（BrokerFactory 経由）。paper_fill_mode（instant/partial/never/reject）および PAPER_TRADING_SQLITE_PATH をサポート。
  - paper_trading 用の検証ツール tools/paper_verification_report.py を追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計して PASS/FAIL を判定する。P95 計算や期間フィルタ、テーブルの存在に応じたフォールバック処理を実装。閾値はソース内に定義（稼働率 99%、成立率 90% など）。
- research
  - research/factor_research.py: DuckDB の prices_daily/raw_financials を前提としたファクター計算モジュール（Momentum/Value/Volatility/Liquidity）の骨組みを追加（関数 calc_momentum 等を開始）。
- その他
  - package の __init__.py に __all__ 指定とバージョンを追加。
  - tools パッケージと初期化ファイルを追加。

Changed
- n/a（初回リリースのため変更履歴無し）

Fixed
- n/a（初回リリースのため修正履歴無し）

Notes / Implementation details
- .env の自動読み込み順序は OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local の override でも上書きされない。
- .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート有無での扱い差）に対応。
- config.validate: PyYAML がない場合は YAML の検証をスキップして警告するため、PyYAML を導入すれば config/*.yaml の構文チェックが有効になる。
- ログ設定: ファイルハンドラ作成に失敗した場合は StreamHandler（stdout）のみで継続。stdout を用いる理由は cron / Task Scheduler でのリダイレクト考慮のため。
- run_monitoring と run_execution は共にプロセス優先度を起動直後に "high" に設定しようとする（失敗時には警告を出して継続）。
- run_monitoring は MONITOR_POLL_INTERVAL が不正な値（0 や負、非整数）の場合にデフォルト 60 秒へフォールバックし、警告を出す。
- position_sizing の aggregate cap スケーリングは lot_size 単位で丸め、残余キャッシュを用いた端数配分ロジックを実装して再現性を保つ。
- risk_adjustment.apply_sector_cap は sector_map に存在しないコードを "unknown" 扱いとし、unknown セクターは上限適用対象外。

Breaking Changes
- なし（初回リリース）

今後の改善案（参考）
- portfolio.position_sizing: 銘柄毎の lot_size をサポートするため stocks マスタからの取込対応。
- risk_adjustment: price 欠損時のフォールバック価格（前日終値や取得原価）を導入して過小見積りを回避。
- validate_config: config/*.yaml のより詳細なセマンティック検証（必須キー、有効値範囲など）。
- research/factor_research: calc_momentum の未完部分と他ファクター実装の完成、およびユニットテスト追加。

--- 
この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・ issue / PR の情報に基づき追記・修正を行ってください。