CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（現在未リリースの変更はここに記載してください）

0.1.0 - 2026-04-23
-----------------

Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基盤機能を追加。
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 起動スクリプト
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、高優先度での起動、PID ファイル管理、停止フラグ（data/execution.pid / data/stop_requested.flag）による安全停止処理を実装。
    - 環境変数 KABUSYS_ENV が paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db を想定）を使用する仕様を導入し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動する組み立て処理を提供。
  - run_monitoring.py:
    - SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に依らず本番用 sqlite_path を使用する挙動を明示。
    - 停止フラグ（data/stop_requested.flag）検出で安全にループを終了。
- 設定管理 / ユーティリティ
  - config.py:
    - 環境変数読み込み・管理機能を追加。プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサーは export 構文、クォート文字列、エスケープ、インラインコメント処理に対応。
    - Settings クラスで各種環境変数をプロパティとして取得。値検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を実装。
  - config_setup.py:
    - .env 作成・更新の対話式ウィザードを追加。テンプレート項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH 等）を対話で入力し .env を生成。
  - validate_config.py:
    - 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ確認、config/*.yaml の存在/パース（PyYAML がインストールされている場合）を実施。
    - --strict オプションで警告を FAIL として扱う。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーを統一的に設定するユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler, 30 日保持）を設定。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py:
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定関数 set_process_priority(level) を追加。psutil を利用しアクセス権限エラー等は警告でスキップ。
    - CPU affinity 設定用の set_cpu_affinity(cpu_count) を追加。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順かつタイブレーク条件で選別する関数を追加。
    - calc_equal_weights / calc_score_weights: 等重配分・スコア加重配分の重み計算を追加（スコアが全て 0 の場合は等重にフォールバックして警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を考慮して新規候補を除外するフィルタを追加。sell_codes（当日売却予定）をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す関数を追加。未知のレジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。
      - risk_based: 許容リスク率（risk_pct）と stop_loss_pct から株数を算出。
      - equal/score: 配分重みから株数を算出。
      - 単元株（lot_size）への丸め、1 銘柄上限（max_position_pct）、利用可能現金（available_cash）に対する aggregate cap とそのスケーリングロジック（端数処理で lot 単位を再配分）を実装。
      - price が欠損/0 の場合はスキップしてログ出力。
- Paper Trading 用検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレーディング用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数を集計してレポートを出力するスクリプトを追加。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を行う。
    - コマンドライン引数 --from / --to / --db に対応。
- 研究・ファクター計算基盤
  - research/factor_research.py:
    - DuckDB 接続を受けてモメンタム等のファクターを計算するインターフェースを追加（モメンタム計算の設計・一部実装）。prices_daily / raw_financials を参照する設計を採用。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / migration
- 自動 .env 読み込み:
  - デフォルトでプロジェクトルートの .env と .env.local を自動ロードします。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。
  - OS 側の環境変数は保護され、.env.local の override でも上書きされません（保護キーとして扱われます）。
- ログ:
  - デフォルトのログ出力先は stdout と logs/<app_name>.log（LOG_DIR で変更可能）。ログディレクトリ作成に失敗した場合はファイル出力を行わず stdout のみになります。
- 実行 / 監視:
  - 監視（run_monitoring）は KABUSYS_ENV に関係なく監視用の sqlite_path（Settings.sqlite_path, デフォルト data/monitoring.db）を使用します。
  - 実行（run_execution）は paper_trading 環境で専用の paper_sqlite_path（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- PAPER_FILL_MODE:
  - PAPER_FILL_MODE 環境変数は "instant" / "partial" / "never" / "reject" のいずれかである必要があります。不正な値は起動時に ValueError を投げます。

Acknowledgments
- 初期リリースでは外部依存（psutil, duckdb, PyYAML 等）を想定しています。環境によっては該当パッケージがない場合に一部機能（CPU affinity 設定、DuckDB クエリ、YAML パース）が無効化または警告になります。