# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
このファイルは、コードベース（src/ 以下）から実装内容を推測して作成した変更履歴です。

## [Unreleased]

- 次回リリース向けの変更点を記載します。

---

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ情報
  - パッケージ初期化（kabusys.__init__）にバージョン `0.1.0` を導入。

- 実行 / 監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
    - 実行中の PID ファイル管理（data/execution.pid）および停止フラグ（data/stop_requested.flag）をサポート。デーモンスレッドでエンジンを起動、停止フラグ検知で安全に停止。
    - 各種依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てを実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。

  - run_monitoring.py: SystemMonitor をポーリングで動かす監視プロセス起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（運用上の意図的挙動）。
    - 停止フラグによりループを終了、例外はログ出力して次ポーリングに進む堅牢なループ設計。

- 設定・環境変数管理
  - config.Settings クラスを追加。
    - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - .env / .env.local の読み込み順序、OS環境変数保護（protected）を実装。
    - 各種プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境種別判定等）。
    - `PAPER_FILL_MODE` の検証（有効値: instant|partial|never|reject）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の値検証（許容値チェック）。
    - `settings` のシングルトンインスタンスを提供。

- .env パーサー
  - export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント扱いのルール（クォート有無で挙動を分離）など堅牢な行パーシングを実装。
  - ファイル読み込み失敗時に警告を出す。

- DB / 分析連携
  - DuckDB 接続を受け取る設計を導入（各種 research / ai モジュールで使用）。
  - 監視用テーブル初期化ユーティリティ（init_monitoring_db）を run_* スクリプトから呼び出し、監視テーブルの冪等初期化を保証。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順・同点は signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア全て 0 の場合は等配分へフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を計算し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: weight と候補を元に発注株数を算出（risk_based / equal / score の各方式）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer による保守的推定、残差処理による追加配分アルゴリズムを実装。

- 研究（research）モジュール
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB 上で計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算（NULL 伝播に配慮）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（最新の財務レコードを選択）。
  - research.feature_exploration
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンを一括クエリで算出。horizons のバリデーションあり。
    - calc_ic: factor と将来リターンを code で結合し Spearman 相関（ランク相関）を計算（ties を平均ランクで処理）。有効サンプルが 3 未満の場合は None を返す。
    - factor_summary / rank: 基本統計量算出とランク付けユーティリティを実装。
  - research モジュールは zscore_normalize（kabusys.data.stats）と併用できるようエクスポートを整備。

- AI ニュース NLP
  - ai.news_nlp モジュールを追加。
    - raw_news / news_symbols を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score（-1.0〜1.0）を ai_scores テーブルへ書き込む設計を実装。
    - バッチサイズ、最大記事数・文字数トリム、スコアクリップ、最大リトライ回数（429/5xx/タイムアウト等）と指数バックオフ、レスポンスバリデーション等の堅牢化が組み込まれている。
    - ニュース収集ウィンドウ（JST ベース）を正確に UTC に変換する calc_news_window を実装。
    - OpenAI API キーの解決ロジック（引数 > 環境変数）を実装。
    - 注意: ファイル末尾付近で処理が途中で切れているため（_fetch_articles の呼び出し以降が未完）、一部機能は実装途中。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 引数で期間（--from / --to）と DB パス（--db）を指定可能。デフォルト DB は data/paper_trading.db。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計してレポート表示。
    - 合否判定基準（閾値）を明記:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 空データやテーブル未存在時のフォールバックを考慮。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。アクセス拒否や未対応 OS では警告を出してフォールバック。
    - set_cpu_affinity(cpu_count): 指定したコア数に CPU affinity を設定（例外ハンドリングあり）。

### Changed
- 実行 / 監視の DB 使用方針
  - 監視プロセスは KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨を明確化（運用設計上の決定）。
  - ExecutionEngine は paper_trading 環境時に専用 paper DB（settings.paper_sqlite_path）を使用して本番とデータ分離。

- ログ設定
  - run_* スクリプトで logging.basicConfig(level=logging.INFO) を使ってデフォルトログレベルを INFO に設定。

- .env 自動ロード動作
  - プロジェクトルートが検出できない場合は自動ロードをスキップするようにし、KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを明示的に無効化可能。

### Fixed / Hardened
- 設定入力のバリデーションを追加/強化
  - MONITOR_POLL_INTERVAL のパースとフォールバック（0 以下 / 非整数はデフォルトに戻す）。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の許容値チェックとエラーメッセージ。
  - calc_forward_returns の horizons 入力検証（正の整数かつ <= 252）。
  - calc_position_sizes 等における価格欠損（価格が None または <= 0 の場合はスキップ）によりゼロ除算や不正結果を回避。

- DB クエリの堅牢化
  - factor/research モジュールでウィンドウバッファや NULL 伝播を考慮した SQL を使用し、データ不足時に None を返すように設計。

- エラーハンドリング
  - run_monitoring のポーリングループで monitor.check_once() の例外を捕捉してログ出力し、次回ポーリングへ継続するフェイルセーフを導入。
  - process_priority / cpu_affinity 呼び出しで権限不足や未実装例外を捕捉して警告を出すように改善。

### Known issues / Notes
- ai/news_nlp モジュールはファイル末尾付近で実装が途切れており、記事集約・API 呼び出しの続き処理（_fetch_articles 等）が未完。使用前に残り実装が必要。
- position_sizing の価格フォールバックは未実装（price が欠損した場合の前日終値や取得原価を使った代替ロジックは TODO コメントあり）。
- apply_sector_cap は "unknown" セクターを除外対象にしない設計だが、実データで想定外の挙動をする可能性があるため運用時に検証が必要。
- DuckDB executemany に関する注意（ai モジュール内コメント）: 空パラメータでの実行失敗を避ける実装上の注意あり。

---

作成者注:
- 本 CHANGELOG は提供されたソースコード（src/ 以下）を解析して推測に基づき作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。