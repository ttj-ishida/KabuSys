# CHANGELOG

すべての変更は「Keep a Changelog」準拠で記載しています。慣例に従いセマンティックバージョニングを想定しています。

## [0.1.0] - 2026-04-19

Added
- 基本アプリケーションを実装（初回リリース）。
- 設定管理
  - Settings クラスを実装し、環境変数から各種設定を提供（J-Quants、kabu API、DB パス、監視パラメータ、システム環境フラグ等）。
  - .env 自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml で検出）。優先順: OS環境 > .env.local > .env。テスト用途に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env 解析は export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントを考慮して安全にパースする実装。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の値検証（無効値は例外を投げるか警告）。
- 設定支援ツール（CLI）
  - config_setup: 対話式ウィザードで .env を作成/更新する CLI を追加。シークレットのマスク表示、デフォルト・選択肢対応、保存確認付き。
  - validate_config: .env と config/*.yaml の検証 CLI を追加。必須環境変数チェック、パス存在/親ディレクトリチェック、YAML パース（PyYAML 未インストール時はスキップ）や本番向けガードチェックを実装。--strict モードで警告も失敗扱いにできる。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db）を使用して本番 DB と分離。ブローカーの生成は BrokerClientFactory 経由。PID ファイル、停止フラグ（data/stop_requested.flag）検出による安全停止をサポート。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する仕様。
- 監視用 DB 初期化
  - init_monitoring_db を利用して監視テーブルの存在を保証（冪等に実行）。
- ロギングユーティリティ
  - setup_logging を実装。stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を持つファイルハンドラ（logs/<app_name>.log）をルートロガーに設定。ログディレクトリの作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。既存ハンドラの二重登録を防止するため再設定時にクリア。
- プロセス制御ユーティリティ
  - set_process_priority(level) を実装し、Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度を設定。失敗時は警告を出してスキップ。
  - set_cpu_affinity(cpu_count) を実装（None で未設定、1 以上で先頭 N コアにピンニング）。権限不足・未対応環境では警告を出してスキップ。
- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder: 候補選定 select_candidates、等分配 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等分配にフォールバックし WARNING）。
  - portfolio.risk_adjustment: セクターキャップ適用 apply_sector_cap（"unknown" セクターは上限チェック対象外）、市場レジームに応じた乗数 calc_regime_multiplier（未知レジームは警告して 1.0 フォールバック）。
  - portfolio.position_sizing: calc_position_sizes を実装。allocation_method により "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケーリングおよび残余配分ロジック）、コストバッファ考慮等を実装。
  - package エクスポートを実装し、主要関数を外部公開。
- 研究・ファクター計算
  - research.factor_research: Momentum 等のファクター計算の枠組みを実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。（注: ファイル末尾は部分的に未完の実装を含む）
- ペーパートレード検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計してレポートを出力。閾値に基づく PASS/FAIL 判定と指標のフォーマットを提供。日付範囲フィルタと --db オプションをサポート。

Changed
- ログ出力は標準エラーではなく標準出力（stdout）に統一して出力（cron /スケジューラとの扱いを考慮）。
- .env の読み込み挙動を安全に: OS 環境変数を保護し、.env.local は OS 環境を上書きしないが .env より優先して上書き可能。

Fixed / Robustness
- MONITOR_POLL_INTERVAL の不正値（0 以下・非整数）に対してデフォルト（60 秒）にフォールバックし、警告を出す実装で time.sleep の ValueError を防止。
- PAPER_FILL_MODE の無効値は ValueError で明示的に検出。
- logging_setup: ログディレクトリ作成失敗時に明示的な警告を出し、ファイルハンドラ作成に失敗した場合はコンソールのみで継続。
- process_priority / set_cpu_affinity: 権限不足や未対応 OS でも例外で落ちないよう適切に捕捉して警告を出す。
- validate_config: PyYAML 未インストール時の YAML 検証スキップと、その旨の警告表示を追加。

Notes / Implementation details
- 実行停止はプロジェクト内 data/stop_requested.flag（停止フラグ）や PID ファイルによって制御。run_execution/run_monitoring は停止フラグ検出で安全に終了する。
- ExecutionEngine は paper_trading 環境で paper トレード専用 DB を利用することで本番データと完全分離する設計。
- ポートフォリオ・ポジションサイズ計算では lot_size（単元）単位の丸め、コストバッファを用いた保守的なコスト見積、スケールダウン時の残余配分ロジックなど、実務的な制約を考慮して実装している。
- research.factor_research は DuckDB を想定し、外部 API には依存しない設計。ただし一部実装が継続中（ファイル末尾が途切れた形で残っているため、追加実装が必要）。

---

初回リリースに含まれる機能や CLI、ユーティリティ、純粋関数群は上記の通りです。追加の機能要望や既存ロジックの変更（例: lot_size の銘柄別対応、価格フォールバックロジック、factor_research の完了など）があれば CHANGELOG に次バージョンとして追記します。