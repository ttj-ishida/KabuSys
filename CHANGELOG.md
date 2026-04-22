# CHANGELOG

すべての注目すべき変更点をバージョン別に記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-04-22

### Added
- 初期リリースとして以下の主要コンポーネントを追加。
- 設定関連
  - kabusys.config: Settings クラスによる環境変数ベースの設定管理を実装。自動 .env ロード（.env → .env.local、OS 環境変数保護）と厳密な値検証（KABUSYS_ENV、LOG_LEVEL 等）をサポート。
  - .env ファイルパーサ: export プレフィックス、シングル/ダブルクォート（バックスラッシュエスケープ対応）、インラインコメントの扱い等に対応する堅牢なパーサを実装。
  - config_setup CLI (`kabusys.config_setup`): 対話式ウィザードで .env の初期作成・更新を支援するツールを追加。テンプレート出力と保存の仕組みを提供。
  - validate_config CLI (`kabusys.validate_config`): 起動前チェックツール。必須環境変数やファイルパス、YAML 構成ファイル（PyYAML があればパース検証）や本番向けのガード条件を検査し、INFO/WARNING/ERROR を出力。
- 実行・監視スクリプト
  - `run_execution.py`: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。BrokerFactory を介したブローカークライアント生成、OrderManager / RiskManager / Reconciler の組立て、デーモンスレッドでのセッション実行、stop flag / pid ファイルの扱いを実装。
  - `run_monitoring.py`: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）、停止フラグの検出、check_once() の例外捕捉ロジックを実装。監視は環境に関わらず本番 sqlite_path を使用する旨を明記。
- データベース統合
  - DuckDB/SQLite の接続を各実行スクリプトで利用する実装を追加（デフォルトパス: data/kabusys.duckdb / data/monitoring.db）。
  - 監視テーブルの初期化を担う init_monitoring_db 関数の呼び出しを組み込んで冪等性を確保。
- 運用ユーティリティ
  - utils.logging_setup.setup_logging: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）を実装。
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）と CPU affinity の固定（set_cpu_affinity）を実装。psutil を用い、権限不足等の例外は警告ログで安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）および市場レジームに応じた投下資金乗数計算（calc_regime_multiplier）を実装。unknown セクターの扱い、レジーム不明時のフォールバック等を明示。
  - portfolio.position_sizing: 発注株数算出ロジック（calc_position_sizes）を実装。allocation_method に応じた計算（risk_based / equal / score）、単元株（lot_size）丸め、ポジション上限・aggregate cap のスケール調整、cost_buffer を考慮した保守的見積りを提供。
  - portfolio パッケージの __all__ を整備し、主要関数をエクスポート。
- リサーチ / ツール
  - research.factor_research: DuckDB を使ったファクター計算モジュール（モメンタム等）を追加（設計・定数類、calc_momentum の導入）。DuckDB の prices_daily/raw_financials を前提にした設計。
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値（Uptime 99%、Fill 90% 等）に基づく PASS/FAIL を判定。--from/--to/--db オプションをサポート。
- パッケージ情報
  - kabusys.__init__.py にて __version__ = "0.1.0" を設定。

### Changed
- （初期リリースのため該当なし）

### Fixed
- ロギング周りでディレクトリ作成やファイルハンドラ生成が失敗した場合、アプリケーションが致命的に停止しないようにフォールバック処理を追加。
- run_monitoring のポーリングループで monitor.check_once() が例外を投げてもループを継続し、次ポーリングまで待機するように例外捕捉とログ出力を追加。
- .env 読み込み時に OS 環境変数を保護する「protected」機構を導入し、意図せぬ上書きを防止。

### Security
- .env ファイルへの機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）について、config_setup の生成時に明示的に「.env を Git にコミットしない」旨の注意書きを出力。

---

今後の予定（例）
- factor_research の各ファクター実装の完成（calc_momentum の続きなど）。
- ExecutionEngine / SystemMonitor のユニットテスト充実化と各種エラーケースの拡張テレメトリ。
- 単体テスト・CI とリリース手順の整備。

もしリリースノートの粒度（もっと詳細な変更点の分割、ファイル別の差分記載、既知の問題一覧の追加など）についてご希望があれば指示ください。