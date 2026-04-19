# Changelog

すべての変更は Keep a Changelog に準拠して記載しています。  
表現はコードベース（src/ 以下）の内容から推測・要約したものです。

全般:
- 初期リリース（バージョン 0.1.0）として、実運用を想定した自動売買システムのコアユーティリティ、実行・監視エントリポイント、設定管理、ポートフォリオ構築ロジック、ペーパートレード検証ツールなどを提供します。
- 環境変数による設定と .env ファイルの自動読み込み/ウィザード/検証ツールを備え、ローカル開発・ペーパートレード・本番（live）を想定した設計になっています。

Unreleased
- （なし）

[0.1.0] - 2026-04-19
Added
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - プロセス優先度を高に設定し、スレッドでエンジンを実行。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 SQLite（data/paper_trading.db 既定）を使用して本番 DB から分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動/停止制御。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視では環境に依らず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了。例外はログに残して次サイクルへフォールバック。

- 設定管理
  - config.py: 強化された Settings クラスを追加。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env/.env.local の読み込み優先度（OS環境 > .env.local > .env）、.env.local は既存 OS 環境を保護する仕組みあり。
    - .env のパースは quote とエスケープ、インラインコメント等を考慮した堅牢な実装。
    - Paper Trading 用の設定（paper_sqlite_path, paper_fill_mode 等）を追加。
    - 各種閾値（cpu/memory/disk）や kill/ pid 関連パス等のプロパティを提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - シークレット項目はマスク表示。
    - 既存 .env 読み込み、デフォルト表示、保存前の確認などを実装。
    - .env を作成する際のテンプレート出力を実装（Git 管理しないよう注意喚起）。

- 設定検証 CLI
  - validate_config.py: .env と config/*.yaml の事前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DBパスの親ディレクトリ存在チェックを実装。
    - config/*.yaml の存在と（PyYAML がある場合）パース検証を実施。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout 出力の StreamHandler と 日次ローテート（TimedRotatingFileHandler）を設定。
    - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > デフォルト。
  - utils/process_priority.py: プロセス優先度設定（Windows / POSIX を吸収）と CPU affinity 設定を追加。
    - アクセス権や未対応 OS に対しては安全にフォールバックし、警告を出力してスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選抜（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限の適用。既存ポジションのセクター比率を算出して新規候補を除外。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数を返す（未定義レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算を実装。
    - 単元株（lot_size）で丸め、max_position_pct・max_utilization・cost_buffer（手数料/スリッページ見積り）を考慮した aggregate cap スケーリングを実装。
    - risk_based の場合は risk_pct と stop_loss_pct からベース株数を算出。

- 研究/ファクター計算（部分実装開始）
  - research/factor_research.py: DuckDB を用いたファクター（Momentum/Value/Volatility/Liquidity）計算モジュールの骨格を追加。prices_daily / raw_financials を参照する方針と定数が定義されている（実装は続きあり）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を読み、システム稼働率・注文成立率・送信率・API レイテンシ（P95 等）を集計してレポートを印字するスクリプトを追加。
    - デフォルト DB パス: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）。
    - PASS/FAIL 判定基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms など）を実装。
    - 日付フィルタ（--from / --to）対応。

Changed
- （初期リリースのため「変更」はなし。将来のリリースで差分を記載予定）

Fixed
- （初期リリースのため「修正」はなし）

Removed
- （初期リリースのため「削除」はなし）

Security
- config_setup.py のヘッダーに .env を Git にコミットしない旨を明記（セキュリティ注意）。
- Settings._require() は必須環境変数未設定時に ValueError を投げ、起動前に明示的に検出できるように設計。

Notes / Known limitations / TODO
- research/factor_research.py はファクター計算の骨格が含まれているが、一部実装が続く（ソース末尾で途切れが確認される）。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合のフォールバック価格は現状未実装（TODO コメントあり）。
  - lot_size は全銘柄共通の想定。将来的には銘柄別単元サイズの対応予定。
- apply_sector_cap:
  - sector_map に存在しない銘柄は "unknown" 扱いでセクター上限の評価対象外になる点に注意。
- run_monitoring は Monitoring 用 DB に環境を問わず本番 sqlite_path を使用する設計。ペーパートレード用の分離が必要な場合は別途運用ルールを検討してください。

Migration / Upgrade notes
- 環境構築手順:
  1. .env を作成（config_setup.py によるウィザード推奨）
  2. python -m kabusys.validate_config で設定検証
  3. run_monitoring, run_execution はそれぞれ setup_logging を呼び出すため、LOG_DIR / LOG_LEVEL の設定に注意
- .env 読み込みの挙動:
  - OS 環境変数が最優先。続いて .env、最後に .env.local（.env.local は override=True だが OS 環境は保護される）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト時に有用）。

開発者・運用者向けヒント
- ログ: デフォルトで logs/<app_name>.log に日次ローテーションで出力（30日保持）。ログディレクトリ作成に失敗した場合はコンソール出力のみになるので、権限・パスを確認してください。
- プロセス優先度設定は権限に依存する（Linux の nice を下げる等）。権限不足時は警告が出て処理をスキップします。
- ペーパートレード検証レポートは運用判定（PASS/FAIL）を行うため、定期的に実行して検証することを推奨します。

---

（この CHANGELOG はソースコードのコメント・実装から推測して作成しています。実際のリリースノートとして使用する際は、追加の設計意図や変更履歴を手動で補完してください。）