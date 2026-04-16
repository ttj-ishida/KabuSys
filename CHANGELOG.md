# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般:
- 互換性: セマンティックバージョニングを採用しています。
- 日付はリリース日（YYYY-MM-DD）を使用します。

## [Unreleased]

## [0.1.0] - 2026-04-16

### 追加 (Added)
- 初回公開リリース。
- パッケージメタ情報
  - kabusys.__version__ を "0.1.0" に設定。

- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite(DB) を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine をデーモンスレッドで実行。
    - data/stop_requested.flag を監視し停止処理を行う。PID 書き込み先を data/execution.pid に設定。
    - プロセス優先度を最初に High に設定する処理を導入。
    - DuckDB 接続を利用（分析/集計用）。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を実装。
    - data/stop_requested.flag による停止検知、init_monitoring_db による監視テーブル初期化、DuckDB 連携を実装。
    - 例外発生時もログを出して次のポーリングへ継続するフェイルセーフ挙動。

- 設定 (config)
  - Settings クラスを追加し、環境変数/`.env`/`.env.local` から設定を読み込む仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を親ディレクトリから探索して決定（CWD 非依存）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - .env のロード優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 各種プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須取得ユーティリティ。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のデフォルトパス。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_ENV, LOG_LEVEL の検証（有効値チェック）。
    - 監視関連閾値 (cpu/memory/disk) や pid/kill フラグのパスをプロパティ化。

- ツール (tools)
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - コマンドラインから期間指定（--from/--to）および DB パス指定（--db）対応。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計してレポート出力。
    - 判定基準（稼働率/成功率/送信率/P95 レイテンシ）を定義し PASS/FAIL 判定を行う。
    - P95 計算や日付フィルタの生成、DB 存在チェック、テーブル欠如時の安全ハンドリングを実装。

- ポートフォリオ構築 (portfolio)
  - portfolio_builder.py:
    - select_candidates: スコア降順・同点時 signal_rank 昇順のタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights を実装。スコア合計がゼロの場合は等配分へフォールバックして警告を出力。
  - risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、セクター上限を超える場合に当該セクターの新規候補を除外。
      - sell_codes（当日売却予定）を除外してエクスポージャー計算可能。
      - "unknown" セクターは上限適用外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは 1.0 でフォールバックし警告を出力。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた株数算出を実装。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング（残差処理を含む）。
      - cost_buffer を用いた保守的コスト見積もり。
      - 価格欠損時のスキップやログ出力を実装。

- リサーチ (research)
  - research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB 上の prices_daily / raw_financials を参照して各種ファクターを計算。
    - 長期移動平均や ATR、ボラティリティ・流動性指標を SQL ウィンドウ関数で算出。
    - データ不足時は None を返す設計。
  - research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を実装。十分なデータがない場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージは zscore_normalize を data.stats からエクスポート。

- AI / ニュース NLP (ai)
  - ai/news_nlp.py:
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント評価して ai_scores テーブルに書き込む処理を実装。
    - ニュース収集ウィンドウを target_date に基づいて JST→UTC で正確に算出する calc_news_window を導入。
    - バッチ処理（最大 20 銘柄/回）、記事・文字数上限、レスポンス JSON バリデーション、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライなどの頑健化を実装。
    - API キーが未設定の場合は明示的にエラーを返す（score_news）。

- ユーティリティ (utils)
  - utils/process_priority.py:
    - set_process_priority(level) を実装し、Windows と POSIX (Linux/Mac/FreeBSD) を吸収して優先度を設定。
    - set_cpu_affinity(cpu_count) を追加。1 未満の値で ValueError を投げる検証、権限不足時に警告を出してスキップする安全処理を実装。
    - OS 非対応時は警告を出してスキップ。

### 変更 (Changed)
- .env の自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。プロジェクトルートが見つからない場合は自動ロードをスキップする安全仕様。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の値が不正（0以下や非整数）な場合にデフォルトにフォールバックするバリデーションを実装（run_monitoring）。
- レポートツールでの P95 計算が空リストの場合に None を返すように修正（tools/paper_verification_report）。
- calc_score_weights で合計スコアが 0 の場合に等配分へフォールバックしログ出力するようにして、ゼロ除算を防止。

### セキュリティ (Security)
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で指定する必要がある旨を明記。未設定時は ValueError を送出して安全に失敗。

---

備考:
- 多くのモジュールは DuckDB / SQLite の schema（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等）を前提としています。実行前に該当テーブル/スキーマを準備してください。
- ドキュメント内（関数 docstring）に参考資料（PortfolioConstruction.md, StrategyModel.md 等）への言及があります。詳細な設計/パラメータは該当ドキュメントを参照してください。