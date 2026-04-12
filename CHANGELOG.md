# Changelog

すべての変更は「Keep a Changelog」形式に従って記載しています。  
このファイルは、与えられたコードベースの内容から実装済み機能・挙動を推測して作成したものであり、実際のコミット履歴と完全に一致しない場合があります。

フォーマット:
- Unreleased — 今後の変更（現時点では未設定）
- 各リリースに対して Added / Changed / Fixed / Deprecated / Removed / Security で記載

## [Unreleased]

（現在のコードベースは初期リリース相当の機能群を含むため、未リリース項目はありません）

---

## [0.1.0] - 2026-04-12

初回リリース（コードベースから推測）

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 環境/設定管理 (`kabusys.config`)
  - .env 自動読み込み機能を実装（プロジェクトルートに基づき `.env` / `.env.local` を読み込む）。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 行のパースは `export KEY=val`、クォート／エスケープ、インラインコメント等を考慮した堅牢な実装。
  - 必須環境変数チェック `_require()` を提供。
  - 設定クラス `Settings` を導入し、アプリケーションで使用する設定（DBパス、APIトークン、監視閾値、環境種別等）の取得インターフェースを提供。
  - デフォルト値や検証を含むプロパティを提供（例: `PAPER_FILL_MODE` の有効値検査、`KABUSYS_ENV` の検証、`LOG_LEVEL` の検証など）。
  - 便宜的に `settings = Settings()` をモジュールレベルで用意。

- 実行スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用する設計。
    - プロセス優先度を高（"high"）に設定する処理を実行開始時に行う。
    - Broker クライアントのファクトリ（`BrokerClientFactory.create(settings)`）を利用してブローカー依存を注入。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立ててセッションを実行。
    - DuckDB と SQLite の接続クローズを finally 節で保証。
    - 監視テーブルの初期化（`init_monitoring_db`）を行い、監視テーブルが存在することを保証（冪等）。

  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - `SystemMonitor` を使ったポーリング監視ループ（デフォルト 60 秒）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きに対応。無効値（0以下、非整数）はデフォルトへフォールバックし警告を出す。
    - 監視プロセスは環境（`KABUSYS_ENV`）にかかわらず本番用の sqlite_path を参照する設計（監視は常に production DB を見る仕様と明示）。
    - 起動時にプロセス優先度を "high" に設定。

- プロセス制御ユーティリティ (`kabusys.utils.process_priority`)
  - 現在プロセスの優先度設定 `set_process_priority(level)`（Windows / POSIX を吸収）を提供。
  - CPU affinity 設定 `set_cpu_affinity(cpu_count)` を提供。
  - 権限不足や未対応プラットフォームで安全にスキップするためのエラーハンドリングと警告出力。

- ポートフォリオ構築関連 (`kabusys.portfolio`)
  - 候補選定 / ウェイト計算（等重み・スコア重み）を含む `portfolio_builder`。
    - `select_candidates`, `calc_equal_weights`, `calc_score_weights` を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバック（警告ログあり）。
  - セクター集中制限・レジーム乗数 (`risk_adjustment`)
    - `apply_sector_cap`: 既存保有のセクター比率が閾値を超える場合、新規候補を除外。
    - `calc_regime_multiplier`: market regime に応じた投下資金乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3）を提供。未知レジームはフォールバック。
    - 実装に TODO コメント（価格欠損時のフォールバック等）を含む。
  - ポジションサイジング (`position_sizing`)
    - `calc_position_sizes` を実装。`risk_based` / `equal` / `score` の割当方法をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金超過時のスケーリング）、cost_buffer（手数料・スリッページ保守見積り）等、実用的なロジックを備える。
    - スケールダウン時に remainder を考慮して lot_size 単位で追加配分する再現性のある実装。

- 研究用モジュール (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - Momentum（1M/3M/6M リターン、MA200乖離）、Volatility（ATR20、相対ATR、20日平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB を使って計算する純粋関数を実装。
    - データ不足時には None を返す扱いを徹底。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）`calc_forward_returns`。
    - IC（Spearman ランク相関）計算 `calc_ic`、ランク変換 `rank`、ファクター要約統計 `factor_summary` を実装。
    - 外部ライブラリに依存せず純粋 Python/SQL で実装。
  - パッケージレベルで `zscore_normalize`（`kabusys.data.stats` から）や上記関数をエクスポート。

- Paper Trading / 検証ツール (`kabusys.tools.paper_verification_report`)
  - Paper Trading 用の SQLite DB（`data/paper_trading.db` デフォルト）を参照し、検証レポートを生成する CLI ツールを追加。
  - 指標:
    - 稼働率（uptime）、監視ログからの稼働/エラー指標
    - 注文成功率（Filled / Created）
    - 送信率（Sent / Created）
    - リスク却下数（risk_logs）
    - レイテンシ（avg / max / P95） — P95 は全値スキャンから計算
  - 合格基準（デフォルト閾値）を定義し、PASS/FAIL 判定を出力:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - コマンドライン引数 `--from` / `--to` / `--db` をサポート。DBパスは引数 > 環境変数 > デフォルトの順で解決。

- AI ニュース NLP モジュール (`kabusys.ai.news_nlp`)
  - raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを -1.0〜1.0 にスコアリングする処理フローを実装。
  - バッチ（最大 20 銘柄）で JSON Mode に送信し、429/ネットワーク/5xx に対して指数バックオフでリトライする仕組みを備える。
  - スコアは ±1.0 にクリップし、取得後 ai_scores テーブルへ置換的に書き込む（部分失敗時に既存スコアを守る設計）。
  - `score_news(conn, target_date, api_key=None)` を提供。API キーは引数または環境変数 `OPENAI_API_KEY` を使用。

- DB 初期化ユーティリティ
  - `init_monitoring_db(sqlite_conn)` を監視/実行スクリプトで使用して監視テーブルの存在を保証。

### Changed
- （初回リリースのため、既存実装からの変更履歴は無し。コード内にデフォルトや挙動に関する明示的設計選択あり）
  - 監視プロセスは環境に関わらず本番 sqlite_path を参照する旨をドキュメント化。

### Fixed
- （初回リリース: 明示的なバグ修正履歴は無し。実装には例外処理・ログ出力・Resource cleanup（finally での DB クローズ）など堅牢化のための対策が含まれる）

### Notes / Usage highlights
- 環境変数の自動読み込みはプロジェクトルート検出に .git または pyproject.toml を使用するため、配布後でも CWD に依存せず動作することを目指している。
- 監視ループのポーリング間隔は `MONITOR_POLL_INTERVAL`（秒）で上書き可能。無効値の場合はデフォルト 60 秒にフォールバックし logger.warning を出す。
- `run_execution.py` は paper_trading モード時に実口座データと完全に分離した DB（data/paper_trading.db）を使用する設計。
- `set_process_priority` / `set_cpu_affinity` は権限やプラットフォーム制約時に安全にスキップし、警告を出力する。
- ポートフォリオ構築・リスク制御・ポジションサイジングは設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照する想定で実装されている（コード内コメント参照）。
- Paper Trading 検証ツールは DB テーブル未存在時に OperationalError を捕捉してデフォルト値でレポートを作成する等、堅牢性を考慮している。

### Known limitations / TODOs（コード内コメントより）
- セクターエクスポージャー計算で価格（price）が欠損した場合、露出が過少見積りされる可能性がある点に関する TODO（前日終値や取得原価でのフォールバックの検討）。
- 単元株サイズ（lot_size）は現状共通の固定値 100 を想定。将来的には銘柄別 lot_size を導入する案あり。
- AI モジュールは OpenAI 呼び出しのレスポンスバリデーションや部分置換ロジックを記述しているが、実運用時は API レートやコストに留意する必要あり。

---

今後のリリースでは、テストカバレッジ（ユニット／統合）追加、API エラー耐性の強化、価格欠損時のフォールバック実装、銘柄別 lot_size 拡張、監視アラート出力（LINE 連携等）の実装などが想定されます。