# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージ内の __version__（現在: 0.1.0）に合わせています。

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション構成とバージョン情報を追加
  - パッケージメタ情報: __version__ = "0.1.0"（kabusys/__init__.py）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - 自動読み込みを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - 環境変数ロードにおける上書き制御（override / protected）をサポート。
  - Settings クラスを追加し、主要な設定値をプロパティ経由で取得（DB パス、API トークン、監視閾値、環境種別等）。
  - 環境値のバリデーションを追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- 実行エントリ/監視エントリ
  - 実行エンジン起動スクリプト（run_execution.py）
    - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority）。
    - 環境に応じた SQLite 接続切り替え（paper_trading 環境では paper_sqlite_path を使用し、本番 DB と分離）。
    - DuckDB 接続の作成（duckdb_path）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。エンジンをスレッド実行し、デーモン化。
    - 停止制御: data/stop_requested.flag の存在で起動抑止・実行中はフラグを検知して安全停止。
    - 実行用 PID ファイルパスをサポート（data/execution.pid 等）。
    - RiskManager の初期設定例（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装し、初期ポートフォリオ値を broker.get_available_cash() から取得。

  - 監視ループ起動スクリプト（run_monitoring.py）
    - プロセス優先度設定（high）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - duckdb 接続と sqlite3 接続を作成。
    - init_monitoring_db 呼び出しで監視用テーブルの存在を保証。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 停止フラグファイル（data/stop_requested.flag）によるループ終了処理を実装。KeyboardInterrupt による終了にも対応。

- 監視 DB 初期化ヘルパー呼び出し（monitoring_db との連携箇所を複数スクリプトで利用）

- ユーティリティ：プロセス優先度 / CPU affinity（kabusys.utils.process_priority）
  - set_process_priority(level) を実装（Windows と POSIX(Linux/Mac/FreeBSD) に対応、未対応 OS ではスキップ）。
  - set_cpu_affinity(cpu_count) を実装（最初の N コアに固定、存在しない場合は全コアを使用）。
  - 権限不足や未実装 API を安全にハンドリングしてログ出力で通知。

- Portfolio 構築モジュール（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソートと上位選抜（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全てが 0 の場合に等重でフォールバック＆警告）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター別時価を計算して上限超過セクターの候補除外）。unknown セクターは上限を適用しない。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト／フォールバック値を含む）。
  - position_sizing
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した株数計算。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash 超過時のスケールダウン）を実装。
    - cost_buffer を考慮した保守的なコスト見積りと残差に基づく追加配分アルゴリズムを実装。

- 研究 / リサーチ機能（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を DuckDB の prices_daily から計算。
    - calc_volatility: ATR(20), ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials（最新）と prices_daily を結合して PER / ROE を算出。
    - 各関数はデータ不足時に None を適切に返す設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を活用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクで処理するランク関数（丸めによる ties 検出対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- Paper Trading 用ツール（kabusys.tools.paper_verification_report）
  - Paper Trading の検証レポート出力スクリプトを追加。
  - コマンドライン引数 (--from / --to / --db) をサポート。
  - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計してレポート出力。
  - Pass/Fail の閾値を設定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
  - DB が存在しない場合・テーブルがない場合のフォールバック処理を実装（OperationalError を捕捉して N/A や 0 を返す）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でスコアリングするための実装を追加。
  - スコアリング設計:
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST の記事）を計算する calc_news_window。
    - バッチ送信（最大 20 銘柄／リクエスト）、トークン肥大化対策（記事数と文字数の上限）。
    - リトライ（429 / 接続エラー / タイムアウト / 5xx）で指数バックオフを実施。
    - レスポンスのバリデーション（JSON Mode 想定）とスコアの ±1.0 クリップ。
    - 成功した銘柄のみ ai_scores テーブルに置換して書き込む（部分失敗時の保護）。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

### Changed
- 環境変数の読み込み設計を確立
  - OS 環境変数を保護する protected set を導入し .env.local での上書きを安全に実施可能に。
  - .env のパースは柔軟（export、クォート、エスケープ、インラインコメント）に対応。

- 実行・監視起動時のプロセス優先度設定を標準化（起動直後に set_process_priority("high") を呼び出す）。

- Paper Trading と本番データの分離を明確化
  - run_execution は settings.is_paper に応じて別 SQLite DB（paper_sqlite_path）を使用。
  - 監視(run_monitoring) は常に本番 sqlite_path を参照する（監視データは本番 DB に保存）。

### Fixed
- N/A（初期リリースにつき bugfix は特記なし）。ただし、いくつかの箇所で運用上の注意をログ・コメントに明記。

### Deprecated
- N/A

### Removed
- N/A

### Security
- OpenAI API キーなどの機密情報は環境変数経由で利用する設計。.env の自動ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

### Notes / Known issues / Limitations
- apply_sector_cap において price_map に欠損（0.0）があるとエクスポージャーが過小評価される可能性があり、将来的に前日終値や取得原価などのフォールバック価格を検討する旨の TODO コメントが残っています。
- calc_score_weights で全スコアが 0 の場合は等金額配分にフォールバックし警告を出す挙動になっています。
- process_priority の設定は OS と権限に依存します。権限不足や未対応プラットフォームでは設定がスキップされ、警告ログが出力されます。
- news_nlp モジュールは外部 API (OpenAI) への依存があり、API 使用量やレスポンス仕様の変更による影響を受けます。実装はフェイルセーフ（失敗時はスキップして継続）を意図していますが、運用上のポリシー（API キー管理・レート制御等）に注意してください。
- ai/news_nlp の処理本体は長く複雑なため、実運用時は API レートやコスト、結果の検証ロジックを十分に確認してください。

---

今後の予定（アイデア）
- unit テストの追加（.env パーサー、portfolio 計算ロジック、research の SQL ロジック等）
- モジュール間のドキュメント整備（PortfolioConstruction.md / StrategyModel.md 参照箇所のコードとの整合性確認）
- ai/news_nlp の部分失敗時のトランザクション改善（より細かなロールバック/リトライ戦略）
- 銘柄ごとの lot_size を stocks マスタから取得する拡張

（以上）