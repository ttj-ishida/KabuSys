# Changelog

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の慣例に従って作成しています。  

- 未リリースの変更については [Unreleased] に記載します。  
- 各バージョンのエントリは実装内容から推測して記載しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-24

Added
- 基本機能の初回リリース。
- 起動/運用用スクリプトを追加:
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル（data/stop_requested.flag）を検知して安全に終了する仕様。Monitoring は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する挙動に合わせて実装。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。停止フラグ検知と PID ファイル管理（data/execution.pid）に対応。
- 環境設定関連 CLI を追加:
  - config_setup: 対話式ウィザードで .env を作成/更新する CLI。複数の設定項目を対話的に入力でき、シークレット値はマスク表示。保存前に確認を促す。
  - validate_config: .env と config/*.yaml の妥当性チェック CLI を追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL/DB パスの検証、PyYAML が存在する場合は YAML のパース検証、KABUSYS_ENV=live 時の追加ガード等を実行。--strict オプションで警告も失敗扱いにできる。
- 設定読み込み/管理:
  - Settings クラスを導入し、環境変数を型安全に取得するユーティリティを提供（jquants_refresh_token、kabu_api_password、duckdb_path、sqlite_path、paper_sqlite_path、pid/kill flag パス、各種閾値など）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env 読み込み無効化をサポート。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。.env/.env.local の取り扱い（.env.local が上書き）と OS 環境変数の保護（上書き禁止）に対応。
  - .env のパースは export KEY=val、クォート/エスケープ、インラインコメント等を考慮した実装を導入。
- ロギング・プロセス管理ユーティリティ:
  - logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定する共通セットアップを追加。LOG_LEVEL / LOG_DIR の解決順やログディレクトリ作成時のフォールトトレランスを実装。
  - process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定関数を追加。Windows/Linux/macOS 等の差分を吸収し、権限不足などで設定できない場合は警告を出してスキップする。
- データベース / 分析統合:
  - duckdb の統合（duckdb 接続を利用）を導入。monitoring や execution の起動時に duckdb へ接続するようになっている。
- Execution サブシステムの基盤:
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）等の構成要素を起動スクリプトから組み立てる処理を追加。RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors など）を指定し、初期ポートフォリオ値はブローカーから取得する設計。
- Paper Trading サポート:
  - Settings.paper_fill_mode（instant/partial/never/reject）で MockBrokerClient の挙動を制御可能に。paper_trading モード時は専用 SQLite を使用して本番データと完全分離する方針。
- portfolio モジュール（銘柄選定・配分・ポジションサイズ）:
  - portfolio_builder: シグナルから候補抽出（select_candidates）、等配分（calc_equal_weights）、スコア比率配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分へフォールバック。
  - risk_adjustment: セクター集中（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。unknown セクターに関する挙動やレジーム別乗数（bull/neutral/bear）を明記。
  - position_sizing: allocation_method（risk_based, equal, score）に基づく発注株数計算を実装。単元株（lot_size）への丸め、1 銘柄上限・aggregate cap（available_cash）によるスケーリング、コストバッファの考慮、残余キャッシュを使った端数処理等のロジックを実装。
- tools:
  - paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs テーブルから各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し、Pass/Fail 判定（閾値はソース内の定数）を出力。P95 計算や日付フィルタ、DB パスの解決（コマンドラインオプションと環境変数対応）を備える。
- research:
  - factor_research のスキャフォールドを追加。DuckDB の prices_daily/raw_financials を使って Momentum/Value/Volatility/Liquidity 等の因子を計算する設計（モジュール内に定数と calc_momentum の雛形あり）。将来的な拡張を想定した設計を反映。

Changed
- なし（初回リリースのため新規追加が中心）

Fixed
- なし（初回リリース）

Security
- .env ファイルは生成時にマスクの注意書きを追加（config_setup の出力で .env を絶対に Git にコミットしない旨を明示）。

Notes / 実装上の注意点（ドキュメント的補足）
- run_monitoring は Monitoring 用 DB として Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用する仕様。paper_trading モードでも監視 DB は分離されない点に留意。
- run_execution は paper_trading モード時に settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離する設計。
- .env 自動ロードはプロジェクトルートが検出できない場合や KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を設定した場合はスキップされる。
- logging_setup はログディレクトリ作成に失敗してもコンソール出力のみで継続するため、起動が不可能になることはない（ただしファイル出力は無効化される）。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、失敗した場合は警告ログを出す（動作継続）。

---

参照:
- パッケージバージョン: __version__ = "0.1.0" (パッケージ初期リリース)