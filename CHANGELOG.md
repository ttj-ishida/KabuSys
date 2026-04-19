# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/

現在バージョン: 0.1.0

[0.1.0] - 2026-04-19
-------------------

Added
- 初回公開リリース。KabuSys の基本的な実行基盤・ユーティリティ・ポートフォリオ構築・検証ツール群を追加。
- 起動スクリプト
  - run_execution: 実取引/ペーパートレードの ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）による制御をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用の sqlite_path を使用する挙動を明示。
    - 停止フラグ検知でループを終了し、例外発生時はログを残して次のポーリングへ継続。
- 設定管理・検証
  - config.py: 環境変数・.env の自動読み込みと Settings クラスを追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の読み込みは OS 環境変数を保護する設計（protected keys）。
    - 各種設定（DB パス、PAPER_FILL_MODE、しきい値、PID/kill flag パス、ログレベル、環境種別判定等）をプロパティで提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - config_setup.py: 対話式 .env ウィザードを追加（.env の生成・更新を支援）。
    - 秘匿入力、選択肢、既存値の取り込み、保存の確認機能を実装。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数の有無チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース（PyYAML がある場合）を検査。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順、同点時は signal_rank の昇順でタイブレークして上位 N 候補を返す。
    - calc_equal_weights / calc_score_weights: 等配分、スコア加重配分。スコア合計が 0 の場合は等配分へフォールバック（警告ログ）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック。既存保有を時価で集計し上限超過セクターから候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告を出して 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に従って銘柄ごとの発注株数を算出。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、全体の aggregate cap（available_cash に対するスケーリング）、cost_buffer を考慮した保守的見積りを実装。
    - リスクベース方式では price / stop_loss に基づくポジションサイズ計算を実装。
- ユーティリティ
  - utils.logging_setup: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を追加。
    - ログディレクトリの自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバック実装。
    - 再設定時は既存ハンドラを flush/close して二重追加を防止。
  - utils.process_priority: Windows と POSIX を吸収するプロセス優先度設定および CPU affinity 設定を追加。
    - set_process_priority は権限不足や未実装 API を安全にハンドリングし、失敗時は警告ログを出して継続。
    - set_cpu_affinity は最初の N コアに固定する機能（引数 None で無効）。
- 監視・計測関連
  - run_monitoring と run_execution 内で monitoring_db.init_monitoring_db を呼び出し、監視テーブルの存在を冪等に保証。
  - monitoring 系は SQLite（監視用）と DuckDB（分析用）を併用する設計を採用。
- 検証ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、PASS/FAIL 判定を行う。
    - --from / --to / --db オプションで期間・DB を指定可能。
- 研究用モジュール
  - research.factor_research: DuckDB を利用したファクター計算の骨組みを追加（モメンタム・MA・ATR 等の設計、定数定義まで含む。関数 calc_momentum の実装開始あり）。

Changed
- ログ出力に関する共通方針を確立。
  - stdout をメインのコンソール出力先に選定（cron 等で stdout を集約しやすくするため）。
- .env 読み込みの挙動
  - OS 環境変数を保護するため .env 読み込み時に protected keys を使う。既存 OS 環境を優先して上書きを制御。

Fixed
- 環境変数パーサの堅牢化
  - config._parse_env_line にてクォート内のエスケープ、インラインコメントの扱い、export プレフィックスに対応するなど現実的な .env 書式のパース対応を実装。
- ロギング設定失敗時のフォールバック強化
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合も、StreamHandler によるログ出力は継続するように変更。

Security
- 秘匿値の扱い
  - config_setup の対話表示・保存確認や、表示時にシークレット値をマスク（****）する UX を実装し、誤操作による露出を軽減。

Notes / その他
- 監視 (run_monitoring) は説明コメントの通り「KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」ため、意図的に監視データを本番用監視 DB に集約する設計になっています。テスト目的で分離したい場合は Settings.paper_sqlite_path 等を利用するか、別プロセスで起動スクリプトを変更してください。
- process_priority の適用は権限やプラットフォームに依存します。権限不足で失敗した場合はログに警告が出ますが、起動自体は続行されます。
- research.factor_research やその他一部モジュールに未完の実装（calc_momentum の途中など）が存在するため、研究用途やテストでの利用に際しては注意してください。

未実装 / 将来検討
- position_sizing の lot_size を銘柄毎に管理する拡張（stocks マスタの導入）などの TODO コメントあり。
- price が欠損している場合のフォールバック価格（前日終値や取得原価など）を使う改良が示唆されている。
- research モジュールの完全実装（ファクター計算の SQL 実装等）。

---- 

注: 本 CHANGELOG は提供されたコードベースの内容から機能・挙動を推測して作成しています。実際のリリースノートとして使用する場合は、実際に意図した仕様やリリース日・バージョン表記をプロジェクト方針に合わせて調整してください。