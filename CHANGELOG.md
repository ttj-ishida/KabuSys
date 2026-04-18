CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

Added
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止制御に data/stop_requested.flag を使用。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（注意点として明記）。
- run_execution.py: ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 SQLite（data/paper_trading.db）に記録。実運用 DB と分離。
  - 停止制御に data/stop_requested.flag、PID 管理用に data/execution.pid を使用。
  - スレッドで ExecutionEngine をデーモン実行し、停止フラグ検知で安全に停止。
- config.py: 設定管理クラス Settings を追加。
  - .env 自動読み込み（.env, .env.local、OS 環境変数保護あり）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
  - 多数の環境変数ラッパーを提供（J-Quants / kabu API / DB パス / モニタ閾値 / ペーパートレード設定等）。
  - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）と paper_sqlite_path の分離用設定。
- config_setup.py: 対話式 .env ウィザードを追加。
  - .env の初回作成・更新を支援する CLI（secret マスク、選択肢、デフォルト、保存確認）。
- validate_config.py: 起動前設定検証 CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス・config/*.yaml の存在・パース検証、live 環境向けガードなど。
  - --strict オプションで警告を失敗扱いに可能。
- utils/logging_setup.py: ロギング初期化ユーティリティを追加。
  - コンソール出力を stdout に集約、TimedRotatingFileHandler による日次ローテーション（30 日保持）を設定。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
  - Windows/Linux/Mac 向けに高/標準/低の優先度設定をラップ（psutil を使用）。フォールバックと例外処理あり。
  - set_cpu_affinity による先頭 N コアへのピン留め機能（利用不可時はスキップ）。
- portfolio/*: ポートフォリオ構築関連モジュール群を追加（純粋関数で副作用なし）。
  - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - risk_adjustment: セクター集中制限 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier)。
  - position_sizing: 発注株数算出 (calc_position_sizes) — risk_based / equal / score の配分方式、lot 単位丸め、aggregate cap によるスケーリング、手数料スライド用 cost_buffer 等をサポート。
- tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
  - SQLite DB（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
  - レポートに使用する閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms など）。
- research/factor_research.py: ファクター計算モジュール骨子を追加（Momentum, Value, Volatility, Liquidity を想定、DuckDB を利用して prices_daily/raw_financials を参照）。
- パッケージ初期化: __version__ = "0.1.0" を設定。

Changed
- ログ出力の一元化: 全スクリプトは setup_logging() を呼び出して統一ログ設定を利用するように設計。
- DB 初期化: init_monitoring_db(sqlite_conn) を両方の起動スクリプトで呼び、監視テーブルの存在を冪等的に保証。

Fixed
- .env パーサーの堅牢化: config._parse_env_line がクォート/エスケープ/インラインコメントを考慮するよう実装。export プレフィックス対応。

Security
- .env の生成テンプレートに「絶対に Git にコミットしないこと」を明記。

0.1.0 - 2026-04-18
------------------

Added
- 初期公開リリース。
  - 上記の各機能（monitoring / execution / config 管理 / 設定ウィザード / 設定検証 / ロギング / プロセス優先度 / ポートフォリオ構築 / ポジションサイジング / ペーパートレード検証ツール / ファクター計算骨子）を実装してパッケージとして公開。
  - ペーパートレードと本番 DB の明確な分離を実装（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）。
  - ExecutionEngine のリスク管理既定値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）し、初期ポートフォリオ値として broker.get_available_cash() を使用。
  - stop/kill フラグ（data/stop_requested.flag, data/kill.flag）および PID ファイルによる外部制御を導入。

Changed
- ドキュメント/CLI の使い勝手向上:
  - config_setup.py と validate_config.py により初期セットアップと起動前チェックを容易に。
  - logging_setup によりログ出力先を安定化（stdout とローテートファイルの併用）。

Fixed
- cross-platform 対応: process_priority の実装で Windows / POSIX の差分を吸収し、実行環境に依存しない API を提供。権限不足等の失敗は警告でスキップ。

Deprecated
- （なし）

Removed
- （なし）

Security
- .env の自動読み込みは OS 環境変数を保護（既存の OS 環境変数は上書きされない）する設計にした。明示的に .env.local で上書きする場合のみ許可。

注記 / 互換性に関する注意
- run_monitoring の実装は「監視データベース」に常に settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。KABUSYS_ENV による切替が期待される場合は注意してください（設計上、監視は環境に依らず本番 DB を想定しています）。
- process_priority / cpu_affinity は psutil に依存します。環境や権限により効果が発揮されない場合があります（失敗時は警告を出してスキップします）。
- position_sizing の lot_size は現状全銘柄共通の仮定（100）です。将来的に銘柄別 lot_map を導入する予定が示唆されています（TODO コメントあり）。
- research/factor_research.py はファクター計算の骨格を含みますが、未完成な箇所があるため（ソース末尾の途中切れ等）実運用で使用する際は該当関数の実装状態を確認してください。

リンク
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/

（この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースノートがある場合はそれに合わせて更新してください。）