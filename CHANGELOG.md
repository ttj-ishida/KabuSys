CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" と Semantic Versioning。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-04-12
-------------------

Added
- 初期リリース: KabuSys v0.1.0 を公開。
- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。ブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、セッションを実行する。
  - Paper Trading モード（KABUSYS_ENV=paper_trading）をサポート。paper_trading 用の専用 SQLite DB (data/paper_trading.db デフォルト) を使用し、本番 DB と完全分離して動作可能。
  - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec など）を実装。初期ポートフォリオ値はブローカーの get_available_cash() を参照して設定。
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用して状態を記録。
  - 監視 DB 初期化（init_monitoring_db）を呼び出して監視テーブルの存在を保証。
- 設定・環境変数管理
  - config.py: .env 自動ロード機能実装（.env → .env.local、OS 環境変数優先）。プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を導入し、配布後のパス問題を回避。
  - .env パースの強化: export 形式対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理などに対応。
  - Settings クラスを実装し、各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH など）をプロパティ経由で提供。値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を追加。
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定（select_candidates）と等金額/スコア加重の重み付け（calc_equal_weights, calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知セクターは "unknown" 扱いで上限適用を無効化。
  - portfolio.position_sizing: position sizing ロジック（calc_position_sizes）を実装。allocation_method（risk_based / equal / score）に対応し、lot_size（単元）で丸め、cost_buffer を考慮した aggregate cap のスケールダウンアルゴリズムを備える。
- 研究（Research）
  - research.factor_research: モメンタム・ボラティリティ・バリューのファクター計算（calc_momentum, calc_volatility, calc_value）を DuckDB SQL による高速実装で提供。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）およびファクター統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。外部依存を持たない純 Python 実装。
- AI / ニュースNLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。バッチサイズ、トークン肥大化対策、リトライ（指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）を備える。ニュース集計ウィンドウ算出ユーティリティ（calc_news_window）を提供。
- ユーティリティ
  - utils.process_priority: cross-platform なプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装（psutil ベース）。Windows/POSIX の違いを吸収し、権限不足や未対応 OS の場合は警告を出してスキップする。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を実装。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計し PASS/FAIL を判定する。期間フィルタ（--from / --to）や DB パスオーバーライド（--db）に対応。
- パッケージ
  - __init__.py にバージョン（0.1.0）とエクスポート定義を追加。

Changed
- 初期リリース相当の実装により、システム設計上の以下の方針を採用:
  - DuckDB を分析用途（prices_daily / raw_financials 等）に使用し、SQLite は監視および paper_trading のログ保存に利用。
  - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - 実行スクリプト起動時にプロセス優先度を最初に High に設定することをデフォルトの挙動とした（set_process_priority 呼び出し）。
- 設定検証を厳格化（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の値チェック）し、無効な値は早期に ValueError を発生させる。

Fixed
- 環境値・設定周りの堅牢性向上:
  - MONITOR_POLL_INTERVAL が 0 以下または非整数のときはデフォルト（60 秒）にフォールバックして例外発生を防止。
  - .env パースの不正行処理・クォート処理・コメント扱いを改善して誤った環境読み込みを防止。
- 実行時の堅牢性:
  - run_monitoring のループ内で monitor.check_once() が例外を投げてもループを継続（例外はログ出力して次回ポーリングへフォールバック）。
  - tools.paper_verification_report は対象テーブルが存在しない/DB が古い場合に sqlite3.OperationalError をキャッチして N/A や 0 を返すようにし、クラッシュを防止。

Documentation
- 各モジュールに詳細な docstring と実装ノート（設計方針、引数仕様、返り値、注意点）を追加。CLI 用の利用例や環境変数説明を各スクリプトに記載。

Security
- OpenAI API キー等の機密値は Settings / 環境変数経由で管理することを想定。API キー未設定時はエラーを投げて明示的に要求。

Notes / Known limitations
- position_sizing の価格フォールバック（前日終値や取得原価）や銘柄ごとの lot_size マスタ対応は将来的な拡張予定（TODO コメントあり）。
- ai.news_nlp の OpenAI 呼び出しはネットワーク/API 制約に依存するため、部分失敗時は成功分のみコミットするフェイルセーフ設計。完全な分散トランザクションは未実装。
- DuckDB executemany に関する互換性（パラメータ非空チェック）に注意。

---

（以降のリリースはここに追記してください）