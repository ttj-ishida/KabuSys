CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/).
The format is Japanese.

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 初期リリースを追加。
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する設計。
    - 起動時にプロセス優先度を "high" に設定するフローを導入。
    - 停止フラグ (data/stop_requested.flag) と PID ファイルの扱いを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
    - stop flag による安全停止、例外発生時のログ化を実装。
- 設定管理
  - config.py: 環境変数/.env 読み込みロジックを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env, .env.local の優先順）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env の行パーサーを実装（export フォーマット、クォート内のエスケープ、インラインコメント処理などに対応）。
    - Settings クラスで主要設定をプロパティとして提供（DB パス、各種閾値、env 判定、paper_trading 用設定等）。
    - PAPER_FILL_MODE の妥当性チェック、PAPER_TRADING_SQLITE_PATH 等のプロパティを追加。
- 設定支援／検証ツール
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 標準項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 関連、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話形式で生成・上書き可能。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの存在／親ディレクトリチェック、config/*.yaml の存在/パース検証を行う。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング/プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション (TimedRotatingFileHandler) を root ロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name による解決順、ファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - Windows/Linux/macOS 等での安全なフォールバックとエラーハンドリングを実装。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定と重み計算関数を追加。
    - select_candidates（スコア降順、同点時の tie-breaker）、calc_equal_weights、calc_score_weights（スコア合計 0 の場合に等分でフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム乗数のロジックを追加。
    - apply_sector_cap（既存保有のセクター比率が上限を超えている場合に候補を除外）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に応じた投資乗数、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py: 株数決定ロジックを追加。
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出。
    - lot_size 単位で丸め、per-position と aggregate のキャップ（max_position_pct, max_utilization、cost_buffer を用いた保守的見積）を実装。
    - aggregate cap 超過時のスケールダウンと端数配分アルゴリズムを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）を集計。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプション対応、PAPER_TRADING_SQLITE_PATH 環境変数対応。
- 研究用ファクターモジュール（研究用）
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム、MA200 乖離、ATR、Volume 系ファクター等を想定）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照する設計。モジュールは複数の定数と calc_momentum などの関数スタブを含む（実装はモジュール内の設計に従う）。

Changed
- パッケージ定義
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Fixed
- 既知のフォールバック／安全側の挙動を実装（ファイル作成失敗時のログ出力フォールバック、psutil による優先度設定失敗時の警告等）。
- .env 読み込みでファイル読み込み失敗時に警告を出すよう改善。

Notes / Implementation details
- 環境変数ロード順序:
  - OS 環境変数 > .env.local > .env（ただし OS 環境変数は protected として上書き不可）。
- MONITOR_POLL_INTERVAL の不正な値（整数変換失敗や 0 以下）はデフォルト 60 秒へフォールバックし、警告を出力。
- run_execution.py と run_monitoring.py は起動時に set_process_priority("high") を呼び出すため、実行環境での権限や psutil の動作に依存する。設定に失敗した場合は警告ログが残るが実行継続する設計。
- Paper Trading と Live の DB は分離（paper_trading 時は paper_sqlite_path を使用）。監視用 monitoring DB は run_monitoring が常に本番 sqlite_path を使用する点に注意。

未解決 / TODO
- research/factor_research の一部実装（calc_momentum 等）はファイル末尾で未完了の箇所が見受けられます。必要に応じてテスト・完成化を推奨。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価を使う等）は TODO コメントとして残されているため、より堅牢な価格フェイルオーバー実装を検討してください。

License
-------
- （パッケージのライセンス情報がソース内に明記されていないため、適切なライセンスを別途追加してください。）