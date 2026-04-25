# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」準拠です。

最新: 未リリースの変更はこの下の Unreleased に記載してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-25
初回リリース — KabuSys コードベースの基本機能を実装しました。主な追加点・振る舞いは以下の通りです。

### 追加 (Added)
- 全体
  - プロジェクト初版の公開。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag ファイルで制御。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV が `paper_trading` の場合はペーパートレード用 DB（data/paper_trading.db）・Mock ブローカを使用する仕組みを実装。実行中の PID 保存・停止フラグ検出による安全停止に対応。

- 設定管理 / ユーティリティ
  - config.Settings: 環境変数ベースの設定取得クラスを実装。多くのプロパティ（DB パス、API トークン、しきい値、環境種別など）を提供。
  - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。.env のパースは export 形式・クォート・インラインコメント等に対応。
  - config_setup: 対話式 .env 作成ウィザードを追加。必須・任意項目の入力支援、既存 .env の読み込み・編集をサポート。
  - validate_config: 起動前に .env と config/*.yaml の基本チェックを行う CLI を追加（必須 env チェック、KABUSYS_ENV 検証、YAML パースチェック、DB パス警告、live 環境向け追加警告等）。--strict オプションで警告をエラー扱いに可能。

- ロギング / プロセス制御
  - utils.logging_setup.setup_logging: stdout 出力の StreamHandler と日次ローテートの file handler（TimedRotatingFileHandler）をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成失敗時にファイル出力をスキップする安全策あり。ログレベル解決ルールを実装。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows と POSIX の差分吸収）と CPU affinity 設定関数を追加。アクセス権限不足などの失敗は警告でスキップ。

- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder: シグナル選定と等金額／スコア加重の重み計算を実装（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中上限チェックとレジーム乗数（apply_sector_cap, calc_regime_multiplier）を実装。
  - portfolio.position_sizing: 単元株丸め・risk_based / equal / score の発注株数計算を実装。aggregate cap スケーリング、lot 単位の再配分ロジック、コストバッファ対応などを含む。

- 解析 / レポート
  - tools.paper_verification_report: ペーパートレード用 SQLite DB を参照して稼働率・注文成功率・送信率・レイテンシ（P95 含む）を解析し、PASS/FAIL 判定のレポートを出力する CLI を追加。閾値はソースに定義（稼働率 99%、成立率 90% 等）。P95 計算、期間フィルタ、DB 存在チェックに対応。

- リサーチ基盤（部分実装）
  - research.factor_research: Momentum / Value / Volatility / Liquidity 等のファクター計算を行うモジュールを追加（設計と一部実装）。DuckDB 接続を受け prices_daily / raw_financials を用いる設計。

### 変更 (Changed)
- ログ出力の既定挙動を stdout に統一
  - setup_logging で StreamHandler を stdout に向ける設計に変更（タスクスケジューラや cron でのリダイレクトを考慮）。

- DB 利用の分離
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して本番監視 DB と完全に分離する挙動を明確化（安全設計）。

### 修正 (Fixed)
- 環境変数の堅牢性向上
  - .env パーサーで export 先頭文字列、クォート内のエスケープ、インラインコメント、空行/コメント行の無視などに対応し、不正な .env 行をスキップするように修正。
  - MONITOR_POLL_INTERVAL（run_monitoring）で不正な（0 以下や整数でない）値を検知した場合にデフォルト（60 秒）へフォールバックし、警告出力する安全措置を追加。

- エラー耐性強化
  - run_monitoring のループ内で monitor.check_once() が例外を投げてもログ出力してループを継続するように変更（単一失敗で監視全体が停止しない）。

- プロセス優先度設定の失敗を安全に扱う
  - set_process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に警告を出して処理を継続するように改善。

### ドキュメント (Documentation)
- 各モジュールに docstring と使用方法を追加（起動スクリプト、config_setup、validate_config、paper_verification_report、各ユーティリティなど）。  
- PortfolioConstruction / StrategyModel に基づく設計コメントをソース内に記載。

### 既知の問題 / 注意点 (Known issues / Notes)
- research.factor_research の一部関数は実装途中（ファイル末尾が途切れている/未完成の箇所あり）。本リリースでは主要機能（起動・発注・監視・レポート・設定）が優先されています。
- position_sizing の価格欠損（price が 0 または未定義）の扱いに関する注釈あり（TODO: 前日終値等のフォールバックを検討）。
- .env ファイルは機密情報を含むため、README 等で Git コミットを避けるよう明記することを推奨。

---

作成日: 2026-04-25

（必要であれば、これを基に将来のリリース向けに Unreleased セクションを更新してください。）