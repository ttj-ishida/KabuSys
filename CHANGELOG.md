CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-13
-------------------

Added
- プロジェクト初期リリース（パッケージバージョン 0.1.0）。
- 基盤機能を多数実装:
  - 実行系
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続してセッションを実行。
    - paper_trading 環境向けに本番 DB と完全分離された PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を導入。KABUSYS_ENV=paper_trading 時は専用 DB を使用する。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動する流れを実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。初期ポートフォリオ値は broker.get_available_cash() を使用。
  - 監視
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を上書き可能。0以下や不正な値はデフォルトへフォールバックして警告を出力。
    - 監視処理は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを管理。
    - 起動時にプロセス優先度を "high" に設定。
  - 設定管理
    - kabusys.config: .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml 基準で検出）。読み込み順は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサーは export プレフィックス、引用符囲み、インラインコメント等に対応する堅牢な実装。
    - Settings クラスに豊富なプロパティを提供（J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定 等）。環境変数バリデーション・デフォルト値を明示。
    - PAPER_FILL_MODE（instant/partial/never/reject）等の列挙値検証を追加。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: シグナル選定（select_candidates）・等配分（calc_equal_weights）・スコア加重（calc_score_weights）を実装。スコア全0時は等配分にフォールバックして WARNING を出力。
    - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。"unknown" セクターは制限対象外として扱う。レジームに応じた multiplier のデフォルトマップを提供（bull/neutral/bear）。
    - portfolio.position_sizing: position size 計算ロジックを実装（risk_based / equal / score）。単元株（lot_size）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap のスケーリングを実装。スケーリング時の端数配分ロジックも導入。
  - 研究モジュール（DuckDB ベース）
    - research.factor_research: momentum, volatility, value ファクター計算を実装（prices_daily, raw_financials を参照）。MA200, ATR20 等の定義を含む。
    - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、基本統計（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
    - research パッケージは data.stats の zscore_normalize と組み合わせて使用可能。
  - AI ニューススコアリング
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）に送り、銘柄ごとのセンチメントスコアを ai_scores テーブルに書き込む機能を追加。バッチ処理（最大 20 銘柄/回）、トークン肥大対策（記事数・文字数制限）、レスポンス検証、スコアの ±1.0 クリップ、リトライ（429/5xx/タイムアウト）などを実装。
    - calc_news_window により JST 時間帯（前日 15:00 ～ 当日 08:30）を UTC に変換して正確に抽出。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し PASS/FAIL 判定（閾値はソース内に定義）を出力。--from/--to/--db オプション対応。
  - ユーティリティ
    - utils.process_priority: プラットフォーム差異を吸収する set_process_priority を追加（Windows / POSIX 対応）。set_cpu_affinity によりプロセスの CPU affinity を設定可能。アクセス拒否や未対応環境では警告ログを出してフォールバック。

Changed
- duckdb および sqlite3 を主要なデータ処理基盤として採用（research / ai / monitoring / execution で利用）。
- 監視・実行の起動時にプロセス優先度を自動で上げることでリアルタイム性を強化。

Fixed
- .env パースにおける引用符やエスケープ、コメントの扱いを強化し、誤った読み込みを防止。
- MONITOR_POLL_INTERVAL に不正な値（0・負数・文字列等）が設定された場合に time.sleep で ValueError にならないようデフォルトへフォールバックして警告を出す処理を追加。
- position_sizing のスケールダウンロジックで端数配分により再現性を確保するため安定ソート（code を二次キー）を導入。
- apply_sector_cap: 当日売却予定銘柄（sell_codes）をエクスポージャー計算から除外するオプションを追加。
- ai.news_nlp: API キー未設定時に明確なエラーを返すよう変更。

Security
- 環境変数の自動読み込みで OS 環境変数を誤って上書きしないよう保護リスト（protected）を導入。

Notes / Implementation details
- 多くの計算関数は外部副作用を持たない純粋関数として実装されており、ユニットテストが容易な設計。
- DuckDB に対するクエリは可能な限りウィンドウ関数 / 1 クエリで完結するよう最適化（パフォーマンス配慮）。
- run_monitoring は監視 DB テーブルの初期化（init_monitoring_db）を必ず行い、冪等性を確保。
- Paper Trading と本番の完全分離を重視（DB ファイル・ブローカークライアント等）。

Acknowledgments
- 初期設計は PortfolioConstruction.md、StrategyModel.md 等のドキュメントに基づいて実装されています（ソース内コメント参照）。

今後の予定（例）
- 銘柄別 lot_size の導入、stocks マスタに基づく個別単元対応。
- AI スコアリングのバージョン別ロジックやキャッシュ／バッチ効率化の改善。
- 監視のアラート送信（LINE など）実装。