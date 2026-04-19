# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」形式に準拠しています。  

注: 以下の変更内容は提供されたコードベースから推測して作成したリリースノートです。

## [Unreleased]

### Added
- 実行系 / 監視系の起動スクリプトを追加
  - run_execution.py: ExecutionEngine の起動/停止ロジック、paper_trading 環境時に専用 DB を使う処理、BrokerClientFactory によるブローカークライアントの生成、ExecutionEngine のスレッド起動と停止フラグ監視を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知での終了処理を実装。
- 環境設定 / 検証用 CLI を追加
  - config_setup.py: 対話式ウィザードで .env を作成/更新する機能を追加。シークレットのマスクや選択肢サポート、保存前の確認を実装。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、パス検証、YAML の構文チェック、KABUSYS_ENV による本番向けガードなどを実装。
- 設定管理モジュール (kabusys.config) を追加/強化
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込みを実装。自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - .env パーサを強化（export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応）。
  - Settings クラスを追加し、各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL など）をプロパティとして提供。値検証（有効な列挙値チェック）を実装。
  - paper_trading 用の paper_sqlite_path と PAPER_FILL_MODE のサポートを追加（instant/partial/never/reject の検証）。
- ロギング / プロセス制御ユーティリティを追加
  - utils.logging_setup: StreamHandler（stdout） と TimedRotatingFileHandler（日次ローテーション）を根幹ロガーに設定するユーティリティ。LOG_DIR・LOG_LEVEL の解決、既存ハンドラのクリア、ファイルハンドラのフォールバック処理を実装。
  - utils.process_priority: psutil を用いたプロセス優先度設定（Windows / POSIX を吸収）。CPU affinity 設定ユーティリティも追加。
- Paper Trading 検証レポートツールを追加
  - tools/paper_verification_report.py: ペーパートレーディング用 SQLite（デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ等を集計してレポートを生成。P95 計算、期間指定、閾値による PASS/FAIL 判定を実装。コマンドライン引数（--from/--to/--db）対応。
- ポートフォリオ構築関連モジュールを追加
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額／スコア加重の重み計算を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（既存ポジションのセクター別エクスポージャ計算、売却予定銘柄除外、unknown セクター扱いの挙動説明）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株（lot_size）丸め、per-position および aggregate cap、cost_buffer を考慮したスケールダウンロジックを実装。残差配分ロジックで再現性のある追加配分を行う。
- research/factor_research.py（ファクター計算基盤）を導入
  - DuckDB 接続を受けて価格・財務データを参照する前提のモメンタム等のファクター計算関数の骨子を実装（momentum 計算など）。設計方針と定数を明記。

### Changed
- 実行開始時にプロセス優先度を高（"high"）に設定する運用方針を導入（run_execution / run_monitoring が共通で set_process_priority("high") を呼び出す）。
- ロギングの標準出力は stderr ではなく stdout を使用するように明示（cron 等でのリダイレクトを想定）。
- DB 接続ポリシー
  - 監視（monitoring）は KABUSYS_ENV にかかわらず production（settings.sqlite_path）を使用する意図を明記。
  - 実行（execution）は paper_trading 環境のとき paper_sqlite_path を使って本番 DB と完全分離する仕様に変更。
- .env 読み込みの優先順位を明確化（OS 環境変数 > .env.local > .env）。既存 OS 環境変数を protected として .env.local の上書きを防ぐ仕組みを導入。
- validate_config の出力を整理し、--strict オプションで警告を失敗扱い（exit(1)）にできるようにした。
- ポートフォリオ計算での安全弁・フォールバック（価格欠損時のスキップ、スコア合計ゼロ時の等配分、unknown セクターは上限適用外 など）を追加して堅牢性を向上。

### Fixed
- .env パーサの不正な行やコメント処理に関する挙動を改善（export プレフィックスのサポート、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い）。
- logging_setup でログディレクトリ作成失敗時にハンドラが二重登録される問題やファイルハンドラ作成失敗時の例外を抑制してコンソール出力のみで継続するように修正。
- process_priority/set_cpu_affinity のプラットフォーム差分や権限不足時の例外をキャッチして警告に留めるように改善（スクリプトのクラッシュを防止）。

### Docs
- 各モジュールに詳細な docstring を追加。環境変数の説明や設計方針（PortfolioConstruction.md 等への言及）を明記。

---

## [0.1.0] - 2026-04-19

初期リリース。上記 Unreleased に記載した機能の多くが本リリースに含まれます。主なポイント:
- 実行/監視プロセス起動スクリプト（run_execution, run_monitoring）
- 設定読み込み/ウィザード/検証ツール（config, config_setup, validate_config）
- ロギング & プロセス優先度ユーティリティ（utils.logging_setup, utils.process_priority）
- ポートフォリオ構築（portfolio パッケージ）
- Paper Trading 検証レポートツール（tools.paper_verification_report）
- DuckDB と SQLite を用いたデータ連携の下地（settings によるパス管理、duckdb 接続受け渡し）

詳しくは上の Unreleased セクションを参照してください。

---

注意事項 / マイグレーション
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかを使用してください。無効な値は起動時にエラーになります。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかである必要があります。設定ミスは ValueError を発生させます。
- .env の自動読み込みはプロジェクトルートの特定に依存します（.git または pyproject.toml）。テスト等で自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視 DB に settings.sqlite_path を使用します。実運用で監視用 DB を分離したい場合は環境変数 SQLITE_PATH を設定してください。
- run_execution は paper_trading 時に PAPER_TRADING_SQLITE_PATH（settings.paper_sqlite_path）を使用し、本番 DB とデータを分離します。

もし追加で変更点の強調や日付の調整、あるいは別のバージョン分割（例: alpha/beta）を希望される場合は指示してください。