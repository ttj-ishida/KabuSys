# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このファイルは、ソースコードの内容から推測した主要な変更点・実装内容を記載しています。

全般的な注意
- バージョン番号は src/kabusys/__init__.py の __version__ (= 0.1.0) に基づいています。
- 日付はこの推測生成日（2026-04-18）を用いています。実際のリリース日が異なる場合は適宜修正してください。

## [Unreleased]

- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションパッケージを追加（kabusys）。
  - バージョン定義: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 起動スクリプト / 実行ユーティリティを追加。
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - プロセス優先度を「high」に設定（utils.process_priority）。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（Mock/実ブローカーの切替を想定）。
    - ExecutionEngine を別スレッドで起動し、停止フラグ（data/stop_requested.flag）で安全に停止可能。
    - pid ファイル管理（data/execution.pid）を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）の検知でループ終了。
- 設定管理・ウィザード・検証ツールを追加。
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - .env のパースは export 形式、クォート、エスケープ、インラインコメント等に対応。
    - Settings クラスで各種設定プロパティを提供（DB パス、API トークン、監視しきい値、環境判定等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新。
    - 秘匿項目はマスク表示、デフォルト/既存値を考慮した入力フローを提供。
    - 書き込み時に .env のテンプレートヘッダーを付加。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的妥当性検査を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パス父ディレクトリ存在チェック、YAML パース（PyYAML が存在する場合）、本番環境向けのガードチェック等を実施。
    - --strict オプションで警告を失敗扱いにできる。
- ログ・プロセス管理ユーティリティを追加。
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30 日保持）を設定するユーティリティ。
    - LOG_LEVEL / LOG_DIR の解決・既存ハンドラのクリア・フォールバック動作を実装。
  - utils/process_priority.py
    - Windows / POSIX（Linux/macOS/FreeBSD）を吸収したプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は安全にスキップして警告ログを出力。
- ポートフォリオ構築・リスク調整関係モジュールを追加（純粋関数化）。
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックし警告ログを出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を実施する apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - weight / candidates / リスク比率に基づく株数算出 calc_position_sizes を実装。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮したスケーリングロジック。
    - aggregate cap 超過時のスケールダウンと端数処理（lot 単位での再配分）を実装。
- Execution 周りの基盤コンポーネントを実装済み（呼び出し側で組み立てられることを想定）。
  - order_repository, order_manager, risk_manager, reconciler, execution_engine（起動フローを run_execution で組み立て）。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を Execution スタート時に設定。
- 監視（Monitoring）基盤を用意。
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在保証を行う（冪等）。
  - SystemMonitor を使った check_once 呼び出しをポーリングで実行、例外はログに記録して次ループへ継続。
- Paper Trading 関連ツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB（デフォルト data/paper_trading.db）を解析し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）・リスク却下数等を集計してレポート出力。
    - PASS/FAIL 判定基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 latency <= 200 ms）を実装。
    - --from / --to / --db オプションをサポート。
- リサーチ（ファクター計算）モジュールの骨格を追加。
  - research/factor_research.py
    - Momentum/Value/Volatility/Liquidity 指標の設計方針と定数（期間等）が定義され、calc_momentum 等の関数実装の開始（DuckDB 経由で prices_daily/raw_financials を利用する想定）。
- パッケージのエクスポートを整理（portfolio パッケージの __all__ を整備）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数を .env に直書きするためのウィザードを提供しているが、.env を決してリポジトリにコミットしない旨を README/ウィザードヘッダで明示。

補足（実装上の注意点・既知の設計選択）
- .env 自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後や特殊な配置では自動ロードがスキップされうる。環境変数で KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化可能。
- run_monitoring は監視用 DB として常に Settings.sqlite_path（本番設定）を使用する設計。paper_trading 実行とは明確に分離している。
- position_sizing の価格フォールバックは未実装（価格欠損時は 0.0 を使うためエクスポージャー過小評価のリスクあり）。TODO コメントとして将来的な拡張を残している。
- utils/logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップしてコンソールログのみで継続する堅牢性を持つ。
- process_priority・cpu_affinity の設定は権限に依存し、失敗時は警告を出してスキップするため、運用環境による挙動差に注意。

もし CHANGELOG に追記したい (例: 正確なリリース日、リリースノートの言語、追加の変更履歴) 項目があれば指示ください。