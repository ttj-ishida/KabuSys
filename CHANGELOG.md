# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴ではありません。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-24

初回公開リリース。システム全体のコア機能、CLI ツール、ユーティリティ、ポートフォリオ構築ロジック、および検証ツールを提供します。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視（monitoring）は環境に関係なく本番用の SQLite (`Settings.sqlite_path`) を使用する設計。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグファイル（data/stop_requested.flag）を検出してループを終了。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成（paper/live に応じた実装を想定）。
    - PID ファイル管理（data/execution.pid）、停止フラグの検出による安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。
    - `.env` / `.env.local` の読み込み順と OS 環境変数の保護（既存値の上書き制御）。
    - .env のパースは `export KEY=val`、クォート、コメント、エスケープを考慮。
    - Settings クラスを提供し、各種設定（J-Quants, kabu API, DB パス, PID/kill フラグパス, 監視閾値, 環境判定等）をプロパティ経由で取得。入力検証を実施（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の妥当性チェック）。
    - settings というインスタンスをモジュールレベルで公開。

- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを実装。既存 .env の読み込み、シークレットのマスク表示、保存前確認などを提供。
    - デフォルト値や選択肢を用意（KABUSYS_ENV、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）。
    - .env 書き込み時に注記（.env を Git にコミットしないよう注意）を出力。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在確認と（PyYAML がある場合の）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 設定や Kill スイッチ設定の注意喚起）を実装。
    - `--strict` オプションで警告を失敗扱いにできる。

- ログ / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一的設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）を設定。ログディレクトリは引数 / 環境変数 / デフォルト（logs/）の順で解決。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールトトレラントな挙動。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）設定ユーティリティを追加。Windows/Linux/Mac の差分を吸収し psutil を使用して設定。アクセス拒否や未対応 OS の場合は警告を出してスキップする。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と配分重み計算（calc_equal_weights, calc_score_weights）を実装。スコアゼロ時は等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限の実装（apply_sector_cap）。既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を提供（bull:1.0, neutral:0.7, bear:0.3、未知は 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック（calc_position_sizes）を実装。risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）での丸め、1 銘柄上限・全体利用上限、手数料・スリッページを考慮した cost_buffer、available_cash に基づくスケーリングと残余配分ロジックを実装。

- 研究用モジュール（骨格）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity の設計に基づくファクター計算モジュールを追加。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。モメンタム等の定義（窓長など）が含まれる。
    - （calc_momentum 等の関数群を用意。ファイル末尾の実装は継続/拡張を想定）

- 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH を参照し、システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL を判定する。
    - デフォルト閾値: uptime>=99%、fill_rate>=90%、send_rate>=95%、P95 latency<=200ms。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

- DB 関連
  - DuckDB を分析用 DB として採用（Settings.duckdb_path）。
  - 監視用 / ペーパートレード用に SQLite を利用（Settings.sqlite_path / Settings.paper_sqlite_path）。
  - 監視初期化関数 init_monitoring_db の呼び出しを起動スクリプトで行い、監視テーブルが存在することを保証（冪等）。

### Changed
- ロギング動作
  - StreamHandler は stdout を使用（stderr ではない）。cron 等で stdout/stderr を一本化する運用を想定。
  - 既存ハンドラをクリアしてからハンドラを再設定することで二重ログ出力を防止。

### Fixed / Improved
- .env パーサーの堅牢化
  - export 構文のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ解釈、インラインコメント処理の扱いを改善。
- 設定検証の利便性向上
  - PyYAML の有無を検出し、未インストール時は YAML 検証をスキップして警告を出力。
  - validate_config の `--strict` オプションで警告をエラー扱いにできるようにした。
- 実行安全性
  - 起動時に停止フラグを検知した場合の安全な早期終了ロジックを各エントリポイントに実装。
  - 起動時にプロセス優先度を上げることで監視/発注処理の優先度を確保（ただし権限不足時は警告でスキップ）。

### Known issues / Notes
- research/factor_research.py の calc_momentum 等の実装がファイル末尾で途中になっている（注記: 実装継続が必要）。
- position_sizing の価格欠損時の挙動について TODO コメントあり（価格が 0.0 の場合にエクスポージャーが過少見積もられる可能性）。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」とあるため、開発環境で監視データを分離したい場合は設定やコードの調整が必要。
- .env は機密情報を含むため、必ずリポジトリにコミットしないこと（config_setup の出力にも注記）。

### Security
- .env に機密情報（API トークン・パスワード等）を保存する設計のため、config_setup に「.env を絶対に Git にコミットしないこと」と明記。

---

（この CHANGELOG はコードの内容から推測して作成したものであり、実際の変更履歴やコミットログとは差異があります。実際のリリースではコミット履歴に基づいて詳細を補完してください。）