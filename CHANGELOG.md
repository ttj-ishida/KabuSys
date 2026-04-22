CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
主要なバージョン、変更点、注意事項を日本語で記載しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-22
------------------

Added
- 基本アプリケーション構成
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
- 設定・環境読み込み
  - Settings クラスを追加し、環境変数経由で各種設定を取得可能に。
  - 自動 .env ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml）。
  - .env 読み込みの優先度: OS 環境変数 > .env.local > .env。自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - .env パーサを実装（export プレフィックス対応、クォート文字列のバックスラッシュエスケープ処理、インラインコメントの扱い）。
  - 環境変数必須チェック用のヘルパ（_require）を追加。
- CLI / 管理ツール
  - 環境設定ウィザード: config_setup.py を追加（対話式で .env の作成・更新、シークレット値はマスク表示）。
  - 設定検証ツール: validate_config.py を追加（必須環境変数やファイルパス、config/*.yaml の存在/パースを検証、--strict オプションをサポート）。
  - Paper Trading 検証レポート生成ツール: tools/paper_verification_report.py を追加（期間指定、P95 等の指標を出力）。
- 実行スクリプト
  - 実行エンジン起動スクリプト: run_execution.py を追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 等の組み立て。
    - エンジンは別スレッドで実行し、data/stop_requested.flag による停止制御を実装。実行中の PID を data/execution.pid に保存する仕組み（pid_file の注入をサポート）。
  - 監視ループ起動スクリプト: run_monitoring.py を追加。
    - SystemMonitor を使った単発チェックをポーリングで実行。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 監視は環境（development/paper_trading/live）に関係なく production 用 sqlite_path を使用する旨を明示。
- DB/分析連携
  - DuckDB 接続の利用を全体でサポート（Settings.duckdb_path）。run_* スクリプトは sqlite3 と duckdb の両方に接続。
  - 監視用 DB 初期化を行う init_monitoring_db 呼び出しを組み込み（冪等に実行）。
- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装。score_weights は全スコアが 0.0 の場合に等金額配分へフォールバックし warning を出力。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中上限の適用）と calc_regime_multiplier（市場レジームに基づく乗数）を実装。unknown セクターは上限適用の対象外に。
  - portfolio.position_sizing: calc_position_sizes を実装。risk_based / equal / score の割当方式をサポートし、lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングを実装。価格欠損や 0 以下の価格に対する安全処理あり。
- ユーティリティ
  - logging_setup: 統一ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日分保持）のファイルハンドラをルートロガーに設定。LOG_DIR や LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時にはファイル出力を無効化してコンソールのみで継続。
  - process_priority: クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows の priority class / POSIX の nice を抽象化）。CPU affinity 設定関数 set_cpu_affinity を提供。
- 研究用モジュール（部分実装）
  - research.factor_research にモメンタム系ファクター calc_momentum の実装（設計・定数定義、ターゲット日ベースの計算を開始）。DuckDB の prices_daily を参照する想定。P95 など解析ユーティリティを含む（ファイル途中まで実装）。

Changed
- ログ出力設計
  - StreamHandler は stderr ではなく stdout を使う方針を採用（cron/task scheduler で stdout/stderr を一本化してリダイレクトしやすくするため）。
- DB 運用方針
  - paper_trading 環境では paper_trading 用の SQLite を使い本番 DB と完全分離する仕様を明確化。

Fixed
- .env 読み込みの堅牢化
  - export プレフィックス、クォートされた値内でのバックスラッシュエスケープ、インラインコメントの扱いなどを細かく処理することで、.env の誤読を防止。
  - .env の読み込み時に OS 環境変数を保護する protected 引数を導入し、明示的に override したい場合のみ上書きする挙動を実現。
- 環境変数検証
  - validate_config による起動前チェックを追加し、必須環境変数未設定やプレースホルダ値の検出を行えるように。
- 実行・監視起動の堅牢化
  - run_monitoring で MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバック（time.sleep に負の値を渡す事故を防止）。
  - run_execution / run_monitoring 共に stop flag（data/stop_requested.flag）の検出で安全に停止する仕組みを実装。
  - process_priority や CPU affinity の設定が失敗した場合（権限不足や未対応 OS）に警告を出してスキップする安全策を導入。
- レポート / 集計の堅牢化
  - tools/paper_verification_report はテーブル欠損時に sqlite3.OperationalError をキャッチして指標の計算をスキップまたは N/A を返すフォールバック実装を追加。P95 の計算をヘルパ関数 _p95 で実装。
- ポートフォリオ計算の安全弁
  - position_sizing で価格が欠損・0 の場合にスキップするロジックを追加し、ゼロ除算や不正な株数計算を防止。

Security
- .env 取り扱いの注意喚起を追加（config_setup が生成する .env のヘッダに「絶対に Git にコミットしないこと」と明示）。
- config_setup の対話表示ではシークレット項目をマスク表示（****）するようにして誤漏洩リスクを低減。

Notes / Known limitations
- research.factor_research はファイル末尾が途中で切れている箇所があり、完全実装は継続作業が必要（calc_momentum の実装途中）。
- 一部の将来的拡張を想定した TODO コメントが残っている（例: position_sizing の銘柄別 lot_size 対応、price フォールバック戦略など）。
- run_monitoring が「監視は環境にかかわらず本番 sqlite_path を使用する」仕様は意図的だが、運用ポリシーに応じて変更を検討する場合がある。

---

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の全ファクター算出）。
- テストカバレッジ拡大（ユニットテスト、CI の導入）。
- 実行エンジン / ブローカーインタフェースのモック強化と paper_trading の検証自動化。