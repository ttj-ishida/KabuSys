# Changelog

すべての重要な変更は「Keep a Changelog」仕様に従って記載しています。  
フォーマット: 変更のカテゴリ (Added, Changed, Fixed, Deprecated, Removed, Security)。

## [Unreleased]
（現在未リリースの変更はありません。）

## [0.1.0] - 初期リリース
リリース日: YYYY-MM-DD

### Added
- 基本パッケージと実行エントリポイントを追加
  - kabusys パッケージ本体を導入。パッケージバージョンは `__version__ = "0.1.0"`。
- 環境設定管理
  - `kabusys.config.Settings` を実装。.env ファイルの自動ロード（プロジェクトルート検出: .git または pyproject.toml）をサポート。
  - 読み込み順序: OS環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - `.env` パーサ実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いなどに対応。
  - 各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、環境種別判定、ログレベル、paper_trading 用設定等）を実装。値検証（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` の妥当性チェック）を追加。
- 実行・監視ランナー
  - run_execution: `src/kabusys/run_execution.py`
    - プロセス優先度設定（`set_process_priority("high")`）。
    - 環境に応じた SQLite パス分離: `paper_trading` 環境では `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - DuckDB 接続の初期化。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てとセッション実行。
    - RiskManager の既定設定値を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() を参照して初期化。
  - run_monitoring: `src/kabusys/run_monitoring.py`
    - プロセス優先度設定（High）。
    - 監視用ポーリングループ。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非整数）では警告を出してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する実装（監視データは本番 DB を参照する想定）。
    - 監視 DB テーブル初期化（`init_monitoring_db` を呼び出し冪等に保証）。
- ユーティリティ
  - `kabusys.utils.process_priority` を実装。Windows と POSIX（Linux/macOS/FreeBSD）両対応でプロセス優先度（nice / Windows priority class）を設定。CPU affinity を最初の N コアに固定する関数も実装。権限不足や未対応 OS の場合は警告を出してスキップするフェイルセーフあり。
- ポートフォリオ構築（純関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定（score 降順、signal_rank によるタイブレーク）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights、全スコア 0 の場合は等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限（apply_sector_cap）。既存保有のセクターエクスポージャ計算、上限超過セクターの新規候補除外。unknown セクターは上限適用除外。
    - 市場レジームに基づく投下資金乗数（calc_regime_multiplier）。"bull"/"neutral"/"bear" をサポート。未知のレジームは警告を出して 1.0 でフォールバック。
  - `kabusys.portfolio.position_sizing`
    - 発注株数計算ロジック（risk_based / equal / score をサポート）。損切り・許容リスク・単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリングと残差処理）を実装。手数料・スリッページ見積り用の cost_buffer に対応。
- リサーチ / ファクター計算
  - `kabusys.research.factor_research`
    - DuckDB（prices_daily, raw_financials テーブル）を用いたファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、MA200乖離（ウィンドウ不足時は None）。
      - calc_volatility: ATR20、ATR百分率、20日平均売買代金、出来高比率（NULL の扱いに配慮）。
      - calc_value: raw_financials から最新の財務情報を取得して PER / ROE を計算。
    - DuckDB のウィンドウ関数を用いた効率的な実装。スキャン範囲にバッファを設けて週末祝日を吸収。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ランキング関数（rank）、ファクター統計サマリー（factor_summary）。外部ライブラリに依存せず純 Python 実装。
- AI / ニュース NLP
  - `kabusys.ai.news_nlp` を追加。raw_news, news_symbols, ai_scores テーブルを参照し、OpenAI API（gpt-4o-mini）を用いて銘柄別センチメントスコアを生成・保存する処理を実装。
    - タイムウィンドウ計算（JST ベース）: 前日 15:00 JST ～ 当日 08:30 JST に相当する UTC 範囲を正確に計算。
    - 銘柄ごとに記事を集約してトリミング（最大記事数 / 最大文字数制限）。
    - 最大 20 銘柄ずつバッチ送信（_BATCH_SIZE=20）。JSON Mode を期待するプロンプト（SYSTEM_PROMPT）を設定。
    - 429 / ネットワーク/タイムアウト / 5xx に対する指数バックオフリトライ、レスポンスバリデーション、結果の ±1.0 クリップ、部分成功時の DB 操作保護（対象コード絞り込みで DELETE/INSERT を行う設計）。
    - API キー未指定時の明示的なエラー（ValueError）。
- ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading DB（デフォルト data/paper_trading.db）を読み込み、稼働率・注文成功率・送信率・リスク却下数・レイテンシ（avg/max/P95）などの指標を集計して CLI レポートを生成。
    - CLI 引数: --from, --to, --db（DB パスは引数 > 環境変数 > デフォルトの優先順）。
    - 指標閾値（Pass/Fail 判定）を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - テーブルが存在しない場合に sqlite3.OperationalError を捕捉して安全にデフォルト値を使うハンドリングを実装。
    - P95 計算、NULL 値の扱い、表示フォーマット関数を実装。
- DB 初期化ユーティリティ
  - `init_monitoring_db` を呼び出して監視用テーブルの存在を保証するフロー（冪等）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` から取得し、未設定時は明示的にエラーとすることで誤動作を抑止。

---

注記:
- 多くの関数は「外部副作用を持たない純関数」あるいは「DB 接続 / duckdb 接続を外から受け取る設計」となっており、テスト容易性を意図した実装になっています。
- 一部に TODO コメントや将来拡張の注記（例: 銘柄別 lot_size、価格フォールバック等）が含まれており、将来的な改善ポイントが明記されています。

（必要であれば、各ファイルごとの細かい変更点や実装の設計意図を追記します。）