# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

- 特になし

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はロギングしてデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止。
    - SQLite / DuckDB 接続の初期化とクリーンなクローズ。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、paper_trading 用 SQLite（`data/paper_trading.db` 既定）を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading では Mock クライアントが想定される）。
    - OrderRepository、OrderManager、RiskManager（既定パラメータあり）、Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで実行、停止フラグ検知により engine.stop() を呼ぶ安全停止処理。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行 PID ファイル path を指定可能。

- 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動ロードを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト用途）。
    - .env のパーサーを改善:
      - export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
      - 無効行はスキップ。
    - `.env` 読み込み時の override/protected（OS 環境変数 保護）機能を実装。
    - Settings クラスを追加し、アプリケーション設定（DB パス、API トークン、監視閾値、環境種別等）をプロパティ経由で安全に取得。
    - 設定値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を行い不正値は ValueError を送出。
    - 各種デフォルトを明確化（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, 閾値のデフォルト値）。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。
    - set_process_priority(level: "high" | "normal" | "low") を提供。権限不足や未対応 OS は警告ログを出して安全にスキップ。
    - set_cpu_affinity(cpu_count: int | None) を提供。引数検証と権限例外の安全ハンドリングあり。

- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を run スクリプトから呼び出して、監視用テーブルの存在を保障（冪等）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - デフォルト DB: `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で上書き可能）。
    - レポート項目:
      - システム稼働率（uptime）
      - 注文成功率（fill rate）
      - 送信率（send rate）
      - リスク却下数
      - API レイテンシ（avg, max, P95）
    - P95 計算、日付フィルタ（--from, --to）をサポート。
    - 合否判定用基準値（稼働率 99.0%、注文成功率 90% 等）を定義し PASS/FAIL を出力。
    - DB のテーブル欠如や空データを想定した堅牢なハンドリング（OperationalError を捕捉して N/A を扱う）。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順 + tie-breaker に signal_rank）。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等分配にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中排除 apply_sector_cap（既存保有からセクター別時価を計算し上限を超えるセクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マップ、未知はフォールバック 1.0）。
  - portfolio/position_sizing.py
    - 銘柄ごとの発注株数算出ロジックを実装（allocation_method: "risk_based" | "equal" | "score"）。
    - risk_based: リスク許容率・ストップロスから算出。
    - equal/score: ウェイトに基づく割付、単元株（lot_size）丸め、1銘柄上限（max_position_pct）対応。
    - aggregate cap: 全銘柄合計が available_cash を超える場合のスケールダウンと残差配分アルゴリズムを実装。cost_buffer（スリッページ・手数料想定）を考慮。

- リサーチ（Factor / Feature）モジュール
  - research/factor_research.py
    - DuckDB を用いたファクター計算群を実装。
    - Momentum（1M/3M/6M リターン、MA200乖離）、Volatility（ATR20, 相対ATR, 20日平均売買代金, 出来高比率）、Value（PER, ROE）を計算する純粋関数を追加。
    - SQL ウィンドウ関数を使い、データ不足時は None を返す設計。
  - research/feature_exploration.py
    - 将来リターン（calc_forward_returns）、IC（calc_ic: スピアマンランク相関）、ランク付けユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - horizons の検証や最小サンプル数チェック（有効レコード < 3 → None）など堅牢な実装。

- AI / NLP
  - ai/news_nlp.py (途中までの実装を含む)
    - ニュース記事のセンチメントを OpenAI (gpt-4o-mini) でスコアリングし `ai_scores` テーブルへ書き込む機能を実装（設計と大部分の実装）。
    - タイムウィンドウ計算（target_date に対する JST ベースの window を UTC に変換する calc_news_window）を実装。
    - バッチサイズ、最大記事数/文字数制限、スコアの ±1.0 クリップ、最大リトライ回数・指数バックオフなどを定義。
    - API キー解決（引数 or 環境変数 OPENAI_API_KEY）と未設定時の ValueError。
    - OpenAI のエラー（429, ネットワーク断, タイムアウト, 5xx）に対する共通リトライ戦略の設計。
    - レスポンス検証、部分成功時のテーブル更新（対象コードの置換で他のコードのスコアを保護）などフェイルセーフな更新方針を採用。
    - （注）ファイルは途中で切れているが、主要な設計方針と前半ロジックは実装済み。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- 多くのモジュールで「DB 参照なしの純粋関数」として設計（ポートフォリオ関連など）。これによりユニットテストが容易。
- DuckDB を分析処理（prices_daily / raw_financials ベースの集計）に採用し、SQL と Python の混合で効率的に計算を行う方針。
- 各種箇所で例外を捕捉してログに記録し、処理を継続する設計（監視ループ、レポート生成、API 呼び出し等）。
- 一部 TODO / 注意コメントあり（例: 価格欠損時のフォールバック価格、将来の lot_size の銘柄別対応など）。

### Security
- 環境変数による API キー等の取り扱いを前提。OpenAI API キー未設定時は明示的な例外を投げる箇所あり。

---

このリリースには多くの新規モジュールとユーティリティが含まれており、自動売買システムの「監視」「実行」「ポートフォリオ構築」「調査」「ニュース NLP」等の基盤機能を一通り備えています。必要であれば各モジュールごとの詳細な変更点（関数一覧、引数仕様、例外動作、既知の制限事項など）を別途ドキュメント化します。