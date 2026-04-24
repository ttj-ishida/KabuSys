CHANGELOG
=========

すべての注目すべき変更は以下に記録します。形式は「Keep a Changelog」に準拠しています。

Unreleased
----------

（現在の配布バージョンは 0.1.0 です。今後の変更はここに追加してください。）

0.1.0 - 2026-04-24
------------------

Added
- 初期リリースを追加。パッケージメタ情報は kabusys.__version__ = "0.1.0"。
- 実行スクリプト:
  - run_execution: ExecutionEngine の起動エントリ。プロセス優先度を設定し、duckdb / sqlite に接続し、BrokerClientFactory を介してブローカークライアントを構築してエンジンを起動。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db を既定）を使用して本番 DB と分離。停止フラグ（data/stop_requested.flag）や実行 PID ファイル（data/execution.pid）を扱う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用。停止フラグ検知、例外ハンドリング、リソースクリーンアップを実装。
- 設定関連:
  - config.Settings: 環境変数ラッパー。データベースパス（DUCKDB_PATH, SQLITE_PATH）、paper_trading 用 sqlite パス、ログレベル、しきい値（CPU/MEM/DISK）等をプロパティで提供。KABUSYS_ENV のバリデーション（development/paper_trading/live）を含む。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml を探索）を基準に .env と .env.local をロード。OS 環境変数を保護する仕組み（override / protected）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサー: export 形式、クォート（シングル・ダブル）とバックスラッシュエスケープ、インラインコメント処理をサポート。
  - config_setup: 対話式ウィザードで .env を作成/更新する CLI。よく使う設定項目を一覧化し、シークレット項目はマスク表示して保存。
  - validate_config: 起動前検証 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）、KABUSYS_ENV=live 時の追加ガード。--strict オプションで警告を FAIL 扱いに可能。
- ロギング / プロセス管理ユーティリティ:
  - utils.logging_setup.setup_logging: ルートロガーを統一設定。stdout ストリームハンドラ（stdout を使用）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils.process_priority: Windows/Linux/Mac の差分を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。CPU affinity 設定関数も提供。権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築ライブラリ:
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア重み配分（全スコアが 0 の場合は等金額にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限。既存保有のセクター時価を算出し、max_sector_pct を超えているセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告と共に 1.0 でフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: 複数の配分方式に対応（"risk_based", "equal", "score"）。単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer を用いた保守的コスト見積り、残差分を lot 単位で再配分するロジックを実装。価格欠損時のスキップやログ出力あり。
  - portfolio パッケージから上記関数群をエクスポート。
- リサーチ / ファクター計算:
  - research.factor_research: DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して各種ファクター（Momentum, Value, Volatility, Liquidity）を計算する設計を導入。モジュールは関数ベースで純粋関数設計（DB は DuckDB 経由）。
- ツール:
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI。PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB を集計し、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出。デフォルト合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を用いた PASS/FAIL 判定を出力。P95 計算や日付フィルタ（--from/--to）をサポート。
- monitoring:
  - monitoring の DB 初期化（init_monitoring_db）呼び出しを run_monitoring/run_execution 両方で行い、監視テーブルが存在することを保証（冪等）。

Changed
- n/a（初回リリース）。

Fixed
- n/a（初回リリース）。

Notes / Implementation details
- 停止制御: run_monitoring と run_execution はプロジェクト内の data/stop_requested.flag（および設定で上書き可能なパス）を用いてグレースフルな停止を実現。
- エラーハンドリング: monitor.check_once 呼び出しや ExecutionEngine のスレッド実行中の例外を捕捉してログ出力し、サービスの継続を目指す設計。
- 環境変数取り扱いの細部: クォート内のバックスラッシュエスケープや、クォートなし値中のインラインコメント解釈（直前が空白の場合のみ）など、現実的な .env 内容に耐えるような実装。
- ロギング: ファイル出力が利用不可でもコンソールには必ずログを出力することで、クラウド/コンテナ/cron 環境での可視性を確保。
- Paper Trading 分離: 本番監視 DB とペーパートレード DB を明確に分離し、誤操作によるデータ混在を防止する方針。

開発者向けメモ
- 今後の改善余地:
  - price の取得が欠損した場合のフォールバック（前日終値や取得原価）処理。
  - 銘柄ごとの lot_size を stocks マスタで管理する拡張。
  - factor_research の完全実装（コメント末尾で途中切れが見られるため続きを実装する必要あり）。
  - validate_config の YAML 検証を PyYAML がない場合でも別手段で強化するか、依存関係として PyYAML を明示する。
  - テストカバレッジ（ユニットテスト・統合テスト）の整備。

ライセンス / セキュリティ
- 本ドキュメントはコード内容から推測してまとめた変更履歴です。機密情報（トークン・パスワード等）は .env に保存し、.env をリポジトリにコミットしない旨が config_setup の注釈に明記されています。

-----------------------------------------------------------------------------