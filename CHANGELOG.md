CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
（コード内容から推測して記述しています）

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- 実行エントリポイントを追加
  - run_monitoring.py: SystemMonitor のポーリングループを開始するランチャースクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視プロセスはプロセス優先度を「high」に設定し、停止フラグ（data/stop_requested.flag）で安全に終了する。
  - run_execution.py: ExecutionEngine を起動するランチャースクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用して paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録し、本番 DB と分離する。停止フラグ検知時にエンジンを停止する仕組みを実装。

- 設定・環境変数管理
  - config.py: .env 自動読み込み機能（.env/.env.local をプロジェクトルートから読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）を追加。プロジェクトルートは .git または pyproject.toml を基準に検出する。多くの設定プロパティ（J-Quants、kabu API、DB パス、紙トレードモード、監視閾値、環境種別判定など）を提供。
    - PAPER_FILL_MODE: paper_trading の fill モード（instant/partial/never/reject）サポートと検証。
    - paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を分離して paper_trading DB を明示的に扱う。
    - is_live/is_paper/is_dev 等のユーティリティプロパティを追加。

- 設定ツール・検証ツール
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。必須項目・任意項目を整理し、保存前に確認を行う。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config YAML の存在とパース検証、KABUSYS_ENV=live の追加ガード等を実装。--strict を指定すると警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決ロジック、既存ハンドラのクリア、安全にファイルハンドラを作るフォールバック処理を実装。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足等は警告でスキップする。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額/スコア加重の重み計算。スコア合計が 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中の上限（max_sector_pct）チェック。既存保有のセクター比率が閾値を超えているセクターからの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") をサポート。単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的見積り、スケーリング時の残差補正ロジック（remaining cash を用いて lot 単位で再配分）を実装。価格未取得時のスキップやログ出力もあり。将来的に銘柄別 lot_size 拡張の TODO を注記。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を使って SQLite から以下を集計・判定:
    - システム稼働率（system_status）: uptime_pct、エラー数、総ポーリング数
    - 注文指標（trade_logs）: Created/Filled/Sent カウント → 成立率（fill_rate）、送信率（send_rate）
    - リスク却下数（risk_logs）
    - レイテンシ指標（avg / max / P95）
    - P95 計算実装と各種しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定とテキストレポート出力。期間指定（--from/--to）と --db オプションをサポート。

- データベースサポート
  - DuckDB と SQLite の両方を接続して利用する設計を導入（duckdb.connect / sqlite3.connect）。monitoring 用のテーブルが存在することを保証する init_monitoring_db 呼び出しを導入。

- パッケージメタ
  - __init__.py にて __version__="0.1.0" を設定。

Changed
- .env 読み込みの挙動/パーサを強化（config.py）
  - export KEY=val 形式のサポート、クォート文字列のエスケープ処理、インラインコメントの扱い、quoted / unquoted のコメント判定等を細かく実装。
  - _load_env_file による protected（OS 環境変数保護）や override オプションを実装（.env.local を .env 上書きできる）。

Fixed
- 長時間稼働プロセスの安定化を考慮
  - run_monitoring と run_execution の各起動スクリプトでプロセス優先度を最初に設定するようにして、低負荷環境での安定性を向上。
  - run_monitoring のポーリング間隔で不正な環境変数の値を検出したときにデフォルトへフォールバックする処理を実装し、time.sleep に渡す不正値による例外発生を防止。

Security
- 機密値の扱いに配慮
  - config_setup.py / .env 書き込みテンプレートでシークレット項目は明示的に取り扱い、.env を Git にコミットしない旨をコメントで強調。

Notes / Misc
- エラーハンドリングとログ出力に配慮
  - DB 作成/ファイルハンドラ作成失敗時は警告を出してコンソールログのみで継続するフェールソフト設計。
  - process_priority や cpu_affinity 設定で権限不足や未サポート環境では警告でスキップする。
- research/factor_research.py はファクター計算モジュール（モメンタム・ATR・流動性等）を設計・一部実装（DuckDB 接続を前提、関数シグネチャあり）。ファイル末尾が途中で切れている（実装継続の余地あり）。

Breaking Changes
- なし（初期リリース）

Acknowledgements / TODO
- position_sizing の lot_size を銘柄別に持たせる拡張、価格欠損時のフォールバック（前日終値や取得原価）の実装、factor_research の完全実装、その他 config/*.yaml の生成支援スクリプトなどはいくつか TODO コメントあり。