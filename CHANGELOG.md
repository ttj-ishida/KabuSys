# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルは初回リリース向けに、コードベースから推測できる機能・改善点・重要な動作を要約したものです。

全般
- バージョン: 0.1.0
- 日付: 2026-04-23

## [0.1.0] - 2026-04-23

### Added
- 実行/監視の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。スレッドでエンジンを起動し、data/execution.pid に PID を書き出す想定の処理、停止フラグ（data/stop_requested.flag）検出による安全停止を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番用 sqlite_path を使用して初期化する。

- 設定管理・初期化のユーティリティ
  - config.py: 環境変数/.env の自動ロード機構を実装。プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込み、OS 環境変数は保護（上書きされない）される。.env のパースは export 形式、クォート、インラインコメント等に対応。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。多くの設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス等）を対話で設定し .env を出力。
  - validate_config.py: 起動前チェック CLI。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境用の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）などを実施。--strict モードで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。ログディレクトリの作成に失敗した場合はファイル出力をスキップして stdout のみで継続する安全設計。
  - utils/process_priority.py: Windows と POSIX の差分を吸収してプロセス優先度を設定するユーティリティを追加。CPU affinity を最初 N コアに固定する set_cpu_affinity() も提供。アクセス権限不足などで失敗しても警告を出してスキップ。

- ポートフォリオ構築関連の純粋関数群
  - portfolio/portfolio_builder.py:
    - select_candidates(): BUY シグナルをスコア降順（同点は signal_rank）でソートして上位 N 件を選択。
    - calc_equal_weights(): 等金額配分（1/N）を計算。
    - calc_score_weights(): スコア加重配分を計算。全銘柄のスコアが 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): セクター集中制限を適用し、既存保有によりセクターが上限を超える場合はそのセクターの新規候補を除外するロジックを提供（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier(): market レジーム（'bull'/'neutral'/'bear'）に対する投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method（"risk_based" / "equal" / "score"）に基づいて発注株数を計算。単元株（lot_size）で丸め、1 銘柄上限、aggregate cap（available_cash）超過時は比例スケーリング＋残差処理で lot 単位の追加配分を行う。cost_buffer による保守的なコスト見積もりにも対応。
  - portfolio/__init__.py で上記 API を公開。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB（デフォルト data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）から指標を集計しレポート出力する CLI を追加。以下の指標を算出・判定:
    - システム稼働率（uptime_pct）
    - 注文成功率（fill_rate）、送信率（send_rate）
    - リスク却下数
    - API レイテンシ（avg / max / P95）
    - デフォルトの合格基準（稼働率 >= 99.0%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）が定義され、PASS/FAIL を出力
  - P95 の計算、日付フィルタ（--from / --to）、DB 存在チェックなどを実装。

- DuckDB を利用したリサーチ基盤の骨組み
  - research/factor_research.py: DuckDB 接続を受けてファクター（Momentum / Value / Volatility / Liquidity）を計算する設計の骨組みを追加。モメンタム計算用の定数（1M/3M/6M、MA200 等）と calc_momentum() のインターフェースを用意（実装は続きが想定される）。

- パッケージメタ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Changed
- DB/環境分離の明確化
  - run_execution.py: KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離して動作するよう明確化。monitoring の初期化は実行・監視ともに init_monitoring_db() を呼び冪等に監視テーブルを保証。
  - run_monitoring.py: 監視は環境に関わらず本番 sqlite_path を使用する旨を明記（監視データは本番 DB に集約）。

- ログ出力の標準化
  - setup_logging(): stdout を StreamHandler に使う（stderr ではなく）、ログレベル・ログディレクトリの解決順を統一。

### Fixed / Improved
- 環境変数・.env パーサの堅牢化
  - export キーワード対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応、インラインコメントの扱いなどを実装し .env のパース耐性を向上。
  - OS 環境変数を protected として .env から上書きされないようにし、デフォルトの自動ロードの無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

- 設定検証の安全性向上
  - validate_config.py: PyYAML が無ければ YAML の検証をスキップして警告を出す。KABUSYS_ENV=live の際は LINE 通知や KILL フラグの自動クリア設定について注意喚起する追加チェックを実装。

- プロセス優先度/CPU 設定の耐障害性
  - set_process_priority / set_cpu_affinity: プラットフォーム間の差分を吸収し、権限不足や未サポート OS の場合は警告を出してスキップ。

- ExecutionEngine / RiskManager 初期設定
  - risk_manager のデフォルトパラメータを明記（max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10、circuit_breaker_window_sec=60、max_drawdown=0.20 など）、初期ポートフォリオ値を broker.get_available_cash() から取得する設計。

- ファイル入出力・ディレクトリ作成時のフォールバック
  - ログディレクトリ作成失敗や SQLite/ DuckDB のクローズ処理を finally で保証するなど、起動/終了時の堅牢性を向上。

### Deprecated
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- なし（コードから明確なセキュリティ修正は推測できませんが、秘密情報（TOKEN/PASSWORD）は .env に対してシークレット表示扱いの UI として扱われる点に注意）。  

---

補足: 本 CHANGELOG は提供されたソースコードの内容から推測して作成したものであり、実際のリリースノートは開発履歴・コミットログに基づいて調整してください。