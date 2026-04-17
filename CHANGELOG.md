# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
初期リリース相当のコードベースから、ファイル内容を読み取って推測した変更点を日本語で記載しています。

注: 日付はコード解析時点（2026-04-17）を使用しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17

### Added
- 全体
  - パッケージ初期実装を追加。バージョンは `kabusys.__version__ = "0.1.0"`。
  - モジュール構成（execution / monitoring / portfolio / research / ai / tools / utils 等）を実装。

- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動とデーモンスレッド管理を実装。
    - 停止用フラグファイル（data/stop_requested.flag）検知により安全に停止可能。
    - プロセス優先度を起動時に "high" に設定する呼び出しを追加。
  - run_monitoring.py: システム監視ループのエントリポイントを実装。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、無効値は警告出力してデフォルトにフォールバック）。
    - 監視は環境に関係なく本番用 sqlite_path を使用する設計（監視データは一元的に保存）。
    - 停止フラグ検知でループ終了、例外発生時はログを出して次回ポーリングへ継続。
    - プロセス優先度設定を呼び出す。

- 設定管理
  - config.Settings クラス実装。
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数の保護（protected）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 環境変数パースの強化（export プレフィックス対応、クォート内エスケープ、インラインコメント扱い等）。
    - 各種プロパティで入力値検証とデフォルト値を提供（例: KABUSYS_ENV の有効値検査、LOG_LEVEL の検査、PAPER_FILL_MODE の検査）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）、PID / kill flag のパス、閾値（CPU/MEM/DISK）など多数の設定プロパティを提供。

- データベース / モニタリング初期化
  - monitoring_db.init_monitoring_db を起動時に呼び出して監視テーブルの存在を保証（冪等）。

- ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（high/normal/low）を実装。psutil を利用。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を追加（検証・例外時は警告でスキップ）。
    - 権限不足や未対応 OS の場合は警告を出してスキップする安全設計。

- ポートフォリオ構築
  - portfolio.portfolio_builder:
    - select_candidates: スコア順でBUY候補を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を実装。全スコアが 0 の場合は等配分へフォールバックして警告を出す。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 同一セクターの既存保有比率が上限を超える場合に新規候補を除外する機能を実装。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数算出ロジックを実装。
      - allocation_method: "risk_based"（リスクベース）、"equal"、"score" をサポート。
      - 損切り・リスク率、単元株（lot_size）で丸め、1銘柄上限・全体投下上限（max_utilization）を考慮。
      - cost_buffer を使った保守的なコスト見積もりと、aggregate cap 超過時のスケーリング（端数は lot 単位で再配分）を実装。
      - 価格欠損時や不正値はログでスキップする安全設計。

- 研究（Research）モジュール
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を DuckDB の prices_daily を用いて計算。過少データ時は None を返す。
    - calc_volatility: 20日 ATR、ATR 比、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播制御など精密な SQL）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER、ROE を計算。target_date 以前の最新財務データを取得するロジックを実装。
  - research.feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを1クエリで取得。ホライズン検証（1..252）を実施。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。有効レコード3件未満は None を返す。
    - rank / factor_summary: ランキング（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を実装。
  - research.__init__: zscore_normalize（kabusys.data.stats）や上記関数群をエクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - OpenAI（gpt-4o-mini）を用いたニュース記事のセンチメントスコアリングの骨格を実装。
    - ニュース収集ウィンドウ計算（JST基準 → UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/回）、スコアの ±1.0 クリップ、リトライ（429/ネットワーク/5xx 共通、指数バックオフ）などを想定した設計。
    - API キー解決（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
    - 設計上のフェイルセーフ（API失敗はスキップして継続）や部分置換（特定コードだけ更新）などの方針を明記。
    - （注）ファイル末尾で記事集約処理呼び出し部分が途中で切れているため、実装の一部は未表示／未完の可能性あり。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - CLI で期間指定（--from / --to）や DB パス指定（--db）をサポート。環境変数 PAPER_TRADING_SQLITE_PATH を利用可能。
    - システム稼働率・注文成功率・送信率・P95 レイテンシ等を計算して標準出力にレポートを出力。
    - 判定基準（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 レイテンシ <=200ms）を定義して PASS/FAIL を判定。
    - SQL による日付フィルタリング、P95 計算ユーティリティ、欠損時の N/A 表示等を実装。

### Changed
- 初版相当のため、主に新規追加。既存コードからの変更点は特になし。

### Fixed
- 多くの関数で None / データ不足 / 例外ケースをハンドリングする実装を追加（例: DuckDB/SQLite の OperationalError によるフォールバック、値検証と警告出力など）。これにより実行時の堅牢性を向上。

### Security
- OpenAI API キーの取得を環境変数 / 引数に限定し、未設定時は明示的に例外を投げる仕様により誤設定を防止。

### Known limitations / Notes
- ai/news_nlp.py の記事集約処理（_fetch_articles 呼び出し以降）がソースの最後で途切れているため、スコアリングフローの一部（記事フェッチ〜API送信〜DB 書込の完全な実装）は未確認です。実運用前に残りの実装と統合テストが必要です。
- 一部の TODO コメント（価格欠損時のフォールバックや銘柄別 lot_size 管理など）が残っています。将来的な拡張ポイントとして意図的に残されています。
- process_priority の権限問題や OS 未対応時は警告でスキップする設計だが、運用環境によっては追加の権限付与が必要です。

---

本 CHANGELOG はコードの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて調整してください。