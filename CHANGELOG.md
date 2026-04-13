# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般:
- 日付は UTC ではなくリポジトリ作成時のリリース日を使用しています。
- バージョニングは semver に準拠します。

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージ初期実装を追加。
  - パッケージ情報 (kabusys.__version__ = 0.1.0) を追加。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - BrokerClientFactory により環境 (本番 / paper_trading) に応じたブローカークライアントを生成。
    - paper_trading 環境時は専用 SQLite (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用し、本番 DB と完全分離。
    - 依存コンポーネント (OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine) の組み立てと engine.run_session() を実行。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

- 設定管理
  - config.py
    - .env / .env.local の自動読み込み実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - 読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
    - .env パースの堅牢化（コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い）。
    - 環境変数取得ヘルパーと各種プロパティを実装（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム設定等）。
    - 設定値検証: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などで不正値時に ValueError を送出。
    - settings = Settings() の単一インスタンスをエクスポート。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定を実装（Windows / POSIX(Linux, Darwin, FreeBSD) を吸収）。
    - set_process_priority(level: "high" | "normal" | "low") 実装。権限不足や未対応 OS 時は警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count: int | None) 実装（最初の N コアにプロセスをピン留め）。引数検証と失敗時のログあり。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - select_candidates(buy_signals, max_positions) を追加：スコア降順・signal_rank によるタイブレークで候補選定。
    - calc_equal_weights(candidates) を追加：等金額配分。
    - calc_score_weights(candidates) を追加：スコア加重配分（全銘柄スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap(...) を追加：既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外。unknown セクターは制限の対象外。
    - calc_regime_multiplier(regime) を追加：market regime に応じた投下資金乗数（bull/neutral/bear）。未知レジームは 1.0 でフォールバックし警告ログ。

  - portfolio/position_sizing.py
    - calc_position_sizes(...) を追加：allocation_method("risk_based" / "equal" / "score") に対応した発注株数算出。
      - lot_size 単位で切り捨て、per-position 上限・aggregate cap（利用可能現金）でスケールダウンするロジックを実装。
      - cost_buffer を考慮した保守的コスト見積り、スケールダウン時の残差解消ロジックを実装。
      - 価格が欠損・非正値の銘柄はスキップし、ログ出力。

  - portfolio/__init__.py で関数群をエクスポート。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum(conn, target_date)：1M/3M/6M リターン、MA200 乖離の計算。
    - calc_volatility(conn, target_date)：20日 ATR、ATR 比率、20日平均売買代金、出来高比率の計算。
    - calc_value(conn, target_date)：raw_financials から EPS/ROE を取得して PER/ROE を計算。
    - DuckDB を用いた SQL ベース実装。データ不足時は None を返す設計。

  - research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons)：将来リターン計算（複数ホライズン）。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンランク相関（IC）計算。有効レコードが 3 未満なら None。
    - rank(values)：同順位は平均ランクで扱うランキング実装（浮動小数丸めで ties の検出誤差を低減）。
    - factor_summary(records, columns)：count/mean/std/min/max/median の集計。

  - research/__init__.py で主要関数をエクスポート（zscore_normalize は kabusys.data.stats から）。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む仕組みを実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で算出。
    - チャンク処理（デフォルト 20 銘柄/回）、記事・文字数上限 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK) によるトリム実装。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフによるリトライ実装、最大リトライ回数制限。
    - レスポンス検証、スコアを ±1.0 にクリップ、部分失敗時に他銘柄の既存スコアを保護しつつ置換（DELETE→INSERT の限定的置換戦略）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - コマンドラインから期間指定 (--from / --to) と DB パス (--db) を受け付け、PAPER_TRADING_SQLITE_PATH をデフォルトとして利用可能。
    - 指標:
      - 稼働率（uptime）・総ポーリング数・エラー数
      - 注文成功率（Filled / Created）
      - 送信率（Sent / Created）
      - リスク却下数（risk_logs）
      - レイテンシ（平均 / 最大 / P95）
    - PASS/FAIL 判定ロジックおよび閾値（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200ms）を実装。
    - P95 算出、日付フィルタリング、DB 存在チェック、テーブル欠如時の耐性を持たせた実装。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Security
- なし

Notes / 実装上の注意点
- config._find_project_root() は __file__ を起点に親ディレクトリを探索するため、CWD に依存せずパッケージ配布後も .env 自動ロードが有効になる設計。ただしプロジェクトルートが見つからない場合は自動ロードをスキップする。
- run_monitoring は監視用 DB として常に settings.sqlite_path（本番 DB 想定）を使用する設計。テスト時は注意すること。
- run_execution は paper_trading モード時に settings.paper_sqlite_path を使用し、本番 DB と分離するため、安全にペーパートレードを行える。
- process_priority の呼び出しは権限不足等で失敗する可能性があるため例外を抑えて警告ログで継続する設計。
- DuckDB / SQLite に依存する関数群は SQL 側のテーブルスキーマを前提としている（prices_daily / raw_financials / trade_logs / system_status / raw_news / news_symbols / ai_scores / risk_logs 等）。
- ai/news_nlp.py の OpenAI 呼び出し部は外部 API 依存のため、API レート・課金・レスポンス安定性に注意。部分的障害に対してはフェイルセーフでスキップする設計。

今後の予定（想定）
- テストカバレッジの追加（特にエッジケースの DB テーブル欠如、外部 API の失敗パス）。
- ポートフォリオ構築ロジックの更なるチューニング（lot_size 銘柄別対応、価格フォールバック）。
- AI スコアリングのバッチ管理とメトリクス（成功率 / レイテンシ）の監視強化。
- ドキュメント（PortfolioConstruction.md, StrategyModel.md など）との整合性レビューとサンプルデータセットの提供。