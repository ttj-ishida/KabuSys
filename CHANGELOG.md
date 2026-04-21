# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新: Unreleased

## [Unreleased]

## [0.1.0] - 2026-04-21
最初の公開リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築関数群、検証・設定ウィザード、ペーパートレード検証ツールなどを追加しました。

### Added
- 基本情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を高（"high"）に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立て、別スレッドでエンジンを実行。停止フラグ（data/stop_requested.flag）で安全に停止可能。
    - init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や数値でない）はログ警告の上デフォルトにフォールバック。
    - 監視（monitoring）は KABUSYS_ENV に関係なく本番用の sqlite_path を使用する旨を明記（意図的に本番監視 DB を参照）。

- 設定関連
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を実装。これにより CWD に依存せず .env 自動ロードが可能。
    - .env/.env.local の自動ロード機構を追加（OS 環境変数優先、.env.local は上書き）。自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - .env の行パースを強化（`export KEY=val`、クォート値のバックスラッシュエスケープ、インラインコメントの扱い等に対応）。
    - Settings クラスを導入し、各種設定値をプロパティで取得可能に：
      - 必須値: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（未設定時はエラー）
      - DB パス: DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
      - Paper Trading 用: PAPER_FILL_MODE の検証（instant|partial|never|reject）、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）
      - 監視関連: pid_file_path, kill_flag_path, kill_flag_clear_on_start, 各種閾値（CPU/MEM/DISK）
      - env/log_level の検証（allowed 値チェック）、is_live/is_paper/is_dev の便宜プロパティ

  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。
    - 指定可能項目（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DUCKDB/SQLITE パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。
    - シークレット入力のマスク、選択肢提示、既存 .env の読み込み・Enter で再利用、保存前の確認表示を実装。
    - .env 書き出しフォーマットにはコメントヘッダを付与し、Git 管理しない旨を注記。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証を実施。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。
    - `--strict` オプションで警告を FAIL 扱いにする機能を追加。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせ、30 日分保持する設定を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - デフォルトで stdout を使用（cron 等で stdout/stderr を一本化する運用を想定）。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定、CPU affinity 固定機能を追加。
    - psutil を利用し、アクセス権限不足などで設定できない場合は警告ログでスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates：スコア降順、同点は signal_rank でタイブレーク）
    - 等金額配分（calc_equal_weights）
    - スコア加重配分（calc_score_weights）で全スコアが 0 の場合は等分配にフォールバックして警告

  - portfolio/risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）：既存保有のセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外。sell_codes を渡すと当日売却予定銘柄をエクスポージャ計算から除外できる。
    - レジーム乗数（calc_regime_multiplier）：regime に応じた乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。

  - portfolio/position_sizing.py
    - ポジションサイズ計算（calc_position_sizes）
      - allocation_method に応じた発注株数計算（risk_based / equal / score）。
      - リスクベース計算は (portfolio_value * risk_pct) / (price * stop_loss_pct) を基に算出。
      - 単元株（lot_size）単位で丸め、1 銘柄上限（max_position_pct）を適用。
      - 全体投下額が available_cash を超えた場合はスケールダウンし、残差は fractional remainder に基づき lot_size 単位で再配分するアルゴリズムを実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。

  - portfolio/__init__.py
    - 上記関数群をパッケージとしてエクスポート。

- リサーチ / ファクター計算（初期実装）
  - research/factor_research.py
    - DuckDB を使ったファクター計算モジュールの骨組みを追加（モメンタム、MA200、ATR、流動性等を想定）。設計方針と定数を定義。モメンタム計算関数の実装を開始（ファイル末尾で実装中）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から指標を集計して検証レポートを標準出力に出力するスクリプトを追加。
    - 集計指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg, max, P95）等。
    - P95 の計算、期間フィルタ（--from / --to）、DB 存在チェック、データ欠損時の gracefully な扱い、閾値に基づく PASS/FAIL 判定を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数やシークレット（API トークン、パスワード）は .env に保存する点をドキュメント化。config_setup で生成された .env を Git にコミットしないよう明記。

---

注記:
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされます（パッケージ配布後の安全性を考慮）。
- run_monitoring が常に本番用 monitoring DB を参照する設計は意図的です。テストや開発環境で別の動作を期待する場合は設定やコードの見直しを検討してください。
- factor_research モジュールは継続的に実装を進める予定です（詳細なファクター計算ロジックは今後追加）。

もしリリースノートに追加してほしい具体的な点（例: 重要な設計上の注意、運用時のコマンド例、環境変数一覧など）があれば教えてください。必要に応じて CHANGELOG を拡張します。