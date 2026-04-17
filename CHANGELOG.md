# Changelog

すべての変更は Keep a Changelog の規約に従って記載します。  
このファイルはコードベースから推測して作成したリリースノートです。

注: 日付はリポジトリ内ソースのタイムラインに合わせて 2026-04-17 を付与しています（推測）。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-17
初回リリース — 基本的な自動売買フレームワークのコア機能を提供します。

### Added
- 実行/監視のエントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。起動時にプロセス優先度を設定し、Broker クライアント、OrderManager、RiskManager、Reconciler を組み立ててエンジンをスレッドで実行する。
    - 停止フラグ (data/stop_requested.flag) を監視して安全に停止可能。
    - エンジンの PID を data/execution.pid に記録する仕組みを想定。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する（設計上の決定）。
    - 停止フラグ (data/stop_requested.flag) 検出でループを終了。

- 設定管理・ウィザード・検証
  - config.py: 環境変数／.env 読み込み・高水準設定アクセスを提供する Settings クラスを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づいて .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パースはクォート・エスケープ・インラインコメントなどを考慮した堅牢な実装。
    - 各種環境変数アクセス（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、PID_FILE_PATH、しきい値など）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - デフォルト値、選択肢、シークレット項目のマスク表示、既存 .env の読み込みと上書き保存。
    - .env のテンプレート出力（Git にコミットしない旨の注意を含む）。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境時の追加ガードを実装。
    - --strict モードで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全0 の場合はフォールバックで等配分）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェックで新規候補を除外する機能（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく発注株数計算。単元（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合はスケーリングして端数処理で補正）を実装。
    - cost_buffer による保守的コスト見積もり（スリッページ・手数料反映）をサポート。

- 監視・検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite DB から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポート出力するスクリプトを追加。
    - デフォルト閾値（稼働率 99%、成功率 90% 等）を定義し、PASS/FAIL 判定を行う。
    - --from / --to / --db オプションに対応。

- Research / ファクター計算
  - research.factor_research: DuckDB を用いたファクター計算（モメンタム、移動平均乖離、ATR、流動性等）の実装。
    - calc_momentum, calc_volatility など。prices_daily テーブルを前提に SQL 複合処理で算出。

- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定と CPU affinity 設定を提供。
    - set_process_priority(level): "high"/"normal"/"low" を受け取り psutil を使って設定。権限がない場合は警告でフォールバック。
    - set_cpu_affinity(cpu_count): 指定コア数に pin する。未対応 OS や権限不足は警告でスキップ。

- DB 接続
  - sqlite3 と duckdb の両方を想定して各処理から接続を受け渡す設計になっている（monitoring 用テーブル初期化用 init_monitoring_db 使用）。

### Changed
- 初回リリースのため特別な後方互換変更項目はなし（新規追加）。

### Fixed
- 実用性・堅牢性に関する実装上の配慮を追加（.env のパース、MONITOR_POLL_INTERVAL の不正値フォールバック、DB 存在チェックと例外ハンドリング、psutil による例外時の警告処理など）。

### Notes / Known issues / TODO
- apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過小評価される可能性があり、将来的には前日終値や取得原価等のフォールバックを導入予定（コード内コメントで明示）。
- 単元株（lot_size）は現状グローバル固定（デフォルト 100）。将来的には銘柄毎の lot_map に拡張予定。
- run_monitoring は説明どおり「監視は環境にかかわらず本番 sqlite_path を使用」する実装になっているため、開発環境で意図せず本番 DB にアクセスしないよう運用上の注意が必要。
- Settings の一部プロパティは未設定時に ValueError を投げるため、運用前に validate_config を必ず実行することを推奨します。
- research モジュールは prices_daily / raw_financials のスキーマに依存。DuckDB 上の該当テーブルが整備されていることが前提。

### Security
- .env ファイルは生成時に「絶対に Git にコミットしないこと」を明示。シークレットは表示時にマスクする配慮を追加。

---

発見した実装の意図・環境変数の一覧（抜粋・参考）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- MONITOR_POLL_INTERVAL (監視ポーリング秒数、デフォルト 60)
- PAPER_FILL_MODE (paper_trading の fill 動作: instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB）
- DUCKDB_PATH, SQLITE_PATH（デフォルト: data/kabusys.duckdb, data/monitoring.db）
- LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- KILL_FLAG_CLEAR_ON_START（本番での自動 Kill Flag クリア抑止推奨）

この CHANGELOG はソースコードからの推測に基づくものであり、実際のリポジトリのコミット履歴やリリースノートとは差異がある可能性があります。必要であれば実際のコミット単位の差分からより正確な履歴を作成します。