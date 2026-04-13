# CHANGELOG

すべての変更は Keep a Changelog 形式に準拠して記載します。

※ 本ログはリポジトリ内のコードから推測して作成したもので、実際のコミット履歴ではありません。

## [0.1.0] - 2026-04-13

### Added
- 初回リリース。KabuSys の基本コンポーネントを実装。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離。
    - duckdb 接続を併用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - 既存の監視テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等）。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。無効な値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（明示的分離）。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.Settings クラスを実装。
    - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。OS 環境変数は保護され、`.env.local` は `.env` を上書き可能。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化。
    - 多数のプロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN/LINE_USER_ID, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値 CPU/MEM/DISK, LOG_LEVEL, env 判定ヘルパー is_live/is_paper/is_dev）。
    - PAPER_FILL_MODE（paper trading の fill 動作）に対する検証（有効値: instant|partial|never|reject）。
    - 環境変数の必須チェックと値検証を実装（不正値は ValueError を送出）。
    - .env パーサーは export 形式やクォート、エスケープ、インラインコメントの取り扱いに対応。
- データベース / DuckDB
  - duckdb 接続を前提とした分析・研究モジュールを追加。
- 研究 / リサーチ
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照して各種ファクター（モメンタム、ATR、流動性、PER/ROE など）を計算。
    - 計算窓や必須行数が不足する場合は None を返す等、安全に動作する設計。
  - research.feature_exploration
    - calc_forward_returns（将来リターン）、calc_ic（Spearman ランクによる IC）、factor_summary（統計サマリ）、rank（ランク付け）を実装。
    - pandas 等の外部依存を持たない純粋 Python 実装。
- ポートフォリオ構築
  - portfolio.portfolio_builder
    - select_candidates（スコア降順・タイブレーク: signal_rank）と重み計算 calc_equal_weights / calc_score_weights（スコア全て 0 の場合は等金額配分にフォールバック）を実装。
  - portfolio.risk_adjustment
    - apply_sector_cap（セクター集中上限チェック。既存保有のセクター比率が上限を超える場合に候補を除外。unknown セクターは除外対象外）を実装。
    - calc_regime_multiplier（market regime に応じた投下資金乗数。bull=1.0, neutral=0.7, bear=0.3。未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes を実装。allocation_method に応じた株数算出（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料／スリッページ見積り）を考慮。
    - スケールダウン後の端数配分（lot 単位）に再現性のあるロジックを実装。
- AI ニュース NLP
  - ai.news_nlp
    - raw_news と news_symbols を集約して OpenAI（デフォルト gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を追加。
    - バッチサイズ、記事/文字数のトリム、最大リトライ（429/ネットワーク/5xx 等）と指数バックオフ、レスポンス検証、スコアのクリップを実装。
    - 書き込みは対象コードを絞って安全に DELETE→INSERT を行う（部分失敗時の既存スコア保護）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
    - ルックアヘッドバイアスを避けるため datetime.today() を参照しない設計（target_date ベース）。
- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成スクリプトを追加。CLI（--from, --to, --db）対応。
    - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計し、閾値（稼働率99%、成功率90%、送信率95%、P95 latency <= 200ms）で PASS/FAIL 判定を出力。
    - DB が存在しない場合やテーブル欠損時に見やすくエラーハンドリング。
- ユーティリティ
  - utils.process_priority
    - プラットフォーム差分を吸収する set_process_priority(level) と set_cpu_affinity(cpu_count) を実装（psutil 利用）。Windows/Linux/macOS 等を想定し、権限不足等では警告を出してスキップする。
- パッケージ情報
  - package version を __version__ = "0.1.0" としてタグ（初版）を設定。
  - __all__ に主要サブパッケージを追加。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- ai.news_nlp は OpenAI API キー（OPENAI_API_KEY）を必要とする。API キーの管理には注意が必要。
- .env 自動ロードはデフォルトで有効だが、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。OS 環境変数は上書きされないよう保護される設計。

### Notes / Important behavior
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用）を参照する設計になっているため、Paper Trading を明確に分離したい場合は運用上の注意が必要。
- Paper Trading 実行は run_execution で KABUSYS_ENV=paper_trading を設定することで data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に完全分離して記録される。
- .env のパーシングは `export KEY=val`、単・二重クォート、エスケープシーケンス、インラインコメントを考慮しており、プロジェクト配布後も CWD に依存しないようプロジェクトルートから .env を探索する。
- DuckDB を用いる研究/分析モジュールは prices_daily / raw_financials / raw_news 等のスキーマを前提としているため、データ整備が必要。

---

今後の予定（例）
- 単体テスト・CI の追加、各モジュールの細かなエラーケースの網羅、AI モジュールの結果保存ロールバック改善、パフォーマンスチューニング（DuckDB クエリ最適化）。