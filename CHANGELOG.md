# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」準拠で、セマンティック バージョニングを採用します。

※ 本リポジトリの現在のパッケージバージョンは src/kabusys/__init__.py の __version__ に基づきます。

## [0.1.0] - 2026-04-17

Added
- 基本アプリケーション構成を追加
  - kabusys.config.Settings: 環境変数／.env の読み込み・取得用設定オブジェクトを実装。
    - 自動 .env 読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）
    - 読み込み順序: OS 環境 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能）
    - 必須値チェック用の _require ユーティリティ、KABUSYS_ENV / LOG_LEVEL 等の妥当性チェックを実装。
    - データベースパス、paper trading 用 DB パス、PID/kill flag パス、監視閾値などをプロパティで提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 実行 & 監視の起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - プロセス優先度を設定し、SQLite / DuckDB 接続を行う。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用（本番 DB と完全分離）。
    - BrokerClientFactory により適切なブローカークライアント（Mock を含む）を生成。
    - ExecutionEngine を別スレッドで実行し、 data/stop_requested.flag により安全停止を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様（監視 DB は本番 DB に紐づけ）。
    - stop flag（data/stop_requested.flag）検出でループ終了。KeyboardInterrupt をハンドリングして終了処理。
- 設定ユーティリティ CLI を追加
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE... 等）を用意。
    - .env の読み書きロジックを実装（既存値再利用、シークレットマスク表示、保存確認）。
    - .env を生成するテンプレートに「Git にコミットしない」旨の注意を含む。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config YAML の存在／パースチェック（PyYAML 未導入時は警告）を実施。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
- portfolio 関連の純粋関数群を追加（DB 参照なし、メモリ計算）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で上位 N 件選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア合計 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限に基づき候補をフィルタ。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知の値は警告して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算。
    - 単元株丸め（lot_size、デフォルト 100）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap と残差配分ロジックを実装。
    - risk_based 方式では risk_pct / stop_loss_pct を用いたリスクベース算出を行う。
- research モジュールにファクター計算を追加
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: ATR、avg_turnover、volume_ratio 等（途中までの実装ファイル。設計方針と定数を定義）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
- ツール: Paper Trading レポート生成スクリプトを追加
  - tools.paper_verification_report.py
    - ペーパートレード結果を SQLite（デフォルト data/paper_trading.db）から集計してレポート出力。
    - 指標: 稼働率(uptime)、注文成功率(fill_rate)、送信率(send_rate)、レイテンシ（avg/max/P95） 等。
    - 合格基準（例: uptime >= 99.0%、fill_rate >= 90% 等）を定義し PASS/FAIL を出力。
    - --from / --to / --db オプションで期間と DB を指定可能。
- utils/process_priority.py を追加
  - set_process_priority(level): Windows / POSIX の差を吸収してプロセス優先度を設定（psutil 必須）。
  - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン止め（未指定は no-op）。
  - 権限不足や未対応プラットフォームは警告してスキップするよう堅牢化。
- その他
  - パッケージ初期化ファイル src/kabusys/__init__.py にバージョンとエクスポートを追加。
  - モジュールエクスポートを整備（kabusys.portfolio に主要関数をエクスポート）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- .env ファイルを生成する際に「.env は絶対に Git にコミットしないこと」という注意を README 相当のコメントに明示（config_setup にて）。

Notes / 実装上の注意
- run_monitoring はドキュメンテーションに従い監視用の sqlite DB を常に本番 sqlite_path を使う挙動となっています。テスト環境で監視 DB を分離したい場合は sqlite_path を明示的に環境変数で設定してください。
- run_execution は KABUSYS_ENV=paper_trading の際に paper_sqlite_path を使用します。ペーパートレードと本番 DB は分離されています。
- .env のパースは quoted value のエスケープや inline コメントの扱いに配慮した独自実装を導入していますが、特殊ケースは未テストのため注意してください。
- position_sizing の価格欠損時の挙動に TODO（フォールバック価格の導入）が残っています。
- research.factor_research の一部計算（ボラティリティ関連など）は大規模なデータ前提で DuckDB を用いており、実行前に prices_daily 等のテーブルが整備されている必要があります。
- process_priority の動作は psutil に依存し、一般ユーザ権限では優先度設定や CPU affinity が失敗する場合があります（警告が出てスキップされます）。

---

今後の予定（例）
- ExecutionEngine / Monitoring の詳細なユニットテスト追加
- research モジュールの追加ファクター実装とバッチ処理の整備
- 銘柄固有の lot_size 管理、手数料モデルの導入

(この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴運用時はコミットメッセージ・タグと合わせて管理してください。)