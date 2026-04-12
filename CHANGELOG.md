CHANGELOG
=========

すべての注目すべき変更はここで記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。セマンティックバージョニングを使用します。

[Unreleased]
------------

- （現在なし）

0.1.0 - 2026-04-12
------------------

Added
- パッケージ初期実装を追加。
  - kabusys パッケージのバージョンを __version__ = "0.1.0" として公開。
- 実行用エントリポイントを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB(data/paper_trading.db) を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
    - duckdb を計算用 DB として接続。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定。
- 環境設定管理を実装。
  - src/kabusys/config.py
    - .env/.env.local の自動ロード（OS 環境変数より優先されない挙動）。プロジェクトルートは .git または pyproject.toml で探索。
    - export 構文やクォート／エスケープ、インラインコメントを考慮した独自の .env パーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - Settings クラスを導入し、各種設定（DB パス、API トークン、紙取引設定、監視閾値、PID/KILL ファイルパス、環境種別等）をプロパティ経由で提供。値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実施し、不正値は ValueError を送出。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ内処理）。
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights)。全スコアが 0 の場合は等配分にフォールバックして警告を出力。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）。既存保有を考慮して過集中セクターの候補を除外。unknown セクターは適用対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear を定義、未知値はフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing 実装（risk_based / equal / score の割付方法）。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap、available_cash によるスケールダウン、cost_buffer を使った保守的見積り、端数配分ロジックを実装。
- リサーチ／ファクター計算モジュールを追加（DuckDB を入力として使用）。
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ（ATR 等）、バリュー（PER/ROE）ファクター計算関数を実装。prices_daily / raw_financials を参照。
    - データ不足時は None を返すなどの堅牢性を確保。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ファクター統計サマリー(factor_summary)、ランク付けユーティリティ(rank) を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - src/kabusys/research/__init__.py に主要 API をエクスポート。
- ニュース NLP スコアリング（OpenAI）を追加。
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約し、OpenAI API (gpt-4o-mini) に対して銘柄ごとのセンチメント（-1.0〜1.0）をバッチ送信して ai_scores に書き込むロジックを実装。
    - タイムウィンドウの計算、トークン肥大化対策（記事数 / 文字数制限）、バッチ処理（最大 20 銘柄/バッチ）、JSON Mode 期待、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアのクリップ、部分失敗時の安全な DB 更新（特定コードのみ置換）などを設計方針に含む。
- ユーティリティを追加。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分を吸収するプロセス優先度設定セット。nice 値や Windows の PRIORITY_CLASS を使い分ける。アクセス権限が無い場合は警告をログに出してスキップ。
    - CPU affinity 設定ユーティリティも提供（set_cpu_affinity）。
- モニタリング DB 初期化ユーティリティを使用。
  - run_monitoring/run_execution から監視用 DB テーブル初期化（init_monitoring_db）を呼ぶ設計により冪等にテーブルを保証。
- 運用・検証ツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを実装。コマンドライン引数 --from/--to/--db をサポート。
    - システム稼働率、注文成功率（fill_rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計し、閾値（稼働率 >= 99% 等）と照合して PASS/FAIL 判定を出力。
    - レポートは空データやテーブル未存在時に耐性を持ち、適宜 N/A を表示。
- パッケージエクスポート整理。
  - portfolio / research / utils / tools の __init__ に主要 API をエクスポート。

Changed
- DuckDB を分析・ファクター計算用 DB として標準採用（各種モジュールで接続を受け取る設計）。
- 環境変数読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護され、自動上書きされない。

Fixed
- .env パーサでのクォート／エスケープ処理、インラインコメント認識の強化により多様な .env フォーマットに対応。
- position sizing の aggregate cap と端数処理におけるスケールダウンロジックを実装し、残余キャッシュを用いた lot 単位での再配分に対応。
- ファクター／リサーチ関数群でデータ不足時に None を返すなどの安全な扱いを実装（NULL の伝播制御、行数不足チェック等）。
- Paper Verification レポートで P95 を計算するユーティリティを追加し、空リストへの対応を明確化。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得する設計。未設定時は明示的にエラーを返す（キー未設定のまま API を呼ばない）。

Notes / Implementation details
- 多くの関数・モジュールは "純粋関数"（副作用の少ない実装）を心がけ、単体テストや解析が容易な設計を採用している（DB 参照が必要な箇所は接続を引数で受け取る）。
- Paper Trading モードでは本番 DB と完全に分離された SQLite を使用することでテスト／検証時の安全性を確保している。
- ニュース NLP の結果は部分的な失敗が発生した場合でも既存のスコアを不必要に上書きしないよう DB 更新戦略に配慮している（対象コードを限定して置換）。

Author
- KabuSys 開発チーム（コードベースから推測して作成）

（注）この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートや履歴と差異がある場合があります。