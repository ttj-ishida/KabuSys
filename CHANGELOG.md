CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
セマンティックバージョニングに従っています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-20
--------------------

Added
- 初期リリースを追加（パッケージバージョン: 0.1.0）。 (src/kabusys/__init__.py)
- 実行用スクリプトを追加:
  - 実行エンジン起動スクリプト (run_execution.py)。プロセス優先度を高く設定し、バックグラウンドスレッドで ExecutionEngine を起動 / 停止管理を行う。停止フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) を使用。Paper Trading 環境時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB から分離する。 (src/kabusys/run_execution.py)
  - 監視ループ起動スクリプト (run_monitoring.py)。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。停止フラグ検知でループ終了。 (src/kabusys/run_monitoring.py)
- 環境設定関連:
  - Settings クラスを導入し、環境変数から設定値を取得する API を提供。必須値チェックや値の正規化を行うプロパティ群を実装。PAPER_FILL_MODE の検証、paper_sqlite_path、各種閾値設定などを含む。 (src/kabusys/config.py)
  - .env の自動読み込み機構を追加（プロジェクトルートの .env / .env.local を読み込む）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。export 付き行・クォート・インラインコメント等に対応したパーサーを実装。 (src/kabusys/config.py)
  - 対話式 .env ウィザードを追加 (config_setup.py)。主要な環境項目の補助入力・既存値の読み込み・.env への書き出しを実装。 (src/kabusys/config_setup.py)
  - 設定検証 CLI を追加 (validate_config.py)。必須環境変数の存在確認、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パースチェック（PyYAML 未インストール時はスキップ）を行う。--strict オプションで警告を FAIL 扱いにできる。 (src/kabusys/validate_config.py)
- ロギングとプロセス制御ユーティリティ:
  - 統一的なログ設定ユーティリティを追加 (utils/logging_setup.py)。コンソール（stdout）への StreamHandler と日次ローテーションする TimedRotatingFileHandler（保持 30 日）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてフォールバックする。LOG_DIR / LOG_LEVEL の解決順を実装。 (src/kabusys/utils/logging_setup.py)
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加 (utils/process_priority.py)。Windows と POSIX（Linux/macOS 等）を吸収し、安全にフォールバックする実装。権限不足や未対応 OS 時は警告を出してスキップ。 (src/kabusys/utils/process_priority.py)
- ポートフォリオ構築ライブラリ:
  - 銘柄選定・重み計算機能を実装（select_candidates, calc_equal_weights, calc_score_weights）。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。 (src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中上限チェックとレジーム乗数（apply_sector_cap, calc_regime_multiplier）を実装。セクター不明銘柄は上限適用外になる挙動を明記。レジームマップは bull/neutral/bear をサポートし、未知のレジームはフォールバック。 (src/kabusys/portfolio/risk_adjustment.py)
  - 株数決定ロジックを実装（calc_position_sizes）。risk_based/equal/score の割当方式、単元株（lot_size）丸め、1銘柄上限・アグリゲート上限、コストバッファ考慮、利用可能現金に対するスケーリング（端数処理ロジック含む）を備える。 (src/kabusys/portfolio/position_sizing.py)
  - portfolio パッケージから主要関数をエクスポートする __init__ を整備。 (src/kabusys/portfolio/__init__.py)
- 研究・分析:
  - ファクター計算モジュールの骨格を追加（research/factor_research.py）。DuckDB を用いて prices_daily / raw_financials を参照してモメンタム・ボラティリティ等を計算する設計。モジュール注釈に計算方針と定数を明記。 (src/kabusys/research/factor_research.py)
- ツール:
  - Paper Trading 検証レポートジェネレータを追加 (tools/paper_verification_report.py)。PAPER_TRADING_SQLITE_PATH（または --db）で指定したペーパートレード DB から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計し、閾値に基づく PASS/FAIL を出力する。P95 計算と日付フィルタリングを実装。 (src/kabusys/tools/paper_verification_report.py)

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Implementation details
- デフォルトの DB / ログパス等:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/ 、ログ保持 30 日
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で変更可能。無効な値や 0/負値の場合は 60 秒にフォールバックして警告出力。
- run_execution は起動時に停止フラグを検知すると起動自体を行わない安全な動作を実装。
- utils は権限不足やライブラリ未インストール時に例外を投げず、警告を出してスキップする設計にして可用性を高めている。