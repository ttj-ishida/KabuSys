# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このファイルは、リポジトリに含まれるコードから推測される初期のリリース内容をまとめたものです。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17
Initial release — 基本機能の実装と CLI / ユーティリティ群を提供

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュールエクスポートを整理（portfolio 関連関数をトップレベルで利用可能に）。

- 設定管理
  - Settings クラスによる環境変数ベースの設定取得機能を実装（kabusys.config）。
    - J-Quants / kabuステーション / LINE / DB / 監視しきい値等のプロパティを提供。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の Paper Trading 用設定をサポート。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出と .env / .env.local の順で読み込み）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - 強制取得用ユーティリティ（未設定時に ValueError を発生）。

- 設定ユーティリティ / CLI
  - 対話式環境設定ウィザード（kabusys.config_setup）を追加。
    - .env の初期作成・更新を対話的に実施可能。
    - デフォルト・選択肢・シークレット入力の取り扱い、.env 書き出し機能を提供。
  - 設定検証 CLI（kabusys.validate_config）を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証。
    - DUCKDB / SQLITE のパス親ディレクトリ存在チェック。
    - config/*.yaml の存在確認および PyYAML が利用可能な場合はパース検証。
    - KABUSYS_ENV=live に対するガード（LINE 通知設定や Kill Flag のクリア設定に関する警告）。
    - --strict オプションで警告も失敗扱いにできる。

- 実行用スクリプト
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動制御。
    - stop flag（data/stop_requested.flag）による停止、実行中の PID ファイル管理、デーモンスレッド起動・停止処理。
  - SystemMonitor 起動スクリプト（kabusys.run_monitoring）を追加。
    - 監視ループ（ポーリング）を実行、MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する仕様。
    - stop flag によるループ終了検知、例外発生時のログ継続。

- 監視 DB 初期化
  - init_monitoring_db を呼び出して監視用テーブルが存在することを保証（冪等）。

- Paper Trading 検証ツール
  - paper_verification_report（kabusys.tools.paper_verification_report）を追加。
    - ペーパートレード SQLite（デフォルト data/paper_trading.db）から各種指標を集計・レポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - 期間フィルタ（--from / --to）、DB 指定（--db）に対応。
    - Pass/Fail 判定基準を定義して判定を出力。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder: 候補選定 (select_candidates)、等ウェイト (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックし警告を出力。
  - risk_adjustment: セクター集中制限 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier) を実装。
    - セクター上限判定（売却予定銘柄の除外、"unknown" セクターは上限適用外）。
    - レジームに応じた乗数（bull/neutral/bear）を提供し、未知のレジームはフォールバック（警告）。
  - position_sizing: 発注株数決定ロジック（calc_position_sizes）を実装。
    - allocation_method ("risk_based", "equal", "score") をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケーリング）を実装。
    - cost_buffer を考慮した保守的見積り、スケールダウン時の端数処理（残余キャッシュでの lot 単位追加配分）を実装。

- リサーチ / ファクター計算
  - factor_research モジュールを追加（DuckDB を使った定量ファクター計算）。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR20）等の計算関数を実装。
    - prices_daily テーブルを前提として効率的に計算（ウィンドウ関数等を利用）。
    - 空データ・データ不足時の None 扱い、ログ出力によるデバッグ情報を提供。

- ユーティリティ
  - process_priority（kabusys.utils.process_priority）を実装。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応した優先度設定（high/normal/low）。
    - CPU affinity 固定機能（set_cpu_affinity）を追加。
    - 許可エラーや未対応 OS に対して安全にスキップしログ出力。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- .env パーサーは export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント相当の取り扱いを考慮した実装になっており、実運用での柔軟性を持たせています。
- config_setup の .env 書き込みテンプレートは Git にコミットしない旨のヘッダを出力します。
- Execution / Monitoring の両スクリプトとも起動直後にプロセス優先度を "high" に設定し、監視・発注処理の優先度を上げる設計になっています（権限不足時は警告を出して続行）。
- Paper Trading（ペーパートレード）は本番 DB と明確に分離される設計（PAPER_TRADING_SQLITE_PATH / Settings.paper_sqlite_path）。
- position_sizing のアルゴリズムは、価格欠損や価格が 0 の場合を安全にスキップする実装になっていますが、価格欠損時のエクスポージャー過小評価に関する TODO コメントがあります（将来的にフォールバック価格を導入予定）。

---
この CHANGELOG はコードから推測して作成しています。実際のリリースノート作成時は、コミットメッセージやリリース履歴と照合して調整してください。