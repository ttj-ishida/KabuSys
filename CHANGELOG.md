# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

（現時点のコードベースではバージョンが 0.1.0 のため、今後の変更はここに追記してください。）

## [0.1.0] - 2026-04-25

### Added
- 基本的なアプリケーション骨格を追加。
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として定義。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite(DB) を使用して実行を分離。
    - デーモン（スレッド）でエンジンを実行し、data/stop_requested.flag による停止制御を実装。
    - 実行中の PID 管理用に data/execution.pid を利用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する（監視 DB を共通化）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理
  - config.py: 環境変数読み込み・Settings クラスを実装。  
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml から探索）。  
    - .env / .env.local の読み込み規則（OS 環境変数を保護する protected 機構、.env.local は上書き）。  
    - .env の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。  
    - 多数の設定プロパティ（DB パス、KABUSYS_ENV 検証、ログレベル、paper_trading の設定など）を提供。
  - config_setup.py: 対話式 .env 作成 / 更新ウィザードを追加。  
    - シークレット値のマスク表示、既存 .env の読み込み、保存時のテンプレート生成をサポート。
- 設定検証 CLI
  - validate_config.py: 起動前に .env および config/*.yaml の不備を検出する CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV 検証、ログレベル・DB パスの警告、YAML の存在・パース検証（PyYAML が無い場合はスキップ）。  
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler を設定。  
    - LOG_DIR 指定・作成の試み、失敗時はファイル出力をスキップしてコンソールログのみで継続。  
    - 既存ハンドラの重複防止のため再設定時にクリアする実装。
- プロセス関連ユーティリティ
  - utils/process_priority.py: Windows / POSIX を吸収する優先度設定と CPU affinity 設定を追加。  
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。  
    - psutil の権限エラー等に対して警告を出して安全にスキップする実装。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア順）と重み計算（等配分 / スコア加重）を実装。  
    - スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター上限適用とレジームに応じた乗数を実装。  
    - セクター上限超過銘柄の除外ロジック、未知セクターは上限適用除外。  
    - レジーム乗数マップ（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio/position_sizing.py: 発注株数算出（risk_based / equal / score）を実装。  
    - 単元株（lot_size）で丸め、ポジション上限・投下上限の考慮、コストバッファ適用、aggregate cap に対するスケーリングと端数配分ロジックを備える。
- 分析・ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率・送信率、リスク却下数、レイテンシ（P95 含む）を算出。  
    - 基準値（稼働率/成功率/送信率/P95）に基づく PASS/FAIL 判定を出力。  
    - PAPER_TRADING_SQLITE_PATH 環境変数 / --db オプションで DB を指定可能。
- 研究用ファクターモジュール（下地）
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨組み（モメンタム、MA、ATR、流動性等）を追加（計算範囲定義・設計方針のコメントあり）。

### Changed
- ログ出力を stdout に統一（ログユーティリティ）: cron / Task Scheduler 等で stdout/stderr をまとめて扱う運用に配慮。
- .env 読み込みの仕様を詳細化: export 形式、クォート付き値のエスケープ処理、コメント扱い（クォート内無視、無クォート時は '#'' 前がスペースならコメント）に対応。
- 実行・監視スクリプトは起動直後にプロセス優先度を high に設定するように変更。

### Fixed
- 環境値パースの堅牢化: MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルトへフォールバックし、ログで警告を出すようにした。
- SQLite / DuckDB の接続を確実にクローズするよう finally ブロックを追加（リソースリーク防止）。

### Notes / Implementation details
- 監視（monitoring）と実行（execution）は DB を共有する場合と paper_trading に分離する場合があるため、Settings により sqlite_path / paper_sqlite_path を切り替え可能。
- validate_config は PyYAML が未インストールでも動作する（YAML 検証をスキップするが警告を出す）。
- position_sizing の aggregate スケーリングでは lot_size 単位での端数処理および残余キャッシュでの追加配分を行い、再現性のため安定ソートを使用している。
- process_priority は各 OS の制約や権限不足を考慮して失敗時は警告ログに留める設計。
- 依存ライブラリ: duckdb, psutil、PyYAML（任意、YAML 検証用）。存在チェックやエラー時のフォールバック実装あり。

### Security
- .env ファイルを絶対にリポジトリにコミットしない旨を config_setup の出力で明記。

---

今後のリリースでは各コンポーネント（ExecutionEngine、SystemMonitor、BrokerClient 等）の詳細な機能追加・安定化、factor_research の完全実装、単体テスト・E2E テストの追加などを予定しています。必要であれば、ファイル単位の変更差分からさらに細かいリリースノート（関数追加・引数変更・既知の制約など）を作成します。