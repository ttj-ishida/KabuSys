# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: ここに記載した項目は、提供されたコードベースの内容から推測してまとめたリリースノートです。実際のコミット履歴ではなく、ソースコードに実装されている機能・振る舞いに基づいています。

## [Unreleased]

（現時点で未リリースの修正や追加があればここに追記してください）

---

## [0.1.0] - 2026-04-18

初期リリース — KabuSys のコア機能を実装しました。日本株自動売買システムの基礎的な実行環境、設定管理、監視、およびポートフォリオ構築ロジックを提供します。

### Added（追加）
- コアパッケージ
  - 基本パッケージ情報を追加（src/kabusys/__init__.py、バージョン 0.1.0）。
- 実行・監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV による paper_trading モード対応（paper_trading 時は専用の Mock ブローカを使用し、paper_trading DB に記録）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御にファイルフラグを採用（data/stop_requested.flag）。実行中は実行エンジンをスレッドで動かし、フラグ検知で安全に停止。
    - PID ファイル出力機能（data/execution.pid）。
    - 依存コンポーネントの組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）。
    - RiskManager のデフォルト設定（max_position_pct 等）を実装し、初期ポートフォリオ価値は broker.get_available_cash() から取得。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔のオーバーライド（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計。
    - 停止フラグの検知（data/stop_requested.flag）でループを終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - Settings クラス（src/kabusys/config.py）を実装し、環境変数から一元的に設定を取得。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索し、.env/.env.local を適切な優先度で読み込む。OS 環境変数は保護（上書き防止）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能。
    - 各種設定プロパティを提供（J-Quants、kabu API、DuckDB/SQLite パス、paper_trading パス、監視しきい値、環境判定ユーティリティ等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV、LOG_LEVEL 等の入力検証。
  - 設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式に .env を初期作成・更新するウィザードを提供。
    - 秘匿項目のマスク表示、選択肢のバリデーション、既存値の読み込みと保存 (.env 書き出し)。
    - デフォルト項目と説明を含むテンプレート出力。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env と config/*.yaml を事前検証するユーティリティを実装。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば実施）など。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict モードで警告を FAIL 扱いにできるオプション。
- ロギング・プロセス制御ユーティリティ
  - logging_setup: 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーション FileHandler（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - LOG_DIR / LOG_LEVEL の解決順を考慮。
    - ログファイル名は app_name に基づく（例: logs/execution.log）。
  - process_priority: クロスプラットフォームのプロセス優先度・CPU affinity 設定（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS に対応し、nice 値や Windows 優先度クラスを適用（権限不足時は警告を出してスキップ）。
    - set_cpu_affinity により最初の N コアにプロセスを固定できる（オプション）。
- ポートフォリオ構築（メモリ内純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋signal_rank タイブレークで切り出す。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバック（警告）。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（unknown セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未定義レジームは 1.0 でフォールバックし警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて銘柄ごとの発注株数を算出。
    - リスクベース算出（risk_pct, stop_loss_pct）や per-position 上限、単元株（lot_size）丸めを実装。
    - 集計上限（available_cash）超過時はスケーリングして、端数は残差（fractional）に応じて lot_size 単位で再配分するアルゴリズムを実装。
    - cost_buffer を使った保守的コスト見積に対応。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - paper_trading SQLite DB を読み、システム稼働率、注文成功率（Fill/Send）、リスク却下数、API レイテンシ（avg/max/P95）を算出してレポート出力。
    - P95 計算の実装（_p95）。
    - デフォルトしきい値定義（稼働率 99%、注文成功率 90% など）に基づく PASS/FAIL 判定。
    - コマンドライン引数で期間指定 (--from, --to) や DB パス指定 (--db) に対応。
- 研究モジュール（factor 計算）
  - research/factor_research.py の基盤を実装（モメンタム等のファクター計算を設計に基づき実施する想定）。
    - 1M/3M/6M リターンや 200 日移動平均乖離率、ATR、出来高指標などの計算方針をドキュメント化（duckdb 接続を受けて prices_daily / raw_financials を参照する設計）。
    - （注）ファイルは途中までの実装が含まれますが、基本設計と定数が定義されています。

### Changed（変更）
- なし（初期リリースのため実装内容の一覧を記載）

### Fixed（修正）
- なし（初期リリース）

### Notes / 運用上の注意
- 環境変数自動ロード:
  - プロジェクトルートが検出できない場合は自動読み込みをスキップします。
  - OS 環境変数は既定で保護され、.env/.env.local による上書きは行われません（ただし .env.local は override=True で読み込み、OS 環境変数以外は上書き）。
  - テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ:
  - ファイル出力に失敗した場合でもコンソール出力（stdout）は動作します。ログディレクトリ作成に失敗した旨が stderr に出力されます。
- 停止制御:
  - run_execution / run_monitoring は共にプロジェクト内の data/stop_requested.flag（パスはスクリプト内定義）を監視して安全に停止します。運用時はこのフラグの扱いに注意してください。
- Paper Trading:
  - paper_trading モードでは paper 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と物理的に分離されるよう設計されています。
- 権限:
  - プロセス優先度や CPU affinity の設定は OS 権限に依存します。権限不足時は警告を出してスキップします。

---

もし特定のファイルや機能についてより詳細な CHANGELOG エントリ（例: 実装当時の設計決定や既知の制限、今後の TODO）を追加したい場合は、対象範囲を指定してください。