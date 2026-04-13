# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
日付はコードベースの最終更新日として 2026-04-13 を使用しています。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 全体
  - 初期リリース。KabuSys のコア機能群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニュース評価、ユーティリティ、CLI ツール）を実装しました。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。不正値はログ出力のうえデフォルトにフォールバック。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視は環境設定にかかわらず本番用 SQLite パス（Settings.sqlite_path）を使用して DB に接続し、DuckDB も併用。
    - 例外発生時はログを残して次ポーリングへフォールバック、KeyboardInterrupt で graceful shutdown。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory を使ったブローカークライアント選択、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の run_session 起動を実装。
    - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors 等）を埋め込み、初期ポートフォリオ値はブローカーの available cash から取得して渡す。

- 設定管理
  - config.py
    - .env ファイルの自動ロード処理を実装。プロジェクトルートは .git または pyproject.toml を基準に探索（__file__ 起点で決定）。
    - `.env` / `.env.local` の読み込みルール:
      - OS 環境変数を保護（既存値は上書きしない）、`.env.local` は上書きフラグで読み込み。
      - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
    - 高機能な .env パーサを実装（`export KEY=val`、シングル/ダブルクォート内のエスケープ、インラインコメント扱い等をサポート）。
    - Settings クラスを実装し、各種設定プロパティを提供（DB パス、PID/KILL フラグ、閾値、env/log level 検証、paper_trading 用設定、PAPER_FILL_MODE のバリデーション等）。
    - 必須環境変数未設定時には明確なエラーを投げる `_require()` を用意（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - CLI から期間指定（--from / --to / --db）して、稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等を算出し、PASS/FAIL 判定を出力。
    - データ欠損（テーブル未作成等）を考慮して安全に動作するよう例外処理を実装。
    - デフォルト DB パスは `data/paper_trading.db`、環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可能。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順、タイブレークに signal_rank）および等金額/スコア加重の重み計算関数を追加。
    - 全銘柄のスコアが 0 の場合は等金額配分へフォールバックしログ出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価を計算し上限超過セクターの候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear とフォールバック）。

  - portfolio/position_sizing.py
    - 発注株数計算（risk_based / equal / score）を実装。損切り率・risk_pct を使った risk-based 計算、単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer の導入による保守的見積りを実装。
    - スケールダウン後の残余配分ロジック（fractional remainder に基づく lot_size 単位での追加配分）を実装。

- ユーティリティ
  - utils/process_priority.py
    - cross-platform なプロセス優先度設定ユーティリティを追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収し、`set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップするフェールセーフ挙動。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り prices_daily/raw_financials を用いたファクター計算を実装（momentum / volatility / value）。
    - 計算の詳細（窓幅、欠損時の None 返却、SQL ベースの高速処理）を実装。

  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク変換ユーティリティ、ファクター統計サマリーを実装。
    - 外部ライブラリに依存せず純 Python で実装。

  - research/__init__.py
    - 主要関数をパッケージエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別にセンチメント評価を行い、ai_scores テーブルへ書き込むロジックを追加。
    - 処理フロー: 時間ウィンドウ計算（JST ベース→UTC 変換）、記事トリム（記事数・文字数上限）、最大 20 銘柄単位のバッチ送信、429/ネットワーク/5xx に対する指数バックオフ・リトライ、レスポンスバリデーション、スコアクリップ（±1.0）、部分成功時の安全な DB 更新（対象コードのみ置換）を実装。
    - OpenAI API キーの解決（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。

### 変更 (Changed)
- 初期リリースのため過去バージョンからの互換性変更はありませんが、各モジュールは将来の拡張（lot_size の銘柄別対応、価格フォールバック、DB スキーマ拡張等）を念頭に設計されています。

### 修正 (Fixed)
- 初期リリースのため「修正」は特になし。内部で不正な設定値（例: MONITOR_POLL_INTERVAL の不正値や PAPER_FILL_MODE の不正値）に対するフォールバックと明示的なログ/例外を追加して堅牢性を確保。

### 注意事項 / マイグレーション
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings で必須扱い。未設定時は起動時に ValueError を送出します。
  - OPENAI_API_KEY は ai/news_nlp.score_news を呼ぶ際に必要（引数で渡すことも可）。
- 自動 .env ロード:
  - プロジェクトルートの検出に .git または pyproject.toml を使用するため、配布後に CWD を変えて実行する場合やパッケージ化した環境では auto-load をスキップする可能性があります。必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して制御してください。
- Paper Trading:
  - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）が使用され、本番 DB と論理的に分離されています。検証時はこの点に注意してください。
- DuckDB/SQLite:
  - 複数モジュールが DuckDB と SQLite を併用します。起動時にそれぞれの DB パス（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`）を確認してください。

---

今後のリリースでは以下を検討しています:
- 銘柄別 lot_size をサポートするためのマスタ導入
- price フォールバック（前日終値や取得原価）によるエクスポージャー算出改善
- ai/news_nlp の詳細なメトリクス収集・監視強化
- ユニットテスト・統合テストの拡充および CI 設定の公開

もし CHANGELOG に追記してほしい詳細（例えば各関数・API の互換性やより細かい実装意図）があれば教えてください。