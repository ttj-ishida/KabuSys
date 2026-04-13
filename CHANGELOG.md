# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠しています。重要な変更点・追加機能・仕様について、コードベースから推測してまとめています。

最新版: Unreleased

## [Unreleased]

### Added
- 全体
  - 初期パッケージ構成を追加。モジュール群（config / utils / portfolio / research / execution / monitoring / tools / ai 等）を実装。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 設定管理（kabusys.config）
  - .env 自動ロード機能を追加。プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を読み込む。
  - 読み込み時の優先順位: OS環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサを追加し、以下の形式に対応:
    - `export KEY=val` 形式
    - シングル/ダブルクォートで囲まれた値（バックスラッシュエスケープ対応）
    - クォート無しの行でのインラインコメント処理（直前がスペース/タブの場合）
  - 環境設定を取得する Settings クラスを実装。以下の設定値をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（検証あり）
    - PAPER_FILL_MODE（paper trading 用の fill モード検証とバリデーション）
  - 環境変数未設定時に ValueError を送出する `_require()` を導入（必須設定の明示化）。

- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite を使用（`PAPER_TRADING_SQLITE_PATH`、data/paper_trading.db がデフォルト）し、MockBroker（broker_factory 経由）で本番 DB と完全に分離する設計。
    - ExecutionEngine の組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）を行い、セッションを実行。
    - 起動時に監視テーブルの初期化（init_monitoring_db）を行い冪等性を確保。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視は環境にかかわらず本番の sqlite_path を使用する仕様（監視 DB は常に本番 DB に記録する設計）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）。不正な値（0以下や非整数）はデフォルトへフォールバックし、警告ログを出力。
    - DuckDB 接続を並行して確立し、SystemMonitor.check_once() を定期実行。例外はログに残して次ポーリングへ継続。

- 監視・モニタリング
  - monitoring_db 初期化ユーティリティを利用して監視テーブルを保証（init_monitoring_db）。
  - SystemMonitor（監視実装）を起動するためのランナーを用意（run_monitoring.py）。

- ユーティリティ（kabusys.utils）
  - process_priority モジュールを追加:
    - set_process_priority(level): Windows / POSIX に差分吸収してプロセス優先度を設定（"high"|"normal"|"low"）。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を固定するユーティリティ。
    - 例外（権限不足等）発生時は警告を出してスキップするフェイルセーフ設計。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順 + signal_rank タイブレークで選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア正規化配分（スコア合計が 0 の場合は等分配にフォールバックして警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比を計算し、上限を超えるセクターの新規候補を除外）。`sell_codes` を指定して当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未定義値は 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数計算（allocation_method: "risk_based" / "equal" / "score"）。
    - lot_size（単元）丸め、per-stock 上限、aggregate cap（available_cash を超えた場合のスケールダウン）、cost_buffer（手数料/スリッページ見積り）を考慮した配分ロジックを実装。
    - risk_based: 許容リスク率、stop_loss_pct を用いた株数算出。
    - スケーリング時の分配は残差（fraction）に基づいて lot 単位で再配分する安定化ロジックを採用。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1m/3m/6m リターン、200 日移動平均乖離（ma200_dev）を DuckDB の prices_daily を用いて計算。
    - calc_volatility: 20 日 ATR（true_range の扱いを明示）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials からの最新財務データと prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新レコードを取得）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズンをサポート）を一度のクエリで取得。horizons の検証（正の整数かつ <=252）を実装。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（同順位の平均ランク対応、3 レコード未満は None）。
    - rank / factor_summary: ランク付け（同順位平均ランク）と基本統計量（count/mean/std/min/max/median）を計算するユーティリティを追加。
  - research パッケージは外部依存（pandas 等）を使わず DuckDB + 標準ライブラリで完結する設計。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書き込む処理を実装（score_news）。
  - 機能概観:
    - ニュース時間ウィンドウ計算（target_date を基準に JST 前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - 記事を銘柄ごとに集約（最大記事数・最大文字数でトリム）。
    - 最大 20 銘柄単位でバッチ API 呼び出し。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフのリトライ（上限 _MAX_RETRIES）。
    - レスポンス検証（JSON structure, known codes, numeric score）、スコアを ±1.0 にクリップ。
    - 成功した銘柄のみ ai_scores に置換的に書き込むことで部分失敗時のデータ保護を実現。
  - OpenAI クライアント生成時に api_key の解決（引数 > 環境変数 OPENAI_API_KEY）。未設定時は ValueError。

- コマンドラインツール（kabusys.tools）
  - paper_verification_report:
    - Paper Trading の検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - オプション: --from, --to（YYYY-MM-DD）, --db（SQLite DB パス）。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 指標:
      - 稼働率（uptime）閾値: 99.0%
      - 注文成功率（fill_rate）閾値: 90.0%
      - 送信率（send_rate）閾値: 95.0%
      - P95 レイテンシ閾値: 200 ms
    - レポートは system_status / trade_logs / risk_logs から集計し、P95 は全レコードを取得して計算。データ不足時には N/A を表示し、Fail/Pass 判定を出力。

### Changed
- DB 開放/接続
  - run_monitoring と run_execution が DuckDB と SQLite の両方への接続を確立し、処理終了時に確実にクローズするように変更（finally ブロックで close）。
- 監視動作
  - run_monitoring は監視用 DB 初期化を保証しつつ、環境に依存せず本番 sqlite_path を使う方針に変更。
- ロギング
  - 起動時に logging.basicConfig(level=logging.INFO) を設定してデフォルトログレベルを INFO に統一。
- 環境変数の検証
  - Settings による各種環境変数のバリデーションを追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。不正値は ValueError を送出して早期検出。

### Fixed
- .env 読み込みの例外ハンドリングを改善（ファイルオープン失敗時に warnings.warn）。
- process_priority / set_cpu_affinity の権限エラーや未対応プラットフォームでの挙動を例外キャッチし、警告を出して安全にスキップするように修正。

### Notes / Migration
- 新規導入の環境変数（主なもの）:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。不正な値は無視されデフォルト 60 秒が使われる。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化するフラグ（"1" で無効化）。
  - PAPER_FILL_MODE: paper_trading 用のモック約定モード（instant/partial/never/reject のうちのいずれかを指定）。
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite ファイルパス（デフォルト: data/paper_trading.db）。
  - OPENAI_API_KEY: OpenAI API 利用キー（news_nlp で必須）。
  - KABUSYS_ENV: 環境指定（development / paper_trading / live）。不正値は起動時に拒否されるので注意。
  - LOG_LEVEL: 文字列でログレベル指定（DEBUG/INFO/...）。不正値は ValueError。
- paper_trading の分離:
  - paper_trading 実行時は本番 sqlite を上書きせず専用 DB を使うため、paper_trading データは本番データと完全に分離されます。既存ワークフローをマイグレーションする際は PAPER_TRADING_SQLITE_PATH の確認を推奨します。
- AI ニュース機能:
  - OpenAI API 利用に伴うコストやレート制限に注意。score_news はバッチ・リトライ・部分失敗保護を実装しているが、APIキー・プロンプト・レスポンス仕様は運用要件に応じて確認してください。
- DuckDB クエリ:
  - research / factor モジュールは DuckDB のテーブル構成（prices_daily, raw_financials 等）に依存します。スキーマが変わるとクエリが失敗するため、スキーマ互換性に注意してください。

---

（上記はコードベースから推測して作成した CHANGELOG です。実際のリリース履歴や追加の変更がある場合は適宜更新してください。）