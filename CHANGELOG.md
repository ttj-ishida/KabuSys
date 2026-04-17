# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本CHANGELOGは与えられたコードベースから実装内容を推測して作成しています。

## [Unreleased]

- マイナー改善・リファクタ（ログ出力の改善やデバッグ情報の追加など）
- テストや運用で発見された小さな修正を随時反映予定

---

## [0.1.0] - 2026-04-17

初回リリース。シンプルな日本株自動売買システムのコアユーティリティ群、CLI、ポートフォリオ構築ロジック、検証ツールなどを含みます。

### Added
- 一般
  - パッケージのバージョンを定義（kabusys.__version__ = 0.1.0）。
  - 基本的なモジュール構成（data, strategy, execution, monitoring 等の名前空間）をエクスポート。

- 設定管理
  - Settings クラスを実装。環境変数経由で各種設定（API トークン、DB パス、環境種別、監視閾値など）を安全に取得・検証するプロパティ群を提供。
  - 自動 .env ロード機能を追加（プロジェクトルートを探索し .env / .env.local を読み込む）。OS 環境変数は保護され、.env.local は上書き優先。
  - 環境変数のパースを強化（export 句、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。

- 環境設定・検証 CLI
  - config_setup ウィザードを追加（対話式に .env を作成・更新する）。秘匿値はマスク表示、確認プロンプト付きで保存。
  - validate_config CLI を追加。必須環境変数・KABUSYS_ENV の妥当性・DB パスや config/*.yaml の存在とパース（PyYAML があれば）・本番用ガードのチェック等を行い、--strict モードで警告も失敗扱いにできる。

- 実行 / 監視用スクリプト
  - run_execution.py を追加（ExecutionEngine 起動用スクリプト）。
    - KABUSYS_ENV=paper_trading 時は paper 用 SQLite（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いて実行時に適切なブローカークライアントを生成（MockBrokerClient を含む想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立ててセッションをスレッドで実行。停止フラグ（data/stop_requested.flag）を監視して安全終了。
    - ExecutionEngine の PID 管理用ファイルパス指定。
  - run_monitoring.py を追加（SystemMonitor のポーリングループ起動スクリプト）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は環境に関係なく本番向け sqlite_path を使用する設計（監視データは単一 DB に集約する想定）。
    - 停止フラグの検知（data/stop_requested.flag）でループを抜ける。

- 監視 DB 初期化支援
  - init_monitoring_db 呼び出しにより、監視用テーブルが存在することを保証（冪等に初期化）。

- プロセス制御ユーティリティ
  - utils.process_priority モジュールを追加。
    - set_process_priority(level) でプラットフォーム差を吸収して優先度指定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity を設定（指定が None の場合は何もしない）。
    - 権限不足や未対応プラットフォームでは警告を出して安全にスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重の重み計算（スコア全体が 0 の場合は等金額にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に同セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未定義値は警告して 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 重み・候補・リスクベース等に基づいて各銘柄の発注株数を算出。lot_size（単元株）で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap（スケールダウン）ロジックを実装。risk_based モードでは risk_pct / stop_loss_pct による株数計算。

- 研究用ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB 上の prices_daily テーブルを参照して計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率などを計算（データ不足時は None を返す）。
    - 計算は DuckDB 接続を受け取り SQL ウィンドウ関数で効率的に実行。

- 検証ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ（ms）などを算出し、事前定義した閾値に基づいて PASS/FAIL を判定。
    - DB パスはコマンドライン引数または PAPER_TRADING_SQLITE_PATH 環境変数で指定可能。

### Changed
- 環境変数の取り扱い
  - .env の自動読み込みにおいて OS 環境変数を保護（既存の環境変数が優先される）しつつ、.env.local は上書きに使えるようにした（ローカルオーバーライド対応）。
  - PAPER_TRADING 用の SQLite パスを Settings で提供し、paper_trading 環境では専用 DB を利用するように分離（本番データと分離して安全にペーパートレード可能）。

- 実行時の振る舞い
  - run_execution と run_monitoring の起動時にプロセス優先度を "high" に設定するフローを導入（最初に実行）。
  - 停止フラグ（data/stop_requested.flag）検出で安全終了する共通挙動を明確化。

- validate_config のチェック強化
  - .yaml ファイルの存在確認を行い、PyYAML 未導入時はパース検証をスキップして警告を出す。
  - KABUSYS_ENV が live の場合に追加の本番ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険な設定）を警告するチェックを追加。

### Fixed
- .env パーサの堅牢性向上
  - export プレフィックス付き行の対応、引用符付き値のバックスラッシュエスケープ処理、コメント判定の細かい挙動を修正し、実際の .env ファイルに含まれる多様な書式に耐性を持たせた。
- MONITOR_POLL_INTERVAL の扱い
  - 環境変数から読み取ったポーリング間隔が 0 以下や不正な文字列だった場合に ValueError を防ぎ、ログ警告のうえデフォルト（60 秒）へフォールバックするように修正。

### Security
- .env の生成テンプレートに「絶対に Git にコミットしないこと」を明示。config_setup の出力もその旨の注意を表示。

---

今後の予定（例）
- リアルタイム注文周りのテスト強化（ブローカー抽象の包括的ユニットテスト）
- 更なる監視項目・アラート（LINE 通知等）の拡張
- 銘柄別単元（lot_size）をマスタ化して position_sizing を拡張

--- 

注: 本CHANGELOGはコードの内容から推測して作成しています。実際のコミット履歴や公開リリースノートが存在する場合はそちらを優先してください。