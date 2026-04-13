# Changelog

すべての重要な変更はこのファイルに記録します。  
この CHANGELOG は「Keep a Changelog」の形式に準拠します。  
公開リリースはセマンティックバージョニングを使用します。

注: 本 CHANGELOG はリポジトリ内のコードから推測して作成したものであり、実際のコミット履歴を完全に反映するものではありません。

## [Unreleased]

## [0.1.0] - 2026-04-13

### Added
- 基本アプリケーション情報
  - パッケージバージョンを 0.1.0 として定義（kabusys.__version__）。

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサはコメント行・export 形式・クォート内エスケープ・インラインコメント処理に対応。
  - 必須環境変数取得用の _require() を提供（未設定時は ValueError）。
  - 各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）。
  - PAPER_FILL_MODE の入力検証（instant/partial/never/reject）と KABUSYS_ENV の検証（development/paper_trading/live）。
  - 複数のユーティリティフラグ（kill_flag_clear_on_start 等）や閾値設定 (CPU/MEM/DISK) を環境変数で設定可能。

- 実行・監視ランナー
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを提供。
    - KABUSYS_ENV が paper_trading の場合、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）と依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立て、ExecutionEngine を実行。
    - duckdb 接続を使用。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を "high" に設定し、例外発生時にもループ継続する安全策を実装。
    - 終了時に SQLite / DuckDB 接続を確実にクローズ。

- モニタリング DB 初期化
  - init_monitoring_db を呼び出して監視用テーブルの存在を冪等に保証（monitoring 側で common に利用）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 小）で選抜。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。全スコア 0 の場合は等配分にフォールバックし警告を出す。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有エクスポージャ計算、sell_codes を除外）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックし警告。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算、単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）でスケールダウン。コストバッファ（cost_buffer）による保守的見積もり、スケールダウン後の残余配分アルゴリズムを実装。
    - price が欠損または <= 0 の場合にスキップする動作や将来の拡張点（銘柄別 lot_size 等）を注記。

- 研究・ファクター（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を DuckDB 上で計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務を取得して PER/ROE を計算。
    - 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials を参照。
  - feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括クエリで取得。
    - calc_ic / rank: Spearman ランク相関（IC）計算とランク付けユーティリティ。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。
  - research.__init__ で主要関数を公開（zscore_normalize は外部モジュールからインポート）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news の記事を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄毎に ai_scores テーブルへ書き込む処理を実装。
  - 処理フロー:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）で記事を集計。
    - 1 銘柄あたり最大記事数・最大文字数を制限してトリム（トークン肥大化対策）。
    - 最大 20 銘柄ずつバッチで API 呼び出し（JSON Mode）、429 / ネットワーク断 / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証とスコアの ±1.0 クリッピング。
    - 部分失敗時に既存スコアを保護するため、対象コードのみを DELETE → INSERT 置換する方式を採用。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- ユーティリティ（kabusys.utils）
  - process_priority
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定。
    - Windows と POSIX (Linux, Darwin, FreeBSD) を吸収し、対応外 OS ではスキップして警告。
    - psutil による AccessDenied 等の例外をハンドルして安全にフォールバック。
    - set_cpu_affinity: 指定コア数への固定をサポート（検証・例外処理あり）。
  - utils パッケージエントリを用意。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポートを生成する CLI スクリプト（モジュールとしても利用可能）。
    - 検証指標:
      - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - CLI オプション: --from / --to / --db。
    - Pass/Fail 判定基準を定義（稼働率 >=99%、fill rate >=90%、send rate >=95%、P95 <=200ms 等）。
    - DuckDB/SQLite にテーブルがない場合でも安全に N/A を返す（OperationalError を捕捉）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の機密情報は環境変数経由で取り扱うように設計。自動 .env ロード時にも OS 環境変数は保護されるよう実装。

---

## 既知の制約・注意点（コード注釈より）
- apply_sector_cap: price が欠損（0.0）の場合、エクスポージャーが過小推定されてしまいブロックが解除される可能性あり。将来的に価格フォールバック（前日終値や取得原価）を導入する余地あり。
- position_sizing: lot_size は現状グローバル固定で 100 を想定。銘柄別の単位未対応（将来的改善予定）。
- DuckDB の一部操作（executemany 等）の挙動に依存する実装上の注意点がある（ai_news_nlp のコメント参照）。
- news_nlp: API 呼び出しの失敗はログを残して処理を継続するフェイルセーフ設計。ただし大量失敗時はスコア欠落が発生する。
- 設定の検証を積極的に行うため、環境変数の不正値は ValueError を送出する箇所がある（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。

---

変更点やバグ修正を加えた場合は、このファイルを更新してください。