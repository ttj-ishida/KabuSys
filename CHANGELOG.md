CHANGELOG
=========

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

0.1.0 - 2026-04-21
-----------------

Added
- 初回リリース。KabuSys の基盤機能を追加。
- 起動スクリプト / ランタイム
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 停止はプロジェクト直下 data/stop_requested.flag によるフラグ検知で行う。
    - Monitoring は KABUSYS_ENV にかかわらず production 相当の sqlite_path を使用。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てて実行。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）に対応。
- 設定管理
  - config.Settings クラスを実装。環境変数から各種設定値（J-Quants トークン、kabu API、DB パス、監視閾値、実行環境判定等）を取得可能に。
  - .env 自動読み込み機能を追加（プロジェクトルートに基づき .env / .env.local を読み込む）。OS 環境変数は保護して上書きされない。
  - .env パーサは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
  - PAPER_FILL_MODE 等の列挙値チェック、KABUSYS_ENV / LOG_LEVEL 等のバリデーションを実装。
- 設定補助・検証ツール
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加。デフォルト値・選択肢・シークレットのマスク表示に対応。
  - validate_config: .env と config/*.yaml の事前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在通知、YAML ファイルの存在・パース検証（PyYAML がない場合は警告でスキップ）。
    - --strict オプションで警告を FAIL 扱い（exit(1)）。
- ログ・プロセス管理ユーティリティ
  - utils.logging_setup: ルートロガーを統一的に設定するユーティリティを追加。
    - stdout へ StreamHandler を出力（cron 等で stdout/stderr をまとめてリダイレクトする運用を考慮）。
    - 日次ローテーションの TimedRotatingFileHandler を追加（既定 logs/ ディレクトリ、30 日分保持）。ディレクトリ作成に失敗した場合はファイルハンドラをスキップして継続。
    - 引数 / 環境変数を優先したログレベル・ログディレクトリの解決。
  - utils.process_priority: プラットフォーム差（Windows / POSIX）を吸収してプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを追加。権限不足などで失敗した場合は警告を出してスキップ。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder: シグナルの候補選定（スコア降順）と等重・スコア重みの計算を実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とマーケット・レジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: 各銘柄の発注株数計算（risk_based / equal / score）を実装。
    - 単位株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金）超過時のスケールダウンロジック、cost_buffer を用いた保守的見積り、残差に基づく追加配分ロジックなどを含む。
  - portfolio パッケージは上記関数をエクスポートして公開 API を提供。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からレポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - 各種閾値を定義して PASS/FAIL 判定を出力。日付フィルタ（--from / --to）と --db オプションに対応。
    - P95 計算ユーティリティを実装。
- research
  - research.factor_research: DuckDB を使用したファクター計算モジュールの骨子を追加（モメンタム等の計算を想定する実装開始。prices_daily / raw_financials テーブル参照前提）。※ファイルは途中まで実装（継続作業向け）。

Changed
- (初回リリースのため該当なし)

Fixed
- (初回リリースのため該当なし)

Deprecated
- (初回リリースのため該当なし)

Removed
- (初回リリースのため該当なし)

Security
- (初回リリースのため該当なし)

Notes / 備考
- モジュールはまだ一部実装が進行中（例: research.factor_research が途中まで）。将来的に追加の検証およびユニットテストを推奨。
- .env は機密情報を含むため絶対に Git にコミットしないこと。config_setup が生成する .env ファイルにもその旨を明記。
- 実行時のファイルパスや挙動は環境変数で柔軟に変更可能（PAPER_TRADING_SQLITE_PATH、SQLITE_PATH、DUCKDB_PATH、LOG_DIR、MONITOR_POLL_INTERVAL 等）。

メタ
- パッケージバージョン: __version__ = "0.1.0"