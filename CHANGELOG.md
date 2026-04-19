CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース（バージョン 0.1.0）。
- 実行用スクリプト／デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止要求はプロジェクト内 data/stop_requested.flag ファイルの存在で検知。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を high に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）で実行中エンジンを安全に停止可能。
    - 実行中の PID を data/execution.pid に保存する想定（pid_file 引数に渡す）。
    - 起動時にプロセス優先度を high に設定。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env のパースロジックを実装（export 形式、クォート、コメント対応）。
    - Settings クラスを提供し、各種環境変数（J-Quants / kabuAPI / DBパス / Paper Trading 関連 / 監視しきい値 等）をプロパティ経由で取得可能。
    - KABUSYS_ENV, LOG_LEVEL などの値検証を実装。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START 等の設定をサポート。
- 設定支援 CLI
  - config_setup.py
    - .env を対話式に作成・更新するウィザードを追加。既存 .env の読み込みと保存機能を持つ。
    - .env 保存テンプレートを実装（秘密値はマスク表示）。
    - コマンドライン引数で保存先ファイルを変更可能（--env-file）。
  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、YAML パース検査（PyYAML が利用可能な場合）、本番環境時の追加ガード等を実装。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング & 実行環境ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定する共通ユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで動作。
    - ログレベル / ログパスの解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）をプラットフォーム差分を吸収して設定するユーティリティを追加。Windows / POSIX(nice) を考慮。
    - CPU affinity を最初の N コアに固定する関数を追加（設定失敗時は警告を出してスキップ）。
- ポートフォリオ構築モジュール（純関数）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - calc_score_weights は全銘柄スコアが 0 の場合に等金額配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。sell_codes（当日売却予定）を除外して既存エクスポージャーを算出。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジックを実装。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - Risk ベースの算出（risk_pct, stop_loss_pct）および per-position / aggregate の上限処理、単元株（lot_size）丸め、コストバッファを考慮した縮小ロジックを実装。
    - 投資合計が available_cash を超える場合のスケーリングと端数処理（lot 単位での再配分）を実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を抽出してレポートを出力する CLI を追加。
    - 判定閾値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）をデフォルトで定義。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）をサポート。
- Research 用モジュール（骨格）
  - research/factor_research.py
    - モメンタム / Value / Volatility / Liquidity の計算指針と初期実装（関数シグネチャ、定数）を追加（prices_daily / raw_financials を DuckDB 経由で参照する設計）。※ 実装の一部が未完（ファイル末尾が途中で終端）。
- パッケージ情報
  - __init__.py にてパッケージバージョンを 0.1.0 として定義。

Changed
- 新規リリースのため初回追加。既存変更無し。

Fixed
- なし

Security
- なし

注記（マイグレーション / 運用上の注意）
- .env 自動読み込みはデフォルトで有効。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring は KABUSYS_ENV の値に関係なく sqlite_path を使用します。本番運用・検証データを分離したい場合は設定を調整してください（paper_trading 用は PAPER_TRADING_SQLITE_PATH を利用）。
- run_execution の paper_trading モードでは DB を別ファイルに分け、本番データと明確に隔離する設計になっています。
- run_monitoring/run_execution は起動時にプロセス優先度を high に設定しようとしますが、権限不足やプラットフォーム非対応時は警告を出してスキップします。
- ログディレクトリ作成に失敗するとファイルローテーションは無効化され、標準出力のみとなるため、ログの保存先は事前に作成しておくことを推奨します。
- research/factor_research.py は一部未完の箇所があります。DuckDB テーブル構造（prices_daily, raw_financials）に依存するため、実運用前にデータ準備を確認してください。

参考（主なコマンド）
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]