# Changelog

すべての注目すべき変更をこのファイルに記載します。
フォーマットは「Keep a Changelog」の慣習に準拠しています。

※以下の履歴はコードベースの内容から推測して作成しています。

## Unreleased
- ドキュメント・補足:
  - 内部実装や既知の動作（.env 自動ロードの挙動、デフォルト値、フォールバック動作など）を CHANGELOG に反映しました。

## [0.1.0] - 2026-04-13
初期リリース。以下の主要機能・モジュールを追加。

### Added
- 実行 / 監視関連スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを提供。
    - 環境変数 KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite DB を使用し、MockBrokerClient を利用する（本番 DB と分離）。
    - 起動時にプロセス優先度を "high" に設定する仕組みを組み込み。
    - 実行に必要な依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の組み立てとセッション実行処理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバック）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視は常に本番 DB を参照）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - kabusys.config.Settings
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。OS 環境変数は保護され、.env.local は .env を上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 必須環境変数取得ヘルパー _require()。JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須列挙。
    - 各種設定プロパティを提供（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/Memory/Disk 閾値、env / log_level の検証など）。
    - PAPER_FILL_MODE の検証（有効値: "instant", "partial", "never", "reject"）および PAPER_TRADING_SQLITE_PATH のデフォルト。
    - env 値は "development" / "paper_trading" / "live" のみ許容。

- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート（score 降順、同点は signal_rank 昇順）と上位選抜。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等金額にフォールバックし WARNING を出力）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限。既存保有比率が閾値を超えるセクターの候補を除外。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム（"bull","neutral","bear"）に応じた投資乗数（未知レジームは警告を出し 1.0 でフォールバック）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based","equal","score"）に応じた発注株数計算。単元株（lot_size）で丸め、position 上限・aggregate cap（available_cash）を考慮してスケーリング。cost_buffer を用いた保守的コスト見積りと残差処理ロジックを実装。

- 研究（Research）モジュール（DuckDB ベース）
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算（prices_daily を参照）。
    - calc_volatility: ATR(20)、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）計算。入力検証あり（horizons は正の整数かつ <=252）。
    - calc_ic / rank / factor_summary: IC（Spearman）計算、ランク付け（同順位は平均ランク）、ファクター統計要約（count/mean/std/min/max/median）を提供。
  - いずれも DuckDB 接続を受け取り、DB 外部 API に依存しない設計。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用検証レポートを生成する CLI スクリプト（python -m kabusys.tools.paper_verification_report）。
    - PAPER_TRADING_SQLITE_PATH / --db で DB を指定可能（デフォルト: data/paper_trading.db）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数など。閾値を定義して PASS/FAIL 判定を出力。
    - DB 内のテーブルが存在しない場合は安全に N/A を出力するフェイルセーフ実装。
    - P95 計算、日付フィルタ生成、出力整形を含む。

- AI ニュース NLP
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し、ai_scores テーブルへ書き込む処理（score_news）。
    - バッチサイズ（_BATCH_SIZE=20）、文字数/記事上限、レスポンス検証、スコアの ±1.0 クリップ、エクスポネンシャルバックオフを用いたリトライ実装の方針を実装。
    - ニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算するユーティリティ calc_news_window。
    - API キー未設定時は ValueError を送出し、部分失敗時にも他銘柄スコアを保護するための DB 書き込み戦略（対象コードのみ置換）を想定。

- ユーティリティ
  - kabusys.utils.process_priority
    - クロスプラットフォームでプロセス優先度設定（Windows 用定数 / POSIX の nice 値を吸収）。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足等で失敗した場合は警告して処理をスキップする安全化。

- パッケージメタ情報
  - kabusys.__init__.py に __version__="0.1.0" を追加。

### Changed
- 設計方針（全体）
  - 多くのコンポーネントは「DB 参照のみ」「外部取引 API にアクセスしない」「純粋関数で副作用を持たない」など安全性・テスト容易性を考慮した実装方針が採用されている点を明確化。
  - 各所でデフォルト値と入力検証（env 値や関数引数の検査）を追加し、想定外の値に対してフォールバックまたは例外を投げるようにした。

### Fixed
- フォールバック・耐障害性の強化
  - MONITOR_POLL_INTERVAL の不正値や 0 以下を検出してデフォルトにフォールバックする処理を追加。
  - .env 読み込み失敗時（ファイル読み取りエラー）に警告を出して継続するように変更。
  - DuckDB / SQLite クエリでテーブルが存在しない場合に発生する sqlite3.OperationalError をキャッチしてフェイルセーフなデフォルトを返す（paper_verification_report）。

### Security
- 環境変数の保護
  - .env 自動ロード時に既存の OS 環境変数を保護する仕組みを実装（protected set）。
  - OPENAI / API トークン等は直接コードに埋め込まず環境変数での提供を想定。未設定時は明示的なエラーを出す。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。未設定時は起動時に ValueError が発生します。
- 環境名:
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれかに設定してください。
- DB パス:
  - デフォルトの duckdb は data/kabusys.duckdb、監視用 sqlite は data/monitoring.db、paper_trading のデフォルト sqlite は data/paper_trading.db です。必要に応じて環境変数で上書きしてください。
- .env 自動ロード:
  - プロジェクトルートが検出できない場合は自動ロードをスキップします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

今後の予定（推定）
- ExecutionEngine / Monitoring の運用時ログ強化、より詳細なメトリクス収集。
- AI スコア周りのバッチ失敗時リトライ戦略・監査ログの拡充。
- 銘柄ごとの lot_size をマスタ管理する拡張（position_sizing の TODO に記載）。

（以上）