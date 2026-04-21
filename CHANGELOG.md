CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
バージョン / セクションは重要度に応じて「Added」「Changed」「Fixed」に分類しています。

Unreleased
----------
（現在のリポジトリ状態。今後のリリースに含める予定の変更点）

Added
- 実行スクリプトとユーティリティを多数追加・整理
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて paper_trading 用 DB を分離して使用する（KABUSYS_ENV=paper_trading 時は専用 SQLite を使用）。BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行・停止制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポートし、停止フラグファイルでループを終了可能。
  - config_setup.py: .env の初期作成・対話的編集ウィザードを追加。複数の設定項目を対話形式で入力し .env を生成・更新できる。
  - validate_config.py: 起動前に .env と config/*.yaml を検査する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し PASS/FAIL を判定する。
  - portfolio モジュール（純粋関数群）を追加:
    - portfolio_builder.py: シグナル選定（select_candidates）と重み付け（calc_equal_weights / calc_score_weights）。
    - risk_adjustment.py: セクター上限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
    - position_sizing.py: 発注株数決定ロジック（calc_position_sizes）。等分配 / スコア加重 / リスクベース配分、単元株丸め、aggregate cap によるスケールダウンを実装。
  - utils パッケージにユーティリティを追加:
    - logging_setup.py: 全アプリケーションで共通利用するログ設定ユーティリティ。コンソール（stdout）と日次ローテートファイルハンドラを設定。
    - process_priority.py: Windows/Linux/Mac を跨いだプロセス優先度設定および CPU affinity 設定ユーティリティ（psutil ベース）。未対応 OS や権限不足時も安全にフォールバック。

Changed
- 設定の自動読み込みの改善（config.py）
  - プロジェクトルートの検出を .git / pyproject.toml により行い、CWD に依存しないよう改善。
  - .env および .env.local の読み込み優先度を明確化（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加。
  - .env のパースロジックを強化し、export プレフィックスやシングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスで多数の設定プロパティを提供（DB パス、paper_trading 用パス、監視閾値、PID/kill フラグパス、PAPER_FILL_MODE のバリデーション等）。
- ログ設定の堅牢化（logging_setup.py）
  - ログディレクトリ作成に失敗した場合でもコンソール出力は継続するようフォールバック。
  - stdout を StreamHandler に使用（cron 等のリダイレクトを想定）。
  - 既存ハンドラをクリアして重複設定を防止。
- run_monitoring の挙動
  - Monitoring は KABUSYS_ENV に依らず常に本番用 sqlite_path を使用して監視テーブルを初期化する（init_monitoring_db を呼び出し、冪等に対応）。
- run_execution の挙動
  - Paper trading モード時は settings.paper_sqlite_path を使用して本番 DB と完全分離。
  - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をコード内で定義。
- paper_verification_report のレポート指標と閾値を整備
  - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、閾値に基づく PASS/FAIL 判定を出力する。
  - 日付フィルタの扱い（ISO8601 UTC 変換）と DB 存在チェックを追加。
- portfolio のアルゴリズム改善
  - calc_score_weights: 全銘柄のスコアがゼロの場合に等配分にフォールバックし WARNING を出す。
  - apply_sector_cap: 現保有のセクター別時価を計算して上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
  - calc_position_sizes: リスクベース / 等分配 / スコア重みの各方式、手数料・スリッページ見積もり（cost_buffer）を考慮した aggregate cap スケーリング、単元株（lot_size）丸め等を実装。

Fixed
- 環境変数や CLI の堅牢性向上
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）の際は警告を出してデフォルトにフォールバックするよう修正（run_monitoring.py）。
  - .env パースで無効行・コメント・クォート内エスケープが正しく扱われない問題を改善（config._parse_env_line）。
  - logging_setup がログディレクトリ作成に失敗した際に未ハンドリングで落ちる可能性を防止。
  - process_priority.set_process_priority が未対応 OS や権限不足で例外にならないよう例外をキャッチして警告でフォールバック。
  - ExecutionEngine の起動前に停止フラグが立っている場合は起動せず終了する安全策を実装（run_execution.py）。

0.1.0 - 2026-04-21
------------------
Initial release — 基本機能の実装と CLI ツール群を含む初期リリース。

Added
- プロジェクト初期版として以下を実装:
  - 基本設定管理（config.py, Settings / settings オブジェクト）
  - .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - 実行系スクリプト（run_execution.py）
  - 監視系スクリプト（run_monitoring.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity ユーティリティ（utils/process_priority.py）
  - Portfolio 構築関連関数（portfolio パッケージ: portfolio_builder, risk_adjustment, position_sizing）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - research/factor_research（ファクター計算モジュールの下地。モジュール開始点を定義）

Changed
- パッケージエントリポイントにバージョンを追加（kabusys.__version__ == "0.1.0"）。
- 各種ユーティリティ／CLI のログ出力・動作を安定化。

Notes / Known issues
- research/factor_research.py はファクター計算ロジックの主要部分が続く設計で、ファイル末尾が未掲載（実装継続の余地あり）。
- position_sizing 等の金融ロジックはデフォルトのパラメータ値に依存するため、本番導入前に戦略設計と閾値の妥当性確認を推奨。
- .env は機密情報を含むため、リポジトリにコミットしないよう README 等で注意喚起すること。

ライセンスやリリース手順、さらなる改良点（CI テスト、ユニットテスト、型注釈の厳密化、DuckDB のスキーマ生成スクリプト等）は今後のリリースで扱う予定です。