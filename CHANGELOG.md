# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
慣習に従いセクションは主に Added / Changed / Fixed / Removed / Security に分類しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-18

初回公開リリース。日本株自動売買フレームワーク「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - __version__ を "0.1.0" に設定。パッケージエクスポートに主要モジュールを追加。

- 環境設定・管理
  - 環境変数読み込み・管理モジュール（kabusys.config）
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - export プレフィックスやクォートされた値、インラインコメント、エスケープを考慮した堅牢な .env パーサー。
    - OS 環境変数を保護する protected 機能（.env.local の上書き制御）。
    - Settings クラスに各種設定プロパティを実装（DBパス、APIトークン、監視閾値、環境種別判定等）。
    - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定をサポート。

  - 環境設定ウィザード CLI（kabusys.config_setup）
    - 対話式で .env を初期作成/更新するウィザードを実装。
    - シークレット項目はマスク表示、デフォルト値や選択肢を提供。
    - .env ファイルのテンプレート出力機能を実装。

  - 設定検証 CLI（kabusys.validate_config）
    - 必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DBパス・config/*.yaml の存在と簡易パース検証を行う。
    - --strict オプションで警告をエラー扱いにするモードを提供。
    - 本番（live）環境向けの追加ガード（LINE 設定の未設定警告や Kill Switch の自動クリア警告）。

- 実行スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - Process 優先度を High に設定する呼び出しを追加。
    - paper_trading 環境では MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）で本番 DB と分離。
    - 実行用 PID ファイル制御、stop フラグ検知による安全停止処理を実装。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組立てと起動ループを実装。

  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は常に本番 sqlite_path を使用して監視 DB を初期化。
    - 停止フラグ検知、例外発生時のログ出力とリトライ継続を実装。

- ログ・プロセスユーティリティ
  - 共通ログ設定ユーティリティ（kabusys.utils.logging_setup）
    - stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（デフォルト logs/）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書き対応、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）をサポート。
    - 既存ハンドラの安全なクローズと再設定を実装。
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX(Linux, macOS, FreeBSD) の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - psutil を使用し、権限不足や未実装機能に対しては警告を出して安全にスキップする実装。

- ポートフォリオ構築（純関数群）
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates（スコア降順、タイブレークロジック） / calc_equal_weights / calc_score_weights（全スコアが0の際のフォールバック）を実装。
  - セクター制約・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap（既存保有比率に基づく新規候補の除外ロジック）。unknown セクターの扱い、sell_codes を除外する挙動を実装。
    - calc_regime_multiplier（bull/neutral/bear に対する乗数と未知レジームのフォールバック警告）。
  - ポジションサイズ計算（kabusys.portfolio.position_sizing）
    - allocation_method ("risk_based", "equal", "score") に対応した株数計算。
    - リスクベース計算、単元株（lot_size）丸め、単銘柄上限・aggregate cap のスケールダウンと残差配分ロジックを実装。
    - cost_buffer を用いた保守的コスト見積り対応。

- 研究用ファクター計算スケルトン（kabusys.research.factor_research）
  - Momentum / MA / ATR / Volume 等の定数と calc_momentum のインターフェースを追加（DuckDB 接続を受け取る設計）。
  - データ不十分時の None を返す挙動やパフォーマンス考慮の設計方針を明記。

- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（P95 等）を算出し PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db。--db/環境変数で上書き可能。
    - P95 計算、閾値（稼働率 99% 等）のデフォルトを実装。

- DB 初期化補助
  - monitoring_db の初期化呼び出しを実行スクリプト側で行い、監視テーブル存在を保証（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 機密情報（トークン・パスワード）の取り扱いに関して
  - config_setup の出力で .env を Git にコミットしない旨を明記。
  - Settings._require は未設定時に ValueError を投げるため、起動前に必須環境変数の存在を強制可能。

### Notes / Migration
- 環境変数自動読み込み
  - デフォルトで .env/.env.local を自動読み込みします。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading と live の DB 分離
  - paper_trading 環境では paper_trading 専用の SQLite が使われ、本番とは完全に分離されます（PAPER_TRADING_SQLITE_PATH で上書き可能）。
- ログ出力
  - デフォルトログディレクトリは logs/。ディレクトリ作成に失敗した場合はファイル出力を行わずコンソール出力のみになります。
- プロセス優先度
  - セットする際に権限不足で失敗する可能性があるため、その場合は警告を出力してスキップします。

### Known issues / TODO
- research.factor_research モジュールは計算の枠組み・定数を実装しているものの、ファンクション群の実装が途中の箇所（ファイル末尾が途中で切れている等）が存在します。今後のリリースで完成させる予定です。
- position_sizing の価格欠損時の挙動について TODO コメントあり（フォールバック価格の導入検討）。
- 将来的に単元株（lot_size）を銘柄別に持たせるなど拡張を計画。

---

この CHANGELOG はコードベースから推測して作成しています。リリースノートの追記・修正があればお知らせください。