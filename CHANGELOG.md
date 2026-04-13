# Changelog

すべての重要な変更は Keep a Changelog 準拠で記載します。  
最新の開発ブランチは Unreleased、リリース済みは下に列挙しています。

タグ付け規則: MAJOR.MINOR.PATCH

## [Unreleased]
- なし

## [0.1.0] - 2026-04-13
初回リリース。自動売買システム KabuSys の基本コンポーネントを実装しました。主な追加点は以下のとおりです。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py の `__version__ = "0.1.0"` で定義。

- 環境/設定管理
  - src/kabusys/config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）による .env 自動ロード機能を実装。
    - .env/.env.local ファイルの読み込み（export 形式、クォート文字列、インラインコメント処理等を考慮したパーサ実装）。
    - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 必須環境変数取得ヘルパー `_require()` と、各種設定プロパティ（DB パス、API トークン、PID/kill フラグ、閾値、環境種別判定 etc.）。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）、KABUSYS_ENV / LOG_LEVEL のバリデーション。

- 実行エントリポイント
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - 起動時にプロセス優先度を高 (high) に設定。
    - 環境に応じて本番 DB と paper_trading 用の DB を分離（KABUSYS_ENV=paper_trading では paper_sqlite_path を使用）。
    - BrokerClientFactory 経由でブローカークライアントを生成。OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - duckdb と sqlite の接続管理、監視テーブル初期化（冪等）を実施。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下など）はデフォルトにフォールバックして警告を出力。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用して実行。
    - 起動時にプロセス優先度を high に設定。

- 監視 DB 初期化ユーティリティ
  - src/kabusys/monitoring/monitoring_db.py（インポート参照あり）を利用して監視テーブルの存在保証を行う（init_monitoring_db を通じて冪等に初期化）。

- プロセス制御ユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティ (`set_process_priority`)。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を実装。
    - アクセス権限不足や未サポート API でも安全にスキップし、ログで通知。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順・タイブレーク）`select_candidates`。
    - 等配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合は等配分へフォールバック）。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap`（売却予定銘柄の除外、unknown セクターは上限除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear のマップ、未知レジームは警告と 1.0 フォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - 発注株数計算 `calc_position_sizes`（risk_based / equal / score 方式対応）。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer（スリッページ・手数料見積）等を考慮した実装。
    - 利用可能現金を超える場合のスケールダウンと残差配分（lot 単位での再配分ロジック）を実装。

  - パッケージエクスポート: src/kabusys/portfolio/__init__.py により主要関数を公開。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照）。
    - mom_1m/3m/6m、MA200 乖離、ATR20、20日平均売買代金、volume_ratio、PER・ROE などを計算。
    - 欠損データや窓サイズ未満の扱いを明示。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）`calc_forward_returns`。
    - Spearman ランク相関による IC 計算 `calc_ic`、ランク付けユーティリティ `rank`。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。

  - パッケージエクスポート: src/kabusys/research/__init__.py で主要関数と zscore_normalize を公開。

- AI ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントスコアを生成し ai_scores テーブルへ書き込む機能。
    - バッチサイズ、最大記事数・最大文字数トリム、ニュース収集ウィンドウ（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を実装。
    - API 呼び出しは JSON Mode 期待、レスポンス検証、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx 系は指数バックオフでリトライ（上限あり）。
    - OpenAI API キー未設定時は例外を投げる（明示的エラーメッセージ）。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB の検証レポートを生成する CLI スクリプト（コマンドライン引数 --from/--to/--db をサポート）。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ組立、DB 存在チェック、テーブル欠落時のフォールバック（OperationalError 捕捉）を実装。
    - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH による上書き可能）。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Notes / Usage highlights
- run_monitoring/run_execution 起動時にプロセス優先度を high に設定するため、実行環境によっては権限不足で警告が出る場合があります（その場合は設定はスキップされる）。
- Paper Trading は本番 DB と完全分離しているため、投入テストや検証を行う際は KABUSYS_ENV=paper_trading と PAPER_TRADING_SQLITE_PATH を利用してください。
- .env の自動読込はデフォルトで有効（プロジェクトルート検出に失敗した場合はスキップ）。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API を使う機能は API キー設定が必須です（環境変数 OPENAI_API_KEY または関数引数で渡す）。

---

今後のリリースでは以下の点を予定しています:
- Strategy / Execution コンポーネントの詳細な単体テストと統合テスト
- 銘柄別 lot_size をサポートする拡張（stocks マスタの導入）
- monitoring / ai scoring の監視・リトライ改善やメトリクス公開

（必要であれば個別のモジュールごとにもっと詳細な変更点を追記します）