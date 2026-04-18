CHANGELOG
=========

すべての注目すべき変更履歴を記録します。
フォーマットは "Keep a Changelog" に準拠しています。
https://keepachangelog.com/ja/1.0.0/

なお、このファイルはコードベースから推測して作成したもので、実際のコミット履歴とは異なる場合があります。

Unreleased
----------

- なし

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離する挙動を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様を明記。
- 設定・環境管理
  - config.py: 環境変数ラッパー Settings を追加。自動 .env 読み込み（.env / .env.local、プロジェクトルート検出）を実装。多くの設定プロパティ（DB パス、KABUSYS_ENV, PAPER_FILL_MODE 等）を提供し、値検証を行う。
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新）。鍵項目のマスク表示、既存値の再利用、.env 出力フォーマットを提供。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス・config/*.yaml の存在チェック、KABUSYS_ENV=live 時の追加警告など。--strict オプションで警告をエラー扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。stdout 出力用 StreamHandler と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）を統一的に設定。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows / POSIX を吸収したインターフェース（set_process_priority, set_cpu_affinity）。権限不足時は警告してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重（calc_score_weights）を追加。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio/position_sizing.py: 発注株数算出ロジック（risk_based / equal / score）、単元（lot）丸め、aggregate cap によるスケールダウンを実装。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を表示。PAPER_TRADING_SQLITE_PATH で DB を指定可能。
- データ分析（研究用）
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム、MA、ATR、流動性等の計算を意図）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。モジュールは設計部分・一部実装を含む（ファイル末尾は一部省略）。
- パッケージ情報
  - __init__.py: パッケージバージョンを設定 (__version__ = "0.1.0")。

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Implementation details
- .env 自動ロードはプロジェクトルート検出に依存（.git または pyproject.toml を探索）。プロジェクトルートが見つからない場合は自動ロードをスキップする。
- .env ローダーは export KEY=val 形式、クォート・エスケープ、行末コメントの扱いなどをサポートする。
- config の PAPER_FILL_MODE は許容値のみ受け付け、無効値は ValueError を送出する。
- run_monitoring は監視停止フラグ data/stop_requested.flag を検知するとループを抜ける。run_execution も同様に停止フラグを尊重して安全停止する設計。
- logging_setup はログディレクトリ作成に失敗した場合はファイル出力を諦め stdout のみで継続する。標準出力には stdout を使用し、stderr を避ける構成。
- position_sizing にて銘柄別の lot_size を将来的にサポートするための TODO がある（現状は共通 lot_size を使用）。
- risk_adjustment.apply_sector_cap は price が欠損（0.0）だとエクスポージャーが過少見積もられる点を将来的改善の TODO として記載。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップする（警告を出力）。

Known issues / TODO
- research/factor_research.py は完全実装が未完（ファイル末尾が途中で切れているなど）。追加の指標計算やテストが必要。
- 銘柄ごとの単元（lot）情報や価格フォールバックロジックなど、いくつかの拡張ポイントが TODO コメントとして残っている。
- 高権限が必要な操作（プロセス優先度設定、CPU affinity 設定）は権限不足で失敗する可能性があるが、現在はワーニングを出して安全にフォールバックする仕様。

Acknowledgments
- 初期設計は PortfolioConstruction.md、StrategyModel.md 等のドキュメント（コード内コメント参照）に基づいています。