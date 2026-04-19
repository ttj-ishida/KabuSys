Keep a Changelog 準拠の CHANGELOG.md（日本語）
========================================

すべての変更は semver に従って記載します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [Unreleased]

---

## [0.1.0] - 2026-04-19

最初の公開リリース。本リポジトリの主要機能群と CLI ツールの初期実装を含みます。

### Added
- 基本パッケージ初期実装
  - kabusys パッケージ本体とバージョン情報 (src/kabusys/__init__.py: __version__ = "0.1.0")。
- 実行 / 監視用起動スクリプト
  - run_execution.py：ExecutionEngine 起動スクリプト。  
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATHで上書き可）。
    - 停止フラグ (data/stop_requested.flag) による安全停止、実行中の PID 管理（data/execution.pid）に対応。
    - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立てと ExecutionEngine の起動ロジックを含む。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプト。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは本番 DB を想定）。
    - 停止フラグ検知でループを終了し、例外時はログ出力して次ポーリングに継続。
- 設定管理
  - config.py：.env 自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）と Settings クラス。  
    - .env/.env.local のロード順、OS 環境変数保護（上書き禁止）対応。
    - 必須環境変数取得ヘルパー _require()、各種既定値および検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証など）。
    - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）および監視閾値等をプロパティで提供。
- 設定ユーティリティ / CLI
  - config_setup.py：対話式 .env 作成/更新ウィザード（既存値の読み込み、秘密値のマスク表示、保存確認）。
  - validate_config.py：起動前設定検証ツール（必須環境変数、KABUSYS_ENV 値、YAML ファイルの存在とパース確認、--strict モードで警告を FAIL 扱いにできる）。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py：ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）を設定。ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py：プラットフォーム依存差を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。Windows / POSIX に対応し、権限不足などは警告でスキップ。
- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py：候補選定（select_candidates）、等配分/スコア加重重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py：セクター集中規制適用（apply_sector_cap）、マーケットレジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py：株数算出ロジック（risk_based / equal / score）、単元丸め、aggregate cap によるスケールダウン、コストバッファ対応。
  - portfolio/__init__.py：上記関数群をエクスポート。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py：Paper Trading DB を参照して稼働率・注文成功率・送信率・レイテンシ等を集計し、Pass/Fail 判定を行う CLI。日付フィルタ、--db オプション、閾値の定義を提供。
- 研究用ファクター計算（骨組み）
  - research/factor_research.py：DuckDB を用いたファクター計算モジュールの骨格（モメンタム・移動平均・ATR などの設計方針と定数）。（calc_momentum 等の実装が含まれるが、一部ファイル末尾で未完の可能性あり）

### Changed
- 起動時のプロセス優先度を高（"high"）に設定する呼び出しを各起動スクリプトの最初に配置（run_execution, run_monitoring）。これにより安定した実行優先度を確保。
- ログ出力はデフォルトで stdout を使用するように明示（cron 等で stdout/stderr をリダイレクトしやすくするため）。
- .env 読み込み時、OS 環境変数は保護され .env.local は override=True で適用される（ただし OS 変数は上書きされない）。

### Fixed / Improvements
- .env パーサーの強化（config._parse_env_line）
  - export プレフィックス対応、クォートされた値のバックスラッシュエスケープ処理、インラインコメント処理、無効行スキップなどを実装。
- ログ設定: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてもプロセスが継続するよう堅牢化。
- position_sizing の集約スケーリング処理において残差を lot_size 単位で分配するロジックを実装し、再現性確保のため残差ソートの安定化を行った。
- paper_verification_report の統計/パーセンタイル計算（P95）および日付フィルタ付与を実装。

### Notes / Known issues / TODO
- monitoring は「環境にかかわらず本番 sqlite_path を使用する」設計のため、監視データは環境分離されません。必要な場合は設定での分離を検討してください。
- position_sizing:
  - price が欠損（0.0）の場合にエクスポージャーや最大株数が過少見積りされる可能性があり、将来的に前日終値や取得原価などのフォールバック価格の導入を検討中（TODO コメントあり）。
  - 将来的に銘柄ごとの lot_size をサポートする設計拡張を想定（現状は全銘柄共通 lot_size）。
- research/factor_research.py の calc_momentum 等がファイル末尾で途切れている（実装が未完/ファイル切れの可能性）。研究用モジュールは今後拡張予定。
- process_priority の設定は権限（特に POSIX の nice の低い値や Windows の特権）により失敗することがあり、その場合は警告を出してスキップする挙動。
- validate_config:
  - PyYAML 未導入時は config/*.yaml の内容検証をスキップし警告を出す。
  - KABUSYS_ENV=live の場合は追加の警告（LINE 設定や KILL_FLAG_CLEAR_ON_START の危険性）を出す。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非数）はデフォルト 60 秒にフォールバックする（time.sleep に渡すと例外となるため保護している）。
- run_execution/run_monitoring の停止フラグ（data/stop_requested.flag）や Kill Switch の運用に注意。KILL_FLAG_CLEAR_ON_START による自動クリアは本番環境では避けることを推奨（validate_config で警告）。

### Security
- .env ファイルは Git にコミットしないことを README / コメントで明記（config_setup.py の出力ヘッダに注意喚起を追加）。

---

将来的なリリースでは以下を検討しています:
- research モジュールの完全実装（全ファクターの生産実装とテスト）
- 個別銘柄単位の lot_size 対応、価格フォールバックの導入
- 監視データの環境分離オプション（monitoring 用 DB の環境別切替）
- より詳細なテストカバレッジと CI ワークフローの整備

（以上）