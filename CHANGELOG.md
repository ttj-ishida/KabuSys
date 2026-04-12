# CHANGELOG

すべての重要な変更点を記録します。本ドキュメントは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-12

初回リリース。システム全体の起動スクリプト、設定管理、ポートフォリオ構築・ポジション計算、リサーチ用ファクター計算、ニュース NLP スコアリング、運用用ユーティリティ、及び検証ツールを追加しました。

### Added
- 起動スクリプト・ランタイム
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動するエントリポイントを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用途の DB は環境にかかわらず本番 sqlite_path を使用する点を明記。
    - 起動時にプロセス優先度を "high" に設定する処理を行う。
  - run_execution.py を追加。ExecutionEngine の起動エントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等の依存コンポーネントを組み立て、ExecutionEngine を実行。
    - 起動時にプロセス優先度を "high" に設定する処理を行う。

- 設定管理
  - config.py を追加。
    - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml）を探索し、.env /.env.local を読み込み。OS 環境変数を保護する overwrite ロジックを備える。
    - .env のパーサーは export 形式、クォート文字列（バックスラッシュエスケープ対応）、インラインコメント処理などに対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - Settings クラスを提供し、J-Quants / kabu / LINE / DB 周りの設定や各種閾値（CPU/MEM/DISK）・PID / kill flag パス・環境（development, paper_trading, live）検証等をプロパティ経由で取得可能。
    - PAPER_FILL_MODE（instant/partial/never/reject）の検証を実装。
    - paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）をサポート。

- 監視・検証ツール
  - tools/paper_verification_report.py を追加。paper_trading の SQLite を解析して稼働率、注文成功率、送信率、レイテンシ（P95 含む）などを計算し、PASS/FAIL 判定付きのレポートを標準出力へ出力。
    - 日付フィルタオプション (--from / --to) と --db オプションを提供。
    - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）をデフォルトで採用。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重配分。スコア合計が 0 の場合は等金額にフォールバックし WARNING を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター露出を評価し、1 セクターの上限を超える場合は新規候補の除外（"unknown" セクターは上限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数算出を実装。lot_size（単元株）丸め、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、残差に基づく追加配分ロジック等を実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を追加。DuckDB の prices_daily / raw_financials を用いてモメンタム、ATR（ボラティリティ）、流動性、PER/ROE 等を計算。窓幅・データ不足時の None ハンドリングを含む。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。有効レコードが 3 未満の場合は None を返す。
    - factor_summary / rank: ファクターの基本統計量計算とランク付けユーティリティを提供。
  - research パッケージの __all__ を整備し、外部公開 API を整理。

- ニュース NLP（AI）
  - ai/news_nlp.py を追加。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、トークン肥大化対策（記事・文字数上限）、エラーハンドリング（429/5xx/ネットワーク断に対する指数バックオフ・リトライ）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の DB 保護（対象コードのみ置換）等を設計方針として採用。
    - calc_news_window ユーティリティによりニュース集計ウィンドウ（JST 基準の前日 15:00 〜 当日 08:30）を UTC 表現で算出。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装。Windows (psutil の優先度定数) と POSIX (nice 値) を吸収し、プラットフォーム非依存の呼び出し API を提供。AccessDenied 等発生時は警告してスキップ。
    - set_cpu_affinity(cpu_count) を追加（最初の N コアに固定）。引数検証と例外ハンドリングを含む。

- パッケージ情報
  - kabusys.__init__.py に __version__ = "0.1.0" を追加。

### Changed
- （該当なし：初回リリースのため既存機能の変更はありません）

### Fixed
- （該当なし）

### Notes / Migration
- 環境変数の挙動:
  - .env 自動ロードはデフォルトで有効。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / DUCKDB_PATH 等で DB のパスを指定できます。paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用するため、本番 DB とデータが混在しません。
  - MONITOR_POLL_INTERVAL は正の整数のみ有効。無効な値はデフォルト（60 秒）にフォールバックします。
  - OPENAI_API_KEY は ai/news_nlp の score_news 呼び出し時に必要です（引数での上書き可能）。未設定時は ValueError が発生します。

- DB スキーマ/テーブル:
  - tools/paper_verification_report や ai/news_nlp、research モジュールはそれぞれ prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等のテーブルを参照します。これらのテーブルが存在しない環境では一部機能は動作しません（tools は存在チェック・例外ハンドリングを含む）。

- 実運用注意:
  - process priority / cpu affinity の設定は権限に依存します。権限不足時は警告ログが出力され、処理は継続されます。

---

本 CHANGELOG は今後のリリースで追記・更新します。リリースに含まれる詳細な API 仕様や DB スキーマ、運用手順は別ドキュメント（設計書・README 等）を参照してください。