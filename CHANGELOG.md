# Changelog

すべての日付は UTC ではなく、リリース時点のローカルカレンダー日を使用しています。

フォーマットは "Keep a Changelog" に準拠します。
- 参照: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成とバージョン情報を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`

- 実行スクリプト（起動用 CLI）
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の紙口座 DB（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - BrokerClientFactory を通じてブローカークライアント生成をサポート。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定する処理を実行（utils.process_priority）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒、無効な値は警告を出してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する設計（settings.sqlite_path）。

- 設定管理とユーティリティ
  - config.py
    - .env の自動読み込みロジックを実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env と .env.local の読み込み順と上書きルール（OS 環境変数保護）を実装。
    - 複数のアプリ設定プロパティを提供（DB パス、API トークン、PID/kill flag パス、閾値など）。
    - PAPER_FILL_MODE の検証（有効値チェック）と paper_sqlite_path のサポート。
    - KABUSYS_ENV の検証（development / paper_trading / live）とログレベル検証。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - デフォルト値・選択肢・シークレット入力などに対応し、既存 .env の読み込み再利用が可能。
    - 保存前に内容確認プロンプトを表示。

  - validate_config.py
    - 起動前検証 CLI を追加（必須環境変数の未設定検出、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの確認、config/*.yaml の存在確認と（PyYAML があれば）パース検査、live 環境向けの追加ガード）。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder
    - シグナル選定（スコア降順・タイブレークに signal_rank）と候補上限（max_positions）選定機能。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全スコアが 0 の場合は等金額にフォールバックして警告を出力。

  - portfolio.risk_adjustment
    - セクター集中制限の適用（apply_sector_cap）：既存保有のセクター露出が閾値を超える場合、そのセクターの新規候補を除外。
      - "unknown" セクターは上限適用対象外（除外しない）。
      - 売却予定銘柄をエクスポージャー計算から除外可能。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）：`bull`/`neutral`/`bear` をマップし、未知の値は 1.0 でフォールバック（警告出力）。

  - portfolio.position_sizing
    - 発注株数決定ロジック（calc_position_sizes）を実装。
      - allocation_method: `risk_based` / `equal` / `score` に対応。
      - lot_size（単元）に従った丸め、price がない銘柄はスキップ。
      - per-stock 上限（max_position_pct）、aggregate cap（available_cash）を適用し、必要ならスケーリングと残差配分を行う。
      - cost_buffer を導入し手数料/スリッページを保守的に見積もる。

- 研究（research）モジュール
  - research.factor_research（モメンタム計算の枠組み）
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する計算設計を導入。
    - モメンタム指標（1M/3M/6M リターン、MA200 乖離率）や ATR/出来高などの計算方針を定義（関数 calc_momentum の骨組みを含む）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）、リスク却下数。
    - デフォルト閾値を設定し（稼働率 99%、成立率 90% 等）、Pass/Fail 判定を出力。
    - --from / --to / --db オプション対応、PAPER_TRADING_SQLITE_PATH 環境変数経由で DB 指定が可能。

- 汎用ユーティリティ
  - utils.logging_setup
    - 統一的なログ設定関数 setup_logging を追加。
    - stdout への StreamHandler と日次ローテーションの FileHandler（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続し、失敗を標準エラーに出力。
    - ログレベル／ログディレクトリの解決ルールを実装。

  - utils.process_priority
    - cross-platform なプロセス優先度設定と CPU affinity 設定を追加（psutil を利用）。
    - Windows と POSIX（Linux/Mac/FreeBSD）向けの nice/priority 設定を吸収。
    - 設定失敗時は警告を出してスキップし、安全に動作を続ける。

- その他
  - 起動・監視系で使用する停止フラグ／PID ファイルのパスやデフォルトパス（data ディレクトリ）の取り扱いを導入。
  - DuckDB/SQLite を併用するデータアクセスの初期化（monitoring DB 初期化関数呼び出し）をスクリプトに統合。

### Changed
- （初回リリースのため該当なし）

### Fixed
- config の .env パーサを堅牢化
  - export プレフィックス対応、クォートされた値のバックスラッシュエスケープ処理、行末コメントの扱いなどに対応。
- run_monitoring のポーリング間隔取得で無効値を検出してデフォルトにフォールバックするようにし、time.sleep に渡す不正値による例外を予防する実装を追加。

### Security
- .env を生成するウィザードで「.env は絶対に Git にコミットしないこと」を明示して出力ファイルヘッダに注意書きを追加。

### Removed
- （初回リリースのため該当なし）

---

Note:
- 本 CHANGELOG はコードベース（現在のソースファイル）から推測して作成しています。実際のリリース履歴や過去バージョンの差分に基づくものではありません。必要であれば、コミット履歴やタグ情報に合わせて修正してください。