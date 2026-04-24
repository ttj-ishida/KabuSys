CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

[0.1.0] - 2026-04-24
--------------------

Added
- 初回リリース（基本機能を実装）。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。  
    - BrokerClientFactory を介して実行環境に応じたブローカークライアントを生成。  
    - PID ファイル / 停止フラグ(stop_requested.flag) を用いたプロセス制御を実装。  
    - RiskManager のデフォルト設定（max_position_pct 等）を組み込み。  
- 監視用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒、無効値は警告の上デフォルトにフォールバック）。  
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して初期化（監視 DB の冪等初期化を実行）。  
    - 停止フラグ検知でループを安全終了。KeyboardInterrupt に対応。  
- 環境設定
  - config_setup.py: 対話式 .env ウィザードを追加。シークレット項目はマスク表示し、.env の生成/更新を支援。  
  - config.py: Settings クラスと自動 .env ロード機構を実装。  
    - プロジェクトルート検出（.git または pyproject.toml を基準）により、CWD に依存しない .env 自動読み込みを行う。  
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。  
    - .env パーサは`export KEY=...`、クォート/エスケープ、インラインコメント（クォートなしのときに直前が空白ならコメントと扱う）等に対応。  
    - 各種設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH, PID ファイルパス、監視しきい値等）のプロパティを提供し、値の検証を行う。  
- 設定検証
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数の存在、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスの親ディレクトリの存在確認、config/*.yaml の存在・パース検査（PyYAML がない場合はスキップ）を実行。--strict オプションで警告も FAIL 扱いにできる。  
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。  
    - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。  
    - LOG_LEVEL / LOG_DIR の解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップするフォールバックを持つ。  
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU アフィニティ設定を追加（psutil を利用）。Windows/Linux(Mac 等) の差分を吸収。アクセス権限不足時は警告を出してスキップ。  
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 銘柄選定 select_candidates と重み計算（等重 calc_equal_weights、スコア加重 calc_score_weights）を実装。スコアが全て 0 の場合は等重にフォールバック。  
  - portfolio/risk_adjustment.py: セクターキャップ適用 apply_sector_cap（既存保有比率に基づく候補除外）と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバックして 1.0 を返す。  
  - portfolio/position_sizing.py: 発注株数計算 calc_position_sizes を実装。  
    - allocation_method="risk_based" と "equal"/"score" をサポート。  
    - 単元株（lot_size）丸め、1 銘柄上限 (max_position_pct)、aggregate cap（available_cash）超過時のスケーリング、コストバッファ反映、残余の端数割当ロジックを実装。  
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。  
    - システム稼働率（system_status）、注文成功率/送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（P95 等）を集計し PASS/FAIL 判定を出力。日付範囲指定・DB パス指定をサポート。既定しきい値はソース内で定義（稼働率 99% 等）。  
- リサーチ
  - research/factor_research.py: DuckDB を用いたファクター計算基盤（モメンタム等）を追加。prices_daily / raw_financials を参照してファクター（Momentum/Value/Volatility/Liquidity）を計算する設計。現状モメンタム等の関数が実装を開始（未完成箇所あり）。

Changed
- ロギングのデフォルトを stdout に統一し、cron/Task Scheduler でのリダイレクト運用に配慮（stderr ではなく stdout を使用）。
- .env 読み込みの優先順位を OS 環境変数 > .env.local > .env に定義。既存 OS 環境変数を保護するための protected オーバーライドロジックを導入。

Fixed
- .env パーサの堅牢化: export 形式、クォートとエスケープシーケンス、インラインコメントの取り扱いを改善。これにより複雑な秘密値や URL などを含む環境変数の読み込み信頼性が向上。
- MONITOR_POLL_INTERVAL の不正な値に対しては警告を出しデフォルトにフォールバックするように修正（time.sleep に不正値を渡さない）。

Notes
- 監視処理（run_monitoring）は監視用テーブルの初期化（init_monitoring_db）を行う。init_monitoring_db は冪等である想定。  
- ExecutionEngine は停止フラグ検知による安全終了をサポート。起動直後に停止フラグが立っている場合は起動を中止する。  
- process_priority / set_cpu_affinity は権限や OS の差分により失敗する場合があるが、その場合は警告を出して処理を継続する。  
- config_setup によって生成される .env ファイルは機密情報を含むため、絶対に Git 等にコミットしないでください（ファイルヘッダで注意喚起あり）。  
- research/factor_research の一部実装は継続開発中。ファクター計算は DuckDB のテーブル構造（prices_daily, raw_financials）に依存します。

開発・運用上の推奨
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定することを推奨（自動クリアは危険）。validate_config にて注意喚起を行う。  
- ログや DB のパス（LOG_DIR, DUCKDB_PATH, SQLITE_PATH）は起動前に適切に設定し、バッチ等での実行ユーザーにディレクトリ作成権限があることを確認してください。

----- 

今後の予定（未実装/改善案）
- research/factor_research の完全実装とユニットテスト追加。  
- Engine / Monitor のユニットテスト整備と CI 導入。  
- 各種設定・しきい値を YAML 等で管理するための外部設定読み込み機能の拡充。