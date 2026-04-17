Keep a Changelog
================

すべての変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-17
------------------

Added
- 初回公開リリース: パッケージバージョンを __version__ = "0.1.0" として導入（src/kabusys/__init__.py）。
- 実行用スクリプト:
  - run_execution: ExecutionEngine 起動・管理スクリプトを追加。paper_trading 環境では MockBrokerClient と分離された SQLite DB（デフォルト: data/paper_trading.db）を使用。停止フラグ（data/stop_requested.flag）や実行 PID ファイル（data/execution.pid）に対応し、スレッドでエンジンを起動／停止する挙動を実装（src/kabusys/run_execution.py）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の挙動を明記（src/kabusys/run_monitoring.py）。
- 設定管理:
  - Settings クラスを導入し、各種環境変数アクセスをプロパティ化（src/kabusys/config.py）。DB パス、PID/kill フラグ、監視しきい値、環境（development/paper_trading/live）などを提供。
  - .env 自動読み込み機能を実装（プロジェクトルート自動検出: .git / pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。読み込みは OS 環境変数 > .env.local > .env の優先順（src/kabusys/config.py）。
  - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の新規プロパティを追加。
- ポートフォリオ構築:
  - 銘柄選定や重み計算の純粋関数群を追加（select_candidates, calc_equal_weights, calc_score_weights）（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中チェック（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加（src/kabusys/portfolio/risk_adjustment.py）。
  - 発注株数算出ロジック（calc_position_sizes）を追加。risk_based / equal / score の複数配分方式、単元株丸め、aggregate cap スケーリング、コストバッファをサポート（src/kabusys/portfolio/position_sizing.py）。
  - 上記をパッケージレベルで公開（src/kabusys/portfolio/__init__.py）。
- 監視・実行のユーティリティ:
  - プロセス優先度設定・CPU affinity ユーティリティを追加（set_process_priority, set_cpu_affinity）。Windows/Linux/macOS 系を抽象化し、権限不足時は警告でスキップ（src/kabusys/utils/process_priority.py）。
- 研究（research）モジュール:
  - ファクター計算モジュールを追加（momentum, volatility, value）。DuckDB 接続を受け prices_daily / raw_financials を参照して必要指標を計算（src/kabusys/research/factor_research.py）。
  - 特徴量探索ユーティリティ（forward returns, IC（Spearman ρ）, rank, factor_summary）を追加。外部ライブラリに依存せず実装（src/kabusys/research/feature_exploration.py）。
  - research パッケージで主要関数をエクスポート（src/kabusys/research/__init__.py）。
- AI ニュース NLP:
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメント評価し、銘柄ごとの ai_scores に書き込む処理を追加（バッチ処理、トークン肥大化対策、JSON モード、リトライ、スコアクリップ等）。タイムウィンドウ計算ユーティリティ calc_news_window を実装（src/kabusys/ai/news_nlp.py）。
  - OpenAI API キー未設定時は明確なエラーを返す仕様。
- ツール:
  - paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。期間指定 (--from / --to) や DB 指定 (--db) に対応し、稼働率・注文成功率・送信率・レイテンシ（P95 等）を算出して判定（PASS/FAIL）を出力。デフォルト DB は data/paper_trading.db。閾値はソース内で定義（src/kabusys/tools/paper_verification_report.py）。
- DB 初期化:
  - 監視テーブル初期化ユーティリティ呼び出しを run_execution / run_monitoring で実施（init_monitoring_db を使用）。paper_trading 環境では専用 DB を使う等の分離を導入。

Changed
- プロジェクトの環境変数読み込みロジックを強化:
  - .env のパースは export プレフィックスやクォート・インラインコメント・エスケープに対応し、安全に環境変数をセットするよう改善（src/kabusys/config.py）。
- 実行・監視スクリプトのプロセス優先度設定を起動直後に行うように変更し、安定性を向上（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）。

Fixed
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能にし、不正値（0 以下や非整数）はデフォルトにフォールバックして警告を出すようにした（src/kabusys/run_monitoring.py）。
- calc_score_weights が全スコア 0 の場合に等金額配分へフォールバックする挙動を実装し、警告ログを出力するようにした（src/kabusys/portfolio/portfolio_builder.py）。

Security
- OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数で提供されない限り使用しないようチェックを追加（src/kabusys/ai/news_nlp.py）。

Notes / Known limitations
- run_monitoring は「監視」用途の DB を環境にかかわらず settings.sqlite_path（production 想定）で開く設計。paper_trading の検証データと完全に分離したい場合は run_execution / tools 等で paper 用 DB を利用すること。
- news_nlp.score_news は OpenAI API 呼び出しに依存するため、API 利用制限や料金に注意。429/5xx エラーは指数バックオフでリトライするが、最終的に部分的失敗が発生した場合は既存スコアの保護を意識した DB 更新処理を行う設計。
- position_sizing の lot_size は現状全銘柄共通の単純実装。将来的に銘柄別 lot_map への拡張を想定している旨をコード内に注記。
- research モジュールは DuckDB 上の prices_daily / raw_financials テーブルに依存する。テーブル構造・データが不足する環境では結果が None を含む可能性あり。
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後に CWD と異なる配置で利用する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動ロードすることを推奨。

Developer notes
- ドキュメント参照: ソース中に PortfolioConstruction.md / StrategyModel.md 等への言及あり。実装はこれらの設計ドキュメントに基づく。
- テストや追加ドキュメントは今後のリリースで順次整備予定。

(以降のリリースでは Changed/Fixed/Removed セクションを使って差分を記録してください。)