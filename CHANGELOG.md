Keep a Changelog — 遵守項目: https://keepachangelog.com/ja/1.0.0/

注: 以下の CHANGELOG は提示されたコードベースの内容から実装意図・挙動を推測して作成しています。

Unreleased
- ドキュメント化やマイナー修正（開発中の変更点をここに記載します）

[0.1.0] - 2026-04-19
Added
- 基本パッケージ初期実装を追加
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。
- 環境設定・読み込み周り
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env パーサ実装（クォート対応、export プレフィックス対応、インラインコメントルール対応）。
  - 環境変数の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを追加（環境変数経由の各種設定取得とバリデーション）。
    - J-Quants / kabuAPI / LINE / DB パス（DuckDB, SQLite）/ pid/kill flag/閾値や実行環境判定（development/paper_trading/live）などを提供。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の値チェック(許容値以外は例外)。
- 設定支援ツール（CLI）
  - config_setup: 対話式ウィザードで .env を生成・更新する CLI（項目の説明、シークレットマスク、確認・保存機能）。
  - validate_config: .env と config/*.yaml の存在/妥当性を検証する CLI。--strict オプションで警告を失敗扱いにできる。
    - 必須環境変数チェック、DBパスの親ディレクトリチェック、YAML パースチェック（PyYAML が無ければ警告）。
    - KABUSYS_ENV=live に関する追加ガード（LINE 通知設定や Kill Flag の自動クリア設定警告）。
- 実行・監視起動スクリプト
  - run_execution: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）へ分離して動作。
    - BrokerClientFactory 経由でブローカークライアントを生成。OrderRepository, OrderManager, RiskManager, Reconciler などを組み立ててエンジンを起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理、スレッド管理を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は本番用 sqlite_path を常に使用（環境に依存しない監視 DB を意図）。
    - stop フラグ検知でループ終了、KeyboardInterrupt ハンドリング、接続クローズ処理を実装。
- データベース & 分析基盤
  - DuckDB 接続サポート（分析用 duckdb を各種コンポーネントで利用）。
  - 監視テーブル初期化用の init_monitoring_db 呼び出し（冪等に監視テーブルの存在を保証）。
- ロギング・プロセス制御ユーティリティ
  - logging_setup.setup_logging を実装
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）でのファイル出力を統合。
    - LOG_LEVEL / LOG_DIR からの解決、ログディレクトリ作成失敗時のフォールバックと警告。
  - process_priority ユーティリティを実装
    - set_process_priority(level) で Windows / POSIX を吸収して優先度(nice/HIGH_PRIORITY_CLASS 等)を設定。失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count) による CPU ピニングを提供（利用不可時は警告）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア配分(calc_score_weights) を追加。
    - スコアが全て 0 の場合は等金額にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（既存保有からセクター比率を計算し、上限超過セクターの新規候補を除外）。unknown セクターは除外対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマップ）を提供。未知レジームは警告と 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。単元株（lot_size）で丸め、per-position と aggregate のキャップ処理、available_cash によるスケールダウン、cost_buffer を考慮した保守的見積りと繰り上げ配分ロジックを実装。
- 解析・研究モジュール（下地）
  - research.factor_research: DuckDB を使ったファクター計算モジュールを追加（モメンタム/MA/ATR/VOLUME 等を想定）。関数シグネチャと定数を実装（calc_momentum 等の実装が続く設計）。
- 運用ツール
  - tools.paper_verification_report: ペーパートレード結果を検証するレポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定（閾値はソース内定義）。
    - --from/--to/--db オプションをサポート。P95 算出ユーティリティを実装。

Changed
- N/A（初期リリースのため大きな変更履歴はなし）

Fixed
- .env 読み込みの I/O エラー時に警告を出すことで堅牢化（読み込み失敗でも起動を継続）。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップして stdout ログのみで動作するようにフォールバック。

Security
- 機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE トークン等）は .env に格納する運用を想定し、config_setup でシークレット入力をマスク表示。

Notes
- run_monitoring は監視用 DB として常に Settings.sqlite_path を使用するため、監視データは環境にかかわらず単一の監視 DB に記録されます。一方で run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離します。
- process_priority / CPU affinity の適用は OS ごとに差異があり、権限不足や未実装の API に対しては警告を出して処理をスキップします（ベストエフォート実装）。
- research.factor_research は設計の骨格・定数と calc_momentum 等のインターフェースを含むが、完全実装はソースの続きに依存します。

--- 
この CHANGELOG はコード構成・コメント・ログメッセージから推測して作成しています。実際の変更履歴やリリースノートに合わせて適宜編集してください。