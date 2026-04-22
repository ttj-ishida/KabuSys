# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-04-22

### Added
- プロジェクト初期リリースを追加。
- 起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを実装。プロセス優先度を起動時に "high" に設定し、スレッドでエンジンを実行。停止制御は data/stop_requested.flag と data/execution.pid を利用。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、RiskManager のデフォルト設定値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 など）を追加。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（デフォルト 60 秒）を指定可能。
    - 監視は KABUSYS_ENV にかかわらず production の sqlite_path を使用する仕様。
- 環境設定／検証ツール
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を実装。主要な環境変数（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）に対応。
  - src/kabusys/validate_config.py
    - .env および config/*.yaml の事前検証用 CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML のパースチェック（PyYAML インストール有無に応じて動作）等を行う。--strict オプションで警告を FAIL 扱いにできる。
- 設定管理
  - src/kabusys/config.py
    - .env 自動ロード（プロジェクトルート検出）と堅牢な .env パーサを実装（export 形式・クォート・インラインコメント対応）。
    - Settings クラスを実装し、アプリケーション設定（J-Quants / kabuAPI / LINE / DuckDB / SQLite / Paper Trading / 監視閾値 / ログ設定 等）をプロパティで提供。
    - PAPER_FILL_MODE（instant|partial|never|reject）や KILL_FLAG_CLEAR_ON_START などの環境変数をサポート。
- ログ／プロセスユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 共通ログ初期化ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日分保持）をルートロガーに設定。LOG_DIR 環境変数や引数で保存先を制御可能。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティを実装（set_process_priority, set_cpu_affinity）。アクセス権限不足等は警告を出してフォールバック。
- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates（スコア降順で候補選択）、calc_equal_weights、calc_score_weights（スコア正規化／スコア合計0時のフォールバック）を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中をチェックして候補を除外）と calc_regime_multiplier（market regime に基づく投下資金乗数のマップ: bull=1.0, neutral=0.7, bear=0.3）を実装。unknown セクターの扱い、ログ出力あり。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes を実装。allocation_method ("risk_based" / "equal" / "score") に対応。単元株（lot_size, デフォルト 100）丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap スケーリング、残差処理ロジックを搭載。
  - src/kabusys/portfolio/__init__.py で上記 API をエクスポート。
- リサーチ／ファクター計算（基盤）
  - src/kabusys/research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールの骨組みを追加。DuckDB 接続を受け取り prices_daily/raw_financials を参照して計算する設計。モメンタム用定数（21/63/126/200 等）を定義。
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）からデータを読み、稼働率・注文成功率・送信率・API レイテンシ（平均/最大/P95）・リスク却下数などを集計して PASS/FAIL 判定を出力。デフォルト閾値は稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95レイテンシ <= 200ms。
- パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / 注意事項（アップグレード／運用メモ）
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用して監視テーブルを初期化・記録します。運用時は適切な SQLite パスを設定してください。
- 実取引/ペーパートレードのデータ分離:
  - KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）の DB を使用します。本番 DB と完全に分離して運用できます。
- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env を自動読み込みします。既存 OS 環境変数は優先され、.env.local は .env をオーバーライドします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 起動時プロセス優先度:
  - run_execution/run_monitoring は起動直後に set_process_priority("high") を呼び出します。環境によっては権限不足で設定に失敗する場合があり、その際は警告が出力されます。
- ログ:
  - デフォルトで logs/ 以下に app_name.log（日次ローテーション、30日保持）を作成します。LOG_DIR 環境変数で変更可。ログディレクトリ作成失敗時はコンソール出力のみで継続します。
- CLI ツール:
  - config_setup: 対話式で .env を生成します。生成後は python -m kabusys.validate_config で検証することを推奨します。
  - validate_config: --strict を付けると警告も失敗扱い（exit 1）になります。
- Paper Trading の検証レポート:
  - thresholds は paper_verification_report.py 内の定数で定義されています。必要に応じて変更して利用してください。

### Security
- 現在の実装では .env 内の機密値（トークン/パスワード）をファイルに保存します。.env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも警告あり）。

---

今後の予定（例）
- factor_research の各ファクター実装の完了（Value / Volatility / Liquidity）。
- ExecutionEngine / RiskManager の詳細テストとエラー処理改善。
- テストカバレッジ追加と CI 設定。

以上。