# Keep a Changelog
すべての注目すべき変更を明確に記録します。  
フォーマットは Keep a Changelog に準拠します。

v0.1.0 — 2026-04-12
-------------------

初期リリース。以下の主要機能と実装を含みます。

Added
- 基本アーキテクチャと起動スクリプト
  - run_execution.py：ExecutionEngine の起動エントリポイントを追加。環境に応じて本番/ペーパー口座を切り替え、依存コンポーネント（BrokerClient, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッションを実行する。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する意図を明記。
  - tools/paper_verification_report.py：Paper Trading 用検証レポート生成 CLI を追加。期間指定オプション（--from/--to）や DB パス指定（--db）をサポートし、稼働率・注文成功率・送信率・レイテンシ（P95）等を算出して PASS/FAIL 判定を出力する。

- 設定管理
  - config.py：.env 自動読み込み（プロジェクトルート検出 .git / pyproject.toml に基づく）、.env/.env.local の優先順序と上書きルールを実装。エスケープ付きクォート対応や export KEY=val 形式、インラインコメントルールなどを備えたパーサを実装。
  - Settings クラスで主要設定をプロパティとして公開（KABUSYS_ENV, LOG_LEVEL, SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）。値検証（例：KABUSYS_ENV の許容値、PAPER_FILL_MODE の有効値チェック、LOG_LEVEL 検証）を実装。
  - settings オブジェクトをデフォルトでエクスポート。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio.portfolio_builder：候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合のフォールバック警告あり。
  - portfolio.risk_adjustment：セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップと未知レジームのフォールバック挙動）。
  - portfolio.position_sizing：allocation_method（risk_based / equal / score）に基づいて発注株数を計算。lot_size（単元株）に合わせた丸め、1銘柄上限(max_position_pct)、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積、スケール後の残差処理（端数の優先配分）を実装。

- リサーチ / ファクター計算
  - research.factor_research：DuckDB 接続を受け取り、momentum（1M/3M/6M リターン、MA200 乖離）、volatility（ATR20、相対ATR、20日平均売買代金、出来高比）、value（PER/ROE を raw_financials 結合で算出）を計算する関数を追加。ウィンドウサイズや欠損ハンドリングを考慮。
  - research.feature_exploration：将来リターン calc_forward_returns（可変ホライズン、入力検証あり）、IC（calc_ic：Spearman ρ の実装、最小サンプル数チェック）、rank / factor_summary（count/mean/std/min/max/median）を追加。外部ライブラリに依存せず純粋 Python と DuckDB SQL で実装。

- AI ニューススコアリング
  - ai.news_nlp：raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores に書き込む処理を実装。
    - バッチサイズ制御（20 銘柄）、記事数/文字数上限（記事数最大 10、文字数最大 3000）でトークン肥大化を回避。
    - 429・ネットワーク・5xx 等に対する指数バックオフ（リトライ上限）を実装。
    - レスポンスの厳密 JSON バリデーション、スコアを ±1.0 にクリップ。
    - 書き込みは対象コードのみを置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）して部分失敗時のデータ保護を図る。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。API キーは引数または環境変数 OPENAI_API_KEY を参照。

- ユーティリティ
  - utils.process_priority：プラットフォーム差分を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を提供。Windows / POSIX（Linux, Darwin, FreeBSD）対応、アクセス拒否や未実装例で警告を出して安全にフォールバック。
  - __init__.py にパッケージバージョン __version__ = "0.1.0" を設定。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / 注意事項 / 環境変数一覧（主なもの）
- 自動 .env ロードはプロジェクトルートが見つからない場合はスキップされます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数（デフォルト値記載）:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - SQLITE_PATH: 本番監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: ペーパー取引用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒、デフォルト: 60）
  - OPENAI_API_KEY: ai.news_nlp で使用（任意引数でも渡せる）

Migration / Usage tips
- ペーパー取引（KABUSYS_ENV=paper_trading）時、run_execution は paper_sqlite_path を使用して本番 DB と完全分離します。MockBroker の挙動は PAPER_FILL_MODE で制御します。
- run_monitoring は常に本番 sqlite_path を参照する設計が意図されています（環境に依存せず監視は本番DBを使用）。
- settings.PID / kill flag 関連のパスや挙動は Settings で提供されており、プロセス起動時にプロセス優先度設定が行われます。

Acknowledgements / Limitations
- DuckDB / sqlite をデータ層に利用しています。DuckDB の executemany の制約（空 params など）に注意。
- AI API 呼び出しでは出力フォーマットの厳密検証や部分置換戦略により安全性を確保していますが、API 利用時のレート・コスト・品質には十分注意してください。
- いくつかの TODO（例: price 欠損時のフォールバック価格、銘柄ごとの lot_size マスタ対応）がコード中に記載されています。

This release represents the initial feature set for KabuSys v0.1.0. 今後はテストの追加、エラーハンドリング強化、ドキュメント整備、CI/デプロイ設定などを予定しています。