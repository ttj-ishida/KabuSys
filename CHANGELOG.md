CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

Unreleased
----------
（なし）

0.1.0 - 2026-04-13
-----------------
初回リリース。以下の主要機能・モジュールを追加しました。

Added
- 基本パッケージ
  - kabusys パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - モジュール群をエクスポートするための __all__ を定義。

- 設定管理（kabusys.config）
  - プロジェクトルート探索機能を導入（.git または pyproject.toml を基準）。
  - .env / .env.local の自動ロードを実装（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサを実装（export プレフィックス、クォート/エスケープ対応、インラインコメント処理）。
  - Settings クラスを追加し、環境変数をプロパティとして型変換・検証して提供。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）
    - API トークン（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）
    - PAPER_FILL_MODE バリデーション（instant/partial/never/reject）
    - 監視関連設定（PID ファイル・kill flag・閾値）
    - 環境種別検証（development / paper_trading / live）
    - LOG_LEVEL 検証

- 実行・監視起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite を使用して本番と分離。
    - BrokerClientFactory 経由でブローカークライアントを作成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を実行。
    - duckdb 接続を利用（分析用 DB）。
    - 起動時にプロセス優先度を 'high' に設定。
    - 監視テーブル初期化（init_monitoring_db）の呼び出しにより冪等に監視テーブルを保証。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 監視処理は常に本番 sqlite_path を使用する仕様。
    - プロセス優先度を 'high' に設定、SQLite / DuckDB 接続の初期化とクリーンアップを実装。
    - KeyboardInterrupt による優雅な終了処理。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を実装（Windows / POSIX の差分を吸収）。
  - set_cpu_affinity(cpu_count) を実装（最初の N コアへ固定、エラー時は警告でスキップ）。
  - アクセス権限や未対応 OS のケースはログ警告でフォールバック。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのソート（スコア降順、同点は signal_rank 昇順）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計 0 の場合は等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックの実装（売却予定銘柄除外等を考慮）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を提供（未知はフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料/スリッページ見積り）を考慮。
    - 欠損価格の扱いに関する注意点とログ出力。

- 研究・リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率（データ状況に応じて None を返す）。
    - calc_value: raw_financials から直近財務情報を取得して PER/ROE を算出。
    - DuckDB を用いた SQL ベースの実装。計算範囲にバッファを設定し週末祝日を吸収。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。
    - calc_ic / rank: スピアマン（ランク）相関（IC）計算、ランク付け（同順位は平均ランク）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - research パッケージから zscore_normalize を含む必要な関数をエクスポート。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から OpenAI（gpt-4o-mini）を利用して銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込み。
  - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を定義して記事を集約。
  - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装（最大リトライ回数設定）。
  - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の DB 保護（影響コードのみ更新）などのフェイルセーフ設計。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

- ツール
  - paper_verification_report.py
    - Paper Trading DB（デフォルト data/paper_trading.db）を読み込み、稼働率・注文成功率・送信率・レイテンシ等の検証レポートを生成。
    - P95 レイテンシ計算、複数テーブル（system_status, trade_logs, risk_logs）から指標取得。DB テーブルが存在しない場合のフォールバック処理を実装。
    - CLI 引数 --from / --to / --db をサポート。
    - 合否基準（稼働率 / 成功率 / 送信率 / P95）を定義し PASS/FAIL 判定を出力。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キー等の機密値は環境変数経由で扱う設計を採用。
- .env 自動ロードにおいて OS 環境変数を保護するために protected セットを導入（上書き制御）。

Notes / Implementation details
- DuckDB と SQLite を併用：DuckDB は主に価格・ファクター計算・AI 集計に使用、SQLite はモニタリング・発注ログ・paper_trading 用 DB に利用。
- paper_trading 環境は本番 DB と分離される（PAPER_TRADING_SQLITE_PATH / Settings.is_paper を使用）。
- 複数箇所で入力値のバリデーションや No-data の扱い（None を返す）に配慮しており、運用中の例外がシステム全体を停止させない設計。
- ロギングは各モジュールで logger を取得して情報・デバッグ・警告を出力するように実装。

Breaking Changes
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Acknowledgements / References
- 各モジュール内ドキュメント（関数 docstring）に実装方針や外部参照（PortfolioConstruction.md、StrategyModel.md 等）が記載されています。運用・拡張時はそちらを参照してください。