# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
主要リリースのみを記載しており、コードベースから推測可能な実装内容・振る舞いを要約しています。

フォーマット:
- メジャーな機能追加や破壊的変更は Added / Changed / Removed / Fixed に分類しています。
- 日付は本リポジトリの現行コードを基にした推定リリース日を使用しています。

## [Unreleased]

- （現時点では未リリースの作業は特に検出されていません。今後の変更はここに記載されます）

## [0.1.0] - 2026-04-21

### Added
- プロジェクト初期リリース。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory 経由でブローカークライアントを作成し、 ExecutionEngine をスレッドで実行。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB (data/paper_trading.db) を使用し、本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag によるフラグ検知で行う。
- 設定・環境管理
  - config.py: .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml を基準）、環境変数のパースロジック、Settings クラスによるプロパティベースの設定提供。PAPER_FILL_MODE 等の検証や paper_trading 用 DB パスなどのデフォルトを定義。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑制に対応。
  - config_setup.py: 対話式 .env ウィザードを提供。シークレットマスク表示、選択肢サポート、.env の読み書き（テンプレート生成）。
  - validate_config.py: 起動前検証 CLI。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML がある場合）などを検査。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中上限の適用）、calc_regime_multiplier（market regime に応じた乗数: bull/neutral/bear など、未知の値はフォールバックで警告）。
  - portfolio.position_sizing: calc_position_sizes（allocation_method: risk_based / equal / score をサポート、lot_size 単位丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリング実装、残差分配ロジック）。
- ユーティリティ
  - utils/logging_setup.py: 共通ログ初期化ユーティリティ。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラをルートロガーに設定。LOG_DIR/LOG_LEVEL 環境変数や引数での上書きに対応。既存ハンドラのクリア実装、ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プラットフォームに依存しないプロセス優先度設定（Windows / POSIX に対応）および CPU affinity 設定ユーティリティ。権限不足などの失敗を警告として扱う。
- モニタリング・監視
  - monitoring モジュール（初期化用の DB 機能、SystemMonitor を想定）を組み込み、実行スクリプトから利用する構成。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH / デフォルト data/paper_trading.db）からレポートを生成。稼働率、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）などを集計し、しきい値に基づく PASS/FAIL 判定を行う。デフォルトの合格基準 (稼働率 >= 99.0%, fill >= 90%, send >= 95%, P95 <= 200 ms) を定義。
- リサーチ（未完/部分実装の可能性あり）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム、MA、ATR、流動性、バリュー等）を開始。設計方針、定数、calc_momentum の雛形を含む（ファイル末尾が未完の可能性あり）。
- パッケージメタ
  - __init__.py: バージョン __version__ = "0.1.0" を設定。公開モジュール一覧を __all__ で宣言。

### Changed
- 環境変数ロードの振る舞い
  - 自動ロード順序を OS 環境変数 > .env.local > .env とし、既存の OS 環境変数は保護される（protected set）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- ログの出力先およびハンドラの初期化方法を統一。既存ハンドラの排除と再作成により二重登録を防止。
- run_execution/run_monitoring でプロセス優先度を最初に設定する流れに統一（set_process_priority("high") の呼び出し）。

### Fixed
- .env パーサの堅牢化
  - config._parse_env_line においてシングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート外で '#' の直前が空白/タブの場合をコメントとみなす）などに対応。export KEY=val 形式のサポートを追加。
- .env の読み込みでファイルアクセス例外を警告で処理し、プログラムの停止を避ける実装に改善。
- ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を明示。ファイルハンドラ作成失敗時も例外を握り潰して継続。

### Deprecated
- なし（初期リリースのため該当なし）。

### Removed
- なし

---

注記（コードから推測した振る舞い）
- 実行停止は各プロセスとも data/stop_requested.flag（または設定に基づくパス）によるファイルフラグ検知で行うため、外部からの安全な停止に対応。
- Paper Trading 環境では発注処理にモックブローカ（MockBrokerClient）を用いる設計が想定され、本番 DB と完全に分離されるよう配慮されている。
- position sizing や risk_adjustment の実装は単元株（lot_size）での丸めや aggregate キャップのスケーリングなど現実的なオーダー数量算出ロジックを考慮している。
- research/factor_research.py は DuckDB を想定しており、prices_daily / raw_financials テーブルに基づく純粋関数群として設計されている（ただし一部実装が未完の可能性あり）。

この CHANGELOG は現行ソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・CHANGELOG の更新方針に従い、差分を明確にするとよいです。