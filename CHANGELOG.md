# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
変更は semver に従って管理してください。

## [Unreleased]

（今後の変更や修正をここに記載）

---

## [0.1.0] - 2026-04-19

初回公開リリース。日本株自動売買フレームワーク「KabuSys」のコアユーティリティ、実行・監視スクリプト、ポートフォリオ構築ロジック、設定管理ツール群、および解析補助ツールを収録。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - DuckDB と SQLite を併用するデータアクセス基盤を導入（設定からパスを取得して接続）。
- 起動／ランタイム
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 DB へ記録し本番 DB と分離する挙動を実装。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組みを実装。
    - 実行中の PID を data/execution.pid に保存する仕組み（pid_file に対応）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒、無効値は警告してデフォルトフォールバック）。
    - 停止フラグの検知でループを終了。
    - 監視は常に本番用 sqlite_path を使用する（環境に依存しない）。
- 設定・検証
  - config.py: 環境変数読み込み・管理モジュールを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づき .env/.env.local を自動ロード（OS 環境変数を保護）。
    - .env 行パーサは export 形式・クォート・エスケープ・インラインコメントに対応。
    - Settings クラスで各種設定（J-Quants トークン、kabuAPI、DB パス、PID・Kill flag、閾値、環境判定メソッド等）を提供。
    - PAPER_FILL_MODE のバリデーションを実装（instant/partial/never/reject）。
  - config_setup.py: .env の対話式ウィザードを追加。
    - デフォルト値や選択肢・説明を表示し対話的に .env を生成／更新。
    - シークレットは入力時にマスクして表示。
  - validate_config.py: 起動前に環境変数や config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在およびパース検証（PyYAML が存在する場合）。
    - KABUSYS_ENV=live 時の追加警告（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性等）。
    - --strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 買い候補の選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコア合計が 0 の場合は等金額にフォールバックし警告を出す。
  - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
    - unknown セクターはセクター上限の対象外とする動作を実装。
    - 未知レジームに対しては 1.0 でフォールバックし警告を出す。
  - portfolio.position_sizing: 発注株数計算ロジック（calc_position_sizes）を追加。
    - allocation_method に "risk_based"/"equal"/"score" をサポート。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer（手数料/スリッページ見積り）などを実装。
    - 価格欠損時のスキップ・ログ出力、スケールダウン時の端数再配分ロジックを実装。
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app>.log、30 日保持）をルートロガーに設定。
    - 既存ハンドラの二重設定を防止するため一旦クリアして再設定。
    - LOG_DIR 作成失敗時はファイル出力を無効化して警告を出力。
  - utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収して優先度設定を行う。psutil に依存しつつ失敗時は警告でスキップ。
    - cpu_affinity 設定（最初 N コアに固定）をサポート。
- 監視／検証ツール
  - monitoring.monitoring_db（参照・初期化呼び出し）と SystemMonitor 用の起動フローを実装（run_monitoring から利用）。
  - tools.paper_verification_report: ペーパートレード結果検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、成功率、送信率、レイテンシ（平均/最大/P95）を算出して標準出力でレポートを生成。
    - デフォルト閾値を定義し PASS/FAIL 判定を行う（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms など）。
    - --from / --to / --db オプションで期間・DB を指定可能。
- 解析
  - research.factor_research: ファクター計算モジュール（モメンタム等）を実装（DuckDB 接続を受け取り prices_daily / raw_financials から計算する設計）。（一部実装ファイルが含まれる）

### Changed
- なし（初回リリースのため新規追加が中心）

### Fixed
- 設定読み込み関連
  - .env のパース挙動を堅牢化（export 形式、クォート・エスケープ、インラインコメントの取り扱いを明確化）。
- ロギング
  - ログディレクトリ作成失敗時にコンソール出力のみで継続する耐障害性を追加。

### Security
- シークレット値（J-Quants トークン / kabu API パスワード 等）は .env で管理する方針を明記。config_setup の出力にて .env を Git コミットしないよう注意喚起を追加。

---

開発・運用に関する補足:
- 本プロジェクトは本番（live）/ペーパー（paper_trading）/開発（development）環境を明確に分離しています。起動前に python -m kabusys.validate_config で設定検証を推奨します。
- ログ設定・プロセス優先度の設定は起動スクリプトの最初で行われます（実行ユーザーの権限により設定が適用できない場合は警告が出ます）。
- DB の初期化（監視テーブル等）は起動時に冪等に実行されます。

もし特定モジュール（例: ExecutionEngine, SystemMonitor, monitoring_db, BrokerClientFactory 等）の動作や API 仕様について詳細な CHANGELOG 項目が必要であれば、該当ファイル群の差分情報や追加の説明を提供してください。