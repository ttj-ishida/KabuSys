KEEP A CHANGELOG
すべての重要な変更をここに記録します。フォーマットは Keep a Changelog 準拠です。

※以下は提供されたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]
- なし（現時点での最新版は 0.1.0。今後の変更はここに追記）

## [0.1.0] - 2026-04-17
初期リリース（コードベースから推測）

### Added
- 基本パッケージ情報
  - パッケージバージョンを公開: kabusys.__version__ = "0.1.0"。
- 環境・設定管理
  - Settings クラスを実装し、環境変数／.env ファイルから設定を読み取る機能を追加。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml）および .env / .env.local の読み込み順を実装。OS 環境変数を保護する仕組みを導入。
  - .env パーサの強化: コメント処理、export プレフィックス、クォート内のバックスラッシュエスケープ対応などを実装。
  - 各種設定プロパティを追加（J-Quants、kabuステーション、LINE、DB パス、監視閾値、環境種別判定など）。
  - 入力検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）を実装し、不正値は例外を投げる/ログを出す。

- 実行スクリプト / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを提供。paper_trading 環境では専用の paper DB を使用し本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。停止フラグファイルで安全に停止可能。
  - 起動時にプロセス優先度を設定するユーティリティ呼び出しを導入（高優先度に設定）。

- 実行コンポーネント（推定）
  - ExecutionEngine の組み立て処理を実装（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等を組み合わせて起動）。
  - RiskManager 初期化用の RiskConfig（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を追加。
  - ExecutionEngine はスレッドで run_session を実行し、停止フラグで停止処理を行う。

- 監視 DB / 分析基盤
  - monitoring 用 DB 初期化機能（init_monitoring_db）を各起動スクリプトで呼び出し、監視テーブルの存在を保証。
  - DuckDB を解析用データベースとして使用する接続処理を追加（duckdb_path）。

- ポートフォリオ構築ロジック
  - portfolio.portfolio_builder:
    - 信号候補選定 (select_candidates)
    - 等金額配分 (calc_equal_weights)
    - スコア加重配分 (calc_score_weights)（全銘柄スコアが 0 の場合は等配分にフォールバック）
  - portfolio.risk_adjustment:
    - セクター集中制限適用 (apply_sector_cap)。既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数計算 (calc_regime_multiplier)（bull/neutral/bear をサポート、未知はフォールバック）。
  - portfolio.position_sizing:
    - position size（発注株数）の計算 (calc_position_sizes)。allocation_method として "risk_based"、"equal"、"score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - スケーリング時の残差処理（lot 単位での再配分）を導入。

- 研究（research）モジュール
  - research.factor_research:
    - Momentum, Volatility, Value ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。prices_daily / raw_financials を DuckDB で参照。
    - ATR / MA200 / 各ホライズンのリターン等を SQL ウィンドウ関数で算出。十分な過去データが無い場合は None を返す設計。
  - research.feature_exploration:
    - 将来リターン計算 (calc_forward_returns)（複数ホライズンを同時に計算可能）。
    - IC 計算 (calc_ic)（Spearman の ρ をランク手法で実装）。
    - ファクター統計サマリ (factor_summary)、ランク関数 (rank) を実装。
  - zscore_normalize を kabusys.data.stats から再エクスポート。

- AI / ニュース NLP
  - ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores テーブルへ書き込む処理を実装（設計段階含む）。
    - バッチ処理（銘柄毎に最大 _MAX_ARTICLES_PER_STOCK 件、文字数トリム）、最大バッチサイズ _BATCH_SIZE=20。
    - OpenAI 呼び出し用のリトライ（429, ネットワークエラー, 5xx）を指数バックオフで行う方針。
    - レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ、部分更新（該当コードのみ DELETE→INSERT）で部分失敗耐性を確保。
    - ニュース時間ウィンドウ計算 utility を実装（JST 基準で前日 15:00〜当日 08:30 を UTC に変換）。

- CLI ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを実装（コマンドライン引数 --from / --to / --db をサポート）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計し、閾値に基づく PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ組み立て、安全な DB 存在チェック、出力整形を実装。
    - デフォルトの評価閾値を定義（稼働率 99.0%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。

- ユーティリティ
  - utils.process_priority:
    - Windows / POSIX の差分を吸収してプロセス優先度を設定する set_process_priority(level) を実装（"high" / "normal" / "low"）。
    - set_cpu_affinity(cpu_count) を実装し、指定コア数にプロセスを固定可能（権限未許可時は警告ログでスキップ）。
    - psutil 例外ハンドリングを実装して失敗時も安全にスキップ。

### Changed / Improved
- 設定と起動時の堅牢性強化
  - MONITOR_POLL_INTERVAL の環境値に対するフォールバックとログ警告を追加（不正値に対するデフォルト回復）。
  - DB 初期化（監視テーブル）を冪等に行う（init_monitoring_db を複数箇所で呼び出し）。
  - Execution 起動時に paper_trading と本番 DB を明確に分離。paper_trading 環境では専用 SQLite を使用することで本番データと完全分離。
  - 実行開始前に停止フラグファイルの存在をチェックして即時終了できる安全策を追加。

- SQL / 集計の堅牢化
  - ファクター計算・集計クエリで NULL 伝播に注意した実装（例えば true_range の NULL 制御やウィンドウ幅チェック）。
  - forward returns / momentum 等でスキャン範囲を適切に限定するバッファ（日数換算）を導入してパフォーマンスを意識。
  - paper_verification_report は DB のテーブル欠損時に sqlite3.OperationalError を捕捉して graceful に扱う。

### Fixed
- 環境値の不正に対する挙動を改善（例: MONITOR_POLL_INTERVAL が負または非数の場合に警告を出してデフォルトに戻す）。
- calc_score_weights: 全スコアが 0 の場合に等配分へフォールバックするように変更（警告ログあり）。

### Security
- OpenAI API キーの取得を引数優先とし、未設定時は ValueError を発生させることで意図しない公開を防止。

### Notes / Known limitations
- ai/news_nlp の実装は設計が詳細に含まれているが、提供コードは途中で切れている（関数内部で記事取得の続きを示唆する箇所で途切れ）。実行時には記事の取得・API 呼び出し・DB 書き込みの結合部分の実装完了が必要。
- 一部関数は将来的な拡張の余地を注記（例: position_sizing の銘柄別 lot_size 対応、apply_sector_cap の価格欠損時のフォールバック価格利用等）。
- Windows / POSIX における権限不足でプロセス優先度や CPU affinity の設定に失敗する場合はログ警告となり、安全にスキップされる設計。

---

参照:
- ソースファイル群（src/kabusys/**）より機能を抽出・要約しました。実際のリリース履歴を生成する場合はコミットログやリリース日、影響範囲の確認を推奨します。