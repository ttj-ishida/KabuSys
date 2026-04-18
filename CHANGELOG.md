CHANGELOG
=========

すべての注目すべき変更点を記録します。形式は「Keep a Changelog」に準拠しています。

注: この CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴ではなく、コード内の機能・コメント・挙動に基づく要約です。

Unreleased
----------

- —（現在未リリースの変更はありません）—

[0.1.0] - 2026-04-18
--------------------

Added
- 実行および監視プロセスの起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを提供。KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db 等）を使用し、MockBrokerClient を利用する想定。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 環境設定関連ユーティリティ
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を実装。主要な環境項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス等）をサポート。
  - validate_config.py: .env と config/*.yaml の事前検証ツールを実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML が利用可能な場合）、本番向けの追加警告などを行う。--strict オプションで警告を FAIL 扱いにできる。

- 設定読み込み・管理
  - config.py: .env 自動ロード機能（プロジェクトルート検出）を実装。OS 環境変数を保護しつつ .env / .env.local を読み込む。Settings クラスを通して各種設定値（パス、しきい値、フラグ、API のトークンなど）を型付で取得できる。PAPER_FILL_MODE のバリデーション、KABUSYS_ENV の妥当性チェック等を含む。

- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーを一括設定するユーティリティ。コンソール (stdout) 出力と日次ローテーションのファイル出力（TimedRotatingFileHandler）をセットアップ。ログディレクトリ作成失敗時はファイルハンドラを落としてコンソールのみで継続するフォールバックを実装。
  - utils/process_priority.py: Windows/Linux（主要 POSIX）でプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを実装。権限不足や未対応 OS の場合は警告を出してスキップする。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0 の場合は等金額にフォールバックする。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、および市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。regime の既知値に対するマッピングと未知レジームのフォールバックを含む。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウンと端数処理）などをサポート。手数料・スリッページを考慮する cost_buffer パラメータ、将来的な拡張点（銘柄別 lot_size）についてコメントあり。

- 研究用ファクター計算（雛形）
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum/Value/Volatility/Liquidity 等のファクターを計算するための設計と一部実装（定数、関数骨格）を追加。prices_daily / raw_financials テーブル依存として設計。

- ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成するスクリプトを実装。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し、閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を出力する。

- パッケージ基本情報
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

Changed
- ログ出力は標準エラーではなく標準出力（stdout）へ出す設計に統一（logging_setup）。cron 等でリダイレクト扱いやすくするため。

Fixed
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合のフォールバックを追加（ログ出力が停止しないように StreamHandler のみで継続）。

Security
- シークレット値（J-Quants トークン、kabu API パスワード、LINE トークン）は config_setup と .env 書き込み内でマスク扱いおよびユーザーの明示的入力を推奨する旨の扱い。Settings._require により必須項目の未設定時は起動前に明示的なエラーにより検出される。

Known issues / Notes
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる懸念があり、将来的に前日終値や取得原価でのフォールバックが必要とコメントあり。
- position_sizing:
  - 将来的に銘柄別の lot_size をサポートする拡張予定（現在は全銘柄共通の lot_size を想定）。
- run_execution / run_monitoring:
  - 停止制御はプロジェクト直下の data/stop_requested.flag を監視する手法を採用しているため、デプロイ時の運用手順の整備が必要。
- research/factor_research.py は途中で切れている（本来の実装が続く想定）。完全なファクター計算の実装・テストが必要。

その他
- validate_config の --strict モードにより「警告を FAIL 扱い」にできるため、本番導入前のチェックで強制的に警告を解消する運用が可能。
- run_execution は paper_trading 環境で DB を完全に切り離す設計（paper_sqlite_path）で、ペーパートレードと本番データの混在を防止。

以上

（この CHANGELOG はコードのコメント・実装内容から推測して作成しています。実際の変更履歴を正確に反映するにはコミットログを参照してください。）