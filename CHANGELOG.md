# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。主にコードベース初期実装のまとめを、ソースコードから推測して日本語で記載しています。

フォーマット:
- 破壊的変更は Breaking Changes として明記します。
- 各項目は機能追加 (Added)、変更 (Changed)、修正 (Fixed)、削除 (Removed)、非推奨 (Deprecated)、セキュリティ (Security) に分類しています。

なお、バージョンはパッケージの __version__ (0.1.0) に合わせています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-25

Added
- 初期リリースとして以下の主要機能を実装・追加。
  - 起動スクリプト
    - run_execution: ExecutionEngine を起動するスクリプトを追加。プロセス優先度を設定し、環境に応じて本番/ペーパーの SQLite を切り替え、Engine をスレッドで実行して停止フラグを監視する。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を指定可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - 設定管理
    - config: 環境変数・.env ファイルの自動読み込みロジックを実装。プロジェクトルートの自動検出（.git または pyproject.toml）を行い、.env/.env.local の読み込み順・上書きルール（OS 環境変数保護）を実装。
    - Settings クラスを実装し、J-Quants / kabu API / DB パス /監視閾値 /環境フラグ等のプロパティを提供。KABUSYS_ENV の妥当性検査や PAPER_FILL_MODE のバリデーションを含む。
  - 設定ユーティリティ CLI
    - config_setup: 対話式ウィザードで .env を生成/更新する CLI を実装。秘密項目はマスク表示、デフォルト・選択肢のサポート、保存前の確認を提供。
    - validate_config: .env と config/*.yaml を検証する CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在確認、PyYAML が無ければ YAML 検証をスキップ。--strict オプションで警告を失敗扱いにできる。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio.portfolio_builder: シグナルから候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - portfolio.risk_adjustment: セクター集中制限の apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジーム時のフォールバック動作と警告ログを含む。
    - portfolio.position_sizing: position sizing ロジックを実装（risk_based / equal / score の各方式）、単元株（lot_size）丸め、max_position や aggregate cap、cost_buffer に基づくスケーリングロジックを実装。
    - portfolio パッケージのエクスポートを整備。
  - ツール
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。期間指定（--from / --to）や DB パス指定（--db）を受け、稼働率/注文成功率/送信率/レイテンシ（平均・最大・P95）などの指標を計算して PASS/FAIL を判定する。P95 計算や閾値（稼働率 99%, 成功率 90% 等）を定義。
  - 監視 DB 初期化
    - monitoring.monitoring_db:init_monitoring_db を呼ぶことで監視用テーブルの存在を保証（冪等）。
  - ロギング・プロセス制御ユーティリティ
    - utils.logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。ログディレクトリ自動作成、LOG_LEVEL 解決順、エラーハンドリング（ファイル作成失敗時はコンソール出力のみ）を実装。
    - utils.process_priority: Windows/Linux/macOS に対するプロセス優先度設定と CPU affinity 設定を提供。プラットフォーム差分を吸収し、権限不足や未対応機能は警告でスキップする。

Changed
- 環境分離
  - run_execution が paper_trading 環境時に専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用することで、本番 DB と完全に分離される設計を採用。
- .env パーサーの取り扱い
  - config モジュールの .env パーサーは以下に対応:
    - 行頭の export を許容
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの値におけるインラインコメント（'#'）の取り扱い（前にスペースがある場合のみコメントと扱う）
  - .env.local は .env の上書き（override=True）として扱い、既存 OS 環境変数は protected で上書き不可。
- 起動時のデフォルト挙動
  - run_monitoring は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用する（設計上の注意: 監視は常に本番 DB を見る）。
  - run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（0 以下や不正値はデフォルト 60 秒にフォールバック）。
- ログ出力の規約
  - logging_setup は stdout を標準出力に使う（stderr ではない）ため、外部スケジューラでの出力リダイレクトが容易。

Fixed
- (設計・堅牢性) 起動スクリプトでのリソースクローズを確実化
  - run_monitoring/run_execution で finally ブロックにより sqlite/duckdb コネクションを確実に閉じる実装を追加。
- (堅牢性) run_monitoring 内の monitor.check_once() 周りで例外を捕捉し、ログ出力して次ポーリングに継続するように修正。

Security
- .env の取り扱いに関する注意書きを config_setup のヘッダに追加（.env を絶対に Git にコミットしない旨）。機密情報（トークン・パスワード）はウィザードで「secret」扱いしてマスク表示。

Notes / Implementation details
- Execution / Monitoring の停止はプロジェクトルート/data/stop_requested.flag により行う設計。Execution は起動時に flag が既に立っている場合は起動しない。
- ExecutionEngine 起動時に PID ファイルを data/execution.pid に書く設計を想定（設定からパス取得）。
- RiskManager の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をコード内で定義し、初期ポートフォリオ値は broker.get_available_cash() を参照して設定する。
- portfolio.position_sizing の aggregate cap ロジックは cost_buffer を用いて保守的に概算コストを見積もり、必要な場合は銘柄別にスケーリングと lot 単位での再配分を行う。
- paper_verification_report は DB にテーブルが無い場合に sqlite3.OperationalError を捕捉してデフォルト値でレポートを継続する耐障害設計。

Breaking Changes
- なし（初期リリース）

Removed / Deprecated
- なし（初期リリース）

Security Advisories
- なし

---

この CHANGELOG はソースコードからの推測に基づき作成しています。挙動やデフォルト値、ファイルパス、環境変数名などは実装に依存するため、実運用にあたっては実際の設定ファイルや README、ドキュメントと照合してください。