CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリース。日本株自動売買システム「kabusys」の基本機能群を追加。
- エントリポイント / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使い、MockBrokerClient 経由で完全に本番 DB と分離して動作。
    - 起動時にプロセス優先度を設定(set_process_priority("high"))し、必要な依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッションを実行。
    - RiskManager のデフォルト設定（max_position_pct 等）を組み込み、initial_portfolio_value を broker.get_available_cash() から初期化。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックし、警告ログを出力。
    - 監視用 DB は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計（監視データは本番 DB を想定）。
    - プロセス優先度設定・DB 初期化・DuckDB 接続といった起動処理を実装。
    - 監視ループ内で check_once() の例外を捕捉してログ出力しつつループ継続する耐障害性を確保。
- 設定管理
  - config.Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）を実装。.env と .env.local の読み込み順と上書きルールを実装（OS 環境変数は保護）。
    - 多数の環境変数プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, PID/KILL フラグパス, PAPER_FILL_MODE 等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 入力検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）と未設定時の例外 / デフォルトを実装。
- .env パーサー改良
  - export プレフィックス対応、クォート付き値のバックスラッシュエスケープ処理、インラインコメント処理、無効行スキップ等を実装。
  - .env ファイル読み込み時のエラーは warnings.warn で通知（クラッシュを防止）。
- DB / データアクセス
  - DuckDB 接続を利用するリサーチ/AI モジュールを追加（prices_daily / raw_financials / raw_news 等を想定）。
  - 監視テーブルの初期化を行う init_monitoring_db を利用して起動時に監視テーブル存在を保証（冪等）。
- ポートフォリオ構築（完全にメモリ内の純粋関数群）
  - portfolio.portfolio_builder: 候補選定(select_candidates)、等重み(calc_equal_weights)、スコア重み(calc_score_weights) を実装。スコア全てが 0 の場合のフォールバックを実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap と市場レジームに応じた乗数 calc_regime_multiplier を実装。unknown セクターの扱いやログ出力を考慮。
  - portfolio.position_sizing: 各銘柄の発注株数計算 calc_position_sizes を実装。allocation_method に "risk_based"/"equal"/"score" をサポート、lot_size（単元）対応、per-position/aggregate cap、cost_buffer を用いた保守的見積、スケールダウン時の余剰配分ロジック（端数の lot 単位での配分）を実装。
- リサーチモジュール
  - research.factor_research: calc_momentum, calc_volatility, calc_value を実装。DuckDB を用いた SQL ベースの計算（MA200, ATR20, 各種モメンタム）を提供。
  - research.feature_exploration: 将来リターン calc_forward_returns、IC（Spearman ρ）計算 calc_ic、ランク変換 rank、統計サマリー factor_summary を実装。外部依存なしで計算。
  - research パッケージの __all__ を設定してエクスポートを整理。
- AI / ニュース
  - ai.news_nlp: raw_news を OpenAI (gpt-4o-mini) にバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む実装を追加。
    - ニュース収集ウィンドウの計算(calc_news_window)、バッチ処理（最大 20 銘柄/コール）、記事・文字数トリミング、429/タイムアウト/5xx の指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 更新保護（対象コードのみ置換）等の堅牢なフローを実装。
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成用 CLI を追加。
    - レポート指標: 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, P95 レイテンシ等。
    - P95 計算、日付フィルタ（--from/--to）、DB パス指定オプション（--db / PAPER_TRADING_SQLITE_PATH）を提供。
    - しきい値（デフォルト: 稼働率 99%、成功率 90% 等）を使った PASS/FAIL 判定を実装。
- ユーティリティ
  - utils.process_priority: プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows (psutil.HIGH_PRIORITY_CLASS 等) / POSIX (nice 値) をサポート。
    - set_cpu_affinity(cpu_count) を追加（None を渡すと設定しない）。権限不足や未サポート環境をログでスキップ。
- パッケージメタ情報
  - __version__ = "0.1.0" を設定。

Changed
- 監視挙動
  - run_monitoring が監視用 DB を常に本番 sqlite_path を使うように明記（環境変数にかかわらず）。これは監視データは production DB に記録する想定のため。
- .env ロード順
  - 自動ロード順を OS 環境変数 > .env.local > .env に明確化。.env.local は override=True（OS 環境変数は保護）で読み込まれる。
- 設定の検証強化
  - Settings の各プロパティで不正値検出時に ValueError を投げて明示的に失敗する挙動に変更（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。

Fixed
- 起動時のリソースクリーンアップ
  - run_execution/run_monitoring で finally ブロックにより sqlite3/duckdb 接続を確実に close するように実装。
- 監視ループの耐障害性
  - monitor.check_once() 内の例外を外側で捕捉してログに出し、次ポーリングへ常に復帰するように実装。KeyboardInterrupt を捕捉して正常終了ログ出力。
- DuckDB executemany の空パラメータ問題に配慮（ai.news_nlp の DB 書き込み前に params が空でないことを想定した設計）。

Security
- 環境変数の必須チェックを厳格化
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須キーは Settings 経由で未設定時に ValueError を送出し、起動時の不正な状態を防止。

Deprecated
- （なし）

Removed
- （なし）

Notes / Migration
- 環境変数とデフォルトパス
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト、監視は本番を想定）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値は Settings から取得可能
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと .env の自動読み込みを抑制できる
- MONITOR_POLL_INTERVAL
  - 環境変数で監視ポーリング秒数を上書き可能。1 未満や不正な整数を指定すると 60 秒（デフォルト）にフォールバックして警告を出力します。
- 実運用上の注意点
  - process priority / CPU affinity 設定は権限に依存するため、権限不足時はログワーニングを出してスキップします。
  - portfolio.position_sizing は lot_size を全銘柄共通で扱う設計。将来的な拡張（銘柄別 lot_size）を想定した TODO コメントあり。
  - ai.news_nlp は OPENAI_API_KEY の設定を必須とする（引数で渡すことも可能）。API の失敗に対してはフェイルセーフでスキップする挙動を採用。

Known issues / TODO
- price が欠損（0.0）の場合にセクターエクスポージャーが過少見積りされブロックが外れる問題に関する注記（risk_adjustment.apply_sector_cap 内の TODO）。
- position_sizing の将来的な拡張: 銘柄別 lot_size のサポートを検討中。
- ai.news_nlp の実装は API レスポンスバリデーション・例外処理等を慎重に設計しているが、実運用での細かなエラーケース（OpenAI のレスポンス仕様変化等）に対する追加テストが望ましい。

Acknowledgements
- 初期実装はモジュール設計（監視・実行・リサーチ・ポートフォリオ・AI）を分離しており、テスト・拡張がしやすい構成を目指しています。今後はドキュメント整備と単体テストの追加を予定しています。