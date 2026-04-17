CHANGELOG
=========

すべての変更は "Keep a Changelog" のフォーマットに従って日本語で記載しています。

2026-04-17 — 0.1.0
------------------

Added
- 基本パッケージ初期リリースを追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。
- 実行・監視用スクリプトを追加。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV に関係なく production の sqlite_path を使用する（監視データは本番 DB を参照）。
    - プロセス優先度を起動時に "high" に設定。
    - stop_requested.flag による安全停止対応、例外発生時はログを残して次ポーリングへ継続。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い ExecutionEngine をスレッドで実行。
    - 起動前・実行中に stop_requested.flag を監視して安全に停止。PID ファイル管理あり（data/execution.pid）。
    - RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を実装。
- 設定管理モジュールを追加。
  - src/kabusys/config.py
    - .env/.env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env のパース強化:
      - export KEY=val 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
      - クォートなしでのインラインコメント（#）処理（直前が空白/タブの場合のみコメントと扱う）
    - 環境変数の必須チェック _require()、各種設定値（DuckDB/SQLite パス、PID/kill flag パス、監視しきい値、LOG_LEVEL/ENV バリデーション等）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- ツール: Paper Trading 検証レポート生成スクリプトを追加。
  - src/kabusys/tools/paper_verification_report.py
    - paper_trading DB（デフォルト data/paper_trading.db）を対象に実行可能な CLI ツールを実装。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 等を集計し PASS/FAIL を判定。
    - デフォルト基準値を定義（稼働率 >= 99%、成立率 >=90%、送信率 >=95%、P95 <=200 ms）。
    - 日付フィルタ指定 (--from, --to)、--db オプション対応。DB 無ければエラーメッセージ出力。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし、メモリ計算）。
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates(): スコア降順選抜（同点は signal_rank でタイブレーク）。
    - calc_equal_weights(), calc_score_weights(): 等金額・スコア加重配分。全スコアが 0 の場合は等配分へフォールバック（警告ログ）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中制限ロジック（既存保有のセクター別時価から上限を判定して新規候補を除外）。unknown セクターは上限適用対象外。
    - calc_regime_multiplier(): 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知時は警告を出して 1.0 フォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes(): 株数決定アルゴリズムを実装。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングと端数処理（余剰キャッシュで再配分）を実装。
    - price 欠損時はスキップする旨のログを出力。
- ユーティリティ: プロセス優先度・CPU affinity ユーティリティを追加。
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level): Windows/POSIX の差を吸収して優先度設定（high/normal/low）。未対応 OS ではスキップして警告ログ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能を実装。権限不足や未対応環境では警告を出してスキップ。
- リサーチ／ファクター計算モジュールを追加（DuckDB 接続を受け、prices_daily/raw_financials を参照）。
  - src/kabusys/research/factor_research.py
    - calc_momentum(), calc_volatility(), calc_value(): モメンタム／ボラティリティ／バリュー系ファクターを計算する SQL 実装を提供（MA200, ATR20, turnovers, PER/ROE など）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(): 将来リターン（複数ホライズン）計算。horizons 引数検証あり。
    - calc_ic(), rank(), factor_summary(): IC（Spearman ρ）計算、ランク付け、ファクター統計サマリを実装。外部ライブラリ非依存で実装。
  - src/kabusys/research/__init__.py に上記 API をエクスポート。
- AI ニュース NLP スコアリングモジュールを追加（OpenAI を利用）。
  - src/kabusys/ai/news_nlp.py
    - raw_news を集約して OpenAI (gpt-4o-mini) にバッチリクエストし、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込み。
    - バッチサイズ、文字数上限、記事数上限、スコアクリップ、リトライ（429/ネットワーク/5xx へ指数バックオフ）等の堅牢化を実装。
    - API キー解決ロジック（引数 > 環境変数 OPENAI_API_KEY）。レスポンス検証の仕組みや部分更新（対象コードのみ DELETE→INSERT）で部分失敗の影響を最小化する設計。
    - ニュース時間ウィンドウ（JST 基準）を計算する calc_news_window() を実装。
- パッケージエクスポートを整備。
  - src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py, src/kabusys/tools/__init__.py を追加して主要関数を公開。

Changed
- 監視と実行の DB ポリシーを明確化:
  - 監視(run_monitoring) は常に本番の sqlite_path を使用（KABUSYS_ENV に依存しない）。そのため監視データは環境に依らず一元化される設計。
  - 実行(run_execution) は paper_trading 環境時に専用 SQLite を使用して本番と完全分離。
- .env の読み込みルール:
  - 読み込み優先順を OS 環境 > .env.local > .env とし、既存 OS 環境変数を保護する仕組みを導入（.env.local は override=True だが OS 環境変数は上書きしない）。

Fixed / Improved
- 環境変数パーサーの堅牢性向上:
  - クォート内のエスケープ処理、export プレフィックス対応、インラインコメント処理等により .env ファイルのパース精度を改善。
- position_sizing のスケーリングと端数配分ロジックを改良:
  - aggregate cap 超過時のスケールダウン処理、余剰キャッシュを使った lot_size 単位の再配分を実装して投資配分の再現性と安全性を向上。
- research モジュールの SQL クエリはデータ不足（ウィンドウ不足）を適切にハンドリングして None を返す設計にして安定性を向上。
- process_priority と CPU affinity の実行時エラー（権限不足など）をログに落として安全にフォールバックするよう改善。

Notes / Known limitations
- ai/news_nlp.py はファイル末尾で処理が途中（コード切断）になっている箇所がある（スニペット切断による）。実運用時は完全版の score_news/_fetch_articles 等が必要。
- 一部の TODO（例: position_sizing で銘柄別 lot_size を将来サポートする等）がコード内に残っている。
- 一部の SQL は DuckDB の機能（ウィンドウ関数等）に依存するため、実行前に prices_daily/raw_financials 等のテーブルスキーマ・データ整備が必要。
- run_monitoring/run_execution はプロセス優先度操作や PID/flag ファイルへのアクセスを行うため、権限やファイルパスの存在に依存する。運用環境での config（環境変数、data ディレクトリ等）設定を事前に確認してください。

セマンティクス上の重要な注意点
- MONITOR_POLL_INTERVAL に不正値（0 以下や非数）を指定した場合はデフォルト 60 秒にフォールバックして警告を出力します。
- PAPER_FILL_MODE の不正値は ValueError を送出して明示的に失敗します（無効設定の検出を厳格化）。
- calc_regime_multiplier は未知のレジームで警告を出し multiplier=1.0 でフォールバックします（知見がない場合は中立的扱い）。

今後の予定 (短期)
- ai/news_nlp の完全実装とテスト（_fetch_articles 部分の実装復元）。
- 単体テスト追加（特に portfolio/position_sizing や research の数値ロジック）。
- ドキュメント（PortfolioConstruction.md 等）との整合チェック、API 使用例の追加。

以上。必要なら各機能ごとの詳細な変更差分（関数・引数単位）や利用方法、サンプルコマンドを別途作成します。どの情報が必要か教えてください。