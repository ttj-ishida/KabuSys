# Changelog

すべての注目すべき変更履歴をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

※ バージョンはパッケージ定義の __version__ に合わせて初期リリース 0.1.0 としています。

## [0.1.0] - 2026-04-24

### Added
- 初期実装: KabuSys 自動売買フレームワークのコア機能を追加。
  - パッケージメタ情報: __version__ = "0.1.0" を設定。
- 起動スクリプト / デーモン類:
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - プロセス優先度を "high" に設定（set_process_priority を使用）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（モック/実ブローカーを抽象化）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き（デフォルト 60秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に依らず production 用 sqlite_path を利用する設計（監視データは本番 DB に集約）。
    - 停止フラグ検知でループ終了。
- 設定関連:
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml を探索）。
    - 読み込み順序：OS 環境変数 > .env.local > .env。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 高機能な .env パーサ実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント取り扱いなど）。
    - Settings クラスで主要な環境変数プロパティを提供（J-Quants / kabu API / DB パス / monitoring 閾値 / 環境判定など）。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を提供。
    - 標準の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス等）をカバー。
    - 既存 .env の読み込みと secret 値のマスク表示、保存確認フローを実装。
  - validate_config.py
    - 起動前に環境変数・config/*.yaml・パス等を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML がある場合）、本番環境向けガードチェックを実装。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群、メモリ内処理）:
  - portfolio/portfolio_builder.py
    - select_candidates（スコア降順、タイブレークは signal_rank）。
    - calc_equal_weights（等金額配分）。
    - calc_score_weights（スコア比率で重み付け、全スコアが 0 の場合は警告して等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap（セクター毎の既存エクスポージャーを計算し上限超過セクターの新規候補を除外。unknown セクターは除外対象外）。
    - calc_regime_multiplier（market レジームに応じた投下資金乗数: bull/neutral/bear のマップ。未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes（allocation_method: risk_based / equal / score をサポート）。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超えた場合のスケールダウンと残差の配分）、cost_buffer による保守的見積りなどを実装。
- ユーティリティ:
  - utils/logging_setup.py
    - ルートロガーの統一設定関数 setup_logging。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler を設定。
    - LOG_DIR 未作成時のフォールバック（ファイルハンドラをスキップしてコンソール出力を継続）を実装。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac 等）を吸収する set_process_priority。
    - CPU affinity を設定する set_cpu_affinity。
    - 権限不足等の失敗は警告ログでスキップ。
- モニタリング / DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの冪等な初期化を実行（run_execution, run_monitoring から呼ばれる）。
  - DuckDB 接続を併用（duckdb_path を Settings から取得）。
- ツール:
  - tools/paper_verification_report.py
    - ペーパートレードの検証レポート生成スクリプト。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を算出。
    - CLI 引数 --from/--to/--db をサポート。閾値判定（稼働率 99%、成立率 90% 等）で PASS/FAIL レポートを出力。
    - DB が存在しない・テーブルがない場合に耐性を持たせた実装（OperationalError を捕捉して N/A を出力）。
- research/factor_research.py
  - ファクター計算モジュールの骨格を追加（モメンタム, MA200, ATR, ボラティリティ等の方針と定数を記述）。モメンタム計算関数の実装開始（実装途中のファイルが含まれる）。

### Changed
- 初期リリースのため該当なし（初回実装）。

### Fixed / Robustness
- 不正な環境変数値に対するフォールバック・警告を多数実装:
  - MONITOR_POLL_INTERVAL が不正な場合、警告してデフォルト（60秒）を使用。
  - PAPER_FILL_MODE の不正値は ValueError を投げて早期検出。
  - logging_setup でログディレクトリ作成に失敗してもコンソールログのみで継続。
  - paper_verification_report ではテーブル欠如時に sqlite3.OperationalError を捕捉してレポート生成を続行。
- .env パーサの堅牢化:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。OS 環境変数を保護する protected オプションを導入。

### Security / Notes
- config_setup により生成される .env ファイルについて「絶対に Git にコミットしないこと」を明記（シークレット管理の注意喚起）。
- validate_config に本番環境（KABUSYS_ENV=live）向けの警告を複数実装（LINE 通知設定や Kill Switch の自動クリア設定など）し、本番起動前の確認を促進。

### Known issues / Work in progress
- research/factor_research.py のモメンタム計算実装が途中で終わっている（ファイル末尾が未完）。今後のリリースで完成予定。
- 一部モジュール（ExecutionEngine / BrokerClientFactory / SystemMonitor 等）は本 changelog 対象のコードベースに呼び出し側の参照のみ存在しており、実装詳細は別ファイルに依存する。結合テストにより振る舞い検証が必要。

---

今後のリリースでは、factor_research の完成、テスト充実、API クライアントのモック化強化、監視/アラートルールの拡張などを予定しています。