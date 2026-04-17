CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-04-17
-------------------

初回公開リリース。

Added
- 基本 CLI / 実行スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。プロセス優先度設定、DB 接続、Broker クライアント作成、ExecutionEngine の起動／停止制御（停止フラグ監視）を実装。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検出、monitoring DB の初期化を実行。
  - validate_config.py: .env および config/*.yaml の事前検証 CLI。必須環境変数チェック、パスの存在チェック、YAML のパース検証（PyYAML が存在する場合）などを提供。--strict モードをサポート。
  - config_setup.py: 対話式 .env 作成ウィザード。既存値の読み込み／再利用、シークレットマスク表示、最終確認後に .env を生成。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出して PASS/FAIL 判定を行う。

- 設定管理
  - config.py: Settings クラスを追加。環境変数の読み取り、デフォルト値、バリデーション（KABUSYS_ENV/PAPER_FILL_MODE/LOG_LEVEL など）、パス解決（expanduser）を提供。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動で読み込む機構を追加。OS 環境変数は保護（上書き防止）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルのスコアソート（select_candidates）、等重み・スコア重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio/position_sizing.py: ポジションサイズ計算（calc_position_sizes）。risk_based / equal / score の割当方式、lot_size による丸め、aggregate cap によるスケーリング、cost_buffer（手数料/スリッページ見積り）を考慮。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装（regime に応じた資金乗数）。
  - portfolio パッケージ統合（__init__.py）で API をエクスポート。

- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（Momentum / Volatility / Liquidity / Value 等の計算の骨組み）。MA200、mom_1m/3m/6m、ATR 等の計算を実装（DuckDB SQL を利用）。

- ユーティリティ
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity を跨プラットフォームで設定するユーティリティ。psutil を用い、Windows と POSIX 系を吸収。失敗時は警告でフォールバック。
  - stop/kill フラグ／PID ファイルの取り扱いを実行スクリプトに組み込み（data/stop_requested.flag, data/execution.pid, 設定経由のパス）。

- DB 初期化・接続
  - run_* スクリプトで sqlite3 / duckdb への接続を行い、監視テーブルの初期化（init_monitoring_db）を保証。
  - Paper Trading モード時は本番 DB と分離して PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用。

Changed
- プロジェクトメタ
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

Fixed / Improvements
- .env パーサの堅牢化（config.py）
  - export KEY=val 形式対応、クォートされた値のバックスラッシュエスケープ処理、インラインコメントの取り扱い（クォート有無に応じて正しく無視）。
  - ファイル読み込み失敗時に警告発行して処理継続。
- config_setup ウィザード
  - シークレット値マスク表示、選択肢チェック、Enter 押下時の既存値／デフォルトの再利用など、対話性の改善。
  - 書き込み時に .env テンプレートを整形して保存（.env は Git にコミットしない旨のヘッダ）。
- Paper Trading 検証レポート
  - P95 計算を実装し、テーブル欠如や OperationalError に対して堅牢に N/A を返すフォールバックを追加。
  - 各指標（稼働率、fill/send rate, P95）に閾値を導入し PASS/FAIL 判定を出力。
- position_sizing のスケーリング処理
  - 全体投資額が利用可能現金を超える場合のスケールダウンロジックと端数処理（lot 単位の再配分）を実装。
- run_monitoring の挙動
  - MONITOR_POLL_INTERVAL 環境変数が不正（数値変換エラーや 0 以下）でもデフォルト（60 秒）にフォールバックして警告を出す安全化。

Security
- config_setup で生成される .env に関する注意喚起を明記（.env を Git にコミットしないこと）。
- 対話式 UI ではシークレット項目をマスク表示。

Notes / Behavior
- run_monitoring は docstring の通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」。実行者は意図した DB を使っているか確認すること。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と完全分離する設計。
- set_process_priority は権限不足や未対応プラットフォームで失敗する可能性があり、その場合は警告を出して処理を継続する。

Breaking Changes
- なし（初回リリース）。

Acknowledgements / TODOs
- research/factor_research の SQL は DuckDB 上で動作する前提。production データの schema（prices_daily, raw_financials）に依存するため、投入データの整合性が必要。
- position_sizing の lot_size は現状全銘柄共通。将来的には銘柄別 lot_map に拡張予定（コード内 TODO）。
- apply_sector_cap の価格欠損時のフォールバック（前日終値等）の扱いは現状未実装（コメントあり）。

---- 

配布／導入時は、config_setup.py による .env 作成 → validate_config.py による検証 を推奨します。