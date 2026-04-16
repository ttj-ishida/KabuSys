# Changelog

すべての重要な変更をこのファイルに記録します。  
このファイルは "Keep a Changelog" の形式に従います。  

## [Unreleased]

## [0.1.0] - 2026-04-16
初回公開リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として導入。

- 実行・監視ランチャー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（モック含む）。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による外部停止を監視。
    - 実行中の PID を data/execution.pid に保存するための pid_file をサポート。
    - RiskManager, OrderManager, Reconciler 等の主要コンポーネントを組み立てて起動。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視処理は環境に関わらず本番の sqlite_path を使用して監視テーブルを更新。
    - data/stop_requested.flag による停止、KeyboardInterrupt の graceful shutdown を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

- 設定管理
  - config.Settings クラスを導入し、環境変数経由でアプリ設定を一元管理。
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 形式、クォート付き値（エスケープ考慮）、インラインコメントの取り扱い等に対応。
    - 多数の設定プロパティを提供（J-Quants / kabu / LINE / DB パス / 監視設定 / システム環境判定 等）。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等の Path 型プロパティを提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補を選択、同点は signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化に基づく重み（全スコア 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有と候補を考慮したセクター集中上限（max_sector_pct）チェック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio.position_sizing
    - calc_position_sizes: 等配分・スコア配分・リスクベース配分をサポート。単元株（lot_size）丸め、1銘柄上限・aggregate 上限、コストバッファを考慮したスケーリングなどを実装。

- 研究（Research）モジュール
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB で計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務データを取得し PER/ROE を算出。
    - 全て DuckDB の SQL（ウィンドウ関数）を用いた実装でパフォーマンスを意識。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算。ホライズンの検証あり。
    - calc_ic / rank: スピアマンランク相関（IC）を計算。タイ付き順位は平均ランクで処理。
    - factor_summary: count/mean/std/min/max/median を計算する統計要約。
  - research.__init__ による主要 API の公開（zscore_normalize を含む）。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込むロジックを実装。
    - バッチサイズ、最大記事数・最大文字数制限、P95/TPS を考慮した設計。
    - 429/ネットワーク/5xx 等のエラーに対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - target_date に対するニュース時間窓計算（JST → UTC 変換）を提供（calc_news_window）。
    - OpenAI API キー未設定時は ValueError を送出。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を追加。期間指定（--from / --to）と DB パス指定（--db）をサポート。
    - システム稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL 判定を出力。閾値はソース内で定義（稼働率 99%、成功率 90% 等）。

- ユーティリティ
  - utils.process_priority
    - プラットフォーム差を吸収するプロセス優先度設定ユーティリティ（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity 設定関数（set_cpu_affinity）を提供。権限不足や未サポート環境では警告ログでスキップ。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- （初回リリースのため過去との互換性変更は無し）

### Fixed
- 環境変数パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内部のエスケープ処理、インラインコメントの取り扱いを実装して .env のパース精度を向上。
- .env の自動ロード時に OS 環境変数を保護する仕組みを導入（.env.local は上書き可能だが OS 環境変数は保護）。

### Known issues / TODO
- ai.news_nlp の実装ファイルは本スナップショットで末尾が切れている箇所があり（_fetch_articles 呼び出し付近で切断）、完全な処理フローの実行確認が必要。
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りになる可能性がある旨の TODO コメントあり。前日終値等のフォールバック実装が未実装。
- position_sizing:
  - lot_size を銘柄別に持たせる拡張は TODO（現在は全銘柄共通の lot_size を使用）。
- DuckDB に対する一部の操作（executemany 等）で空 params が問題となるケースがあり、コード内で注意喚起コメントあり。
- テストコード・CI 設定は本リリースに含まれない（別途整備予定）。

### Security
- 現状、機密情報（API キー等）は環境変数経由で扱う設計。利用者は .env/.env.local のファイル管理に留意すること。

---

今後のリリースでは以下を予定しています（未確定）:
- AI ニュース NLP の完遂とエンドツーエンドテスト。
- per-stock lot_size 対応、価格フォールバックロジックの追加。
- 単体テスト・統合テスト・CI の整備。
- ドキュメント（API 参照、アーキテクチャ図、運用手順）の拡充。