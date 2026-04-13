# CHANGELOG

すべての重要な変更は Keep a Changelog 準拠で記載します。  
このファイルはコードベース（現状バージョン: 0.1.0）の機能・実装内容をソースコードから推測してまとめた初期リリース向けの変更履歴です。

最新更新: 2026-04-13

## [Unreleased]
- （今後の変更履歴をここに記載）

## [0.1.0] - 2026-04-13
初回公開リリース。システム全体のコア機能（実行・監視・ポートフォリオ構築・ファクター研究・ニュースNLP・ユーティリティ・ツール）を実装。

### Added
- 全体
  - パッケージ基本情報を追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB と SQLite を併用するデータアクセス基盤を導入（duckdb, sqlite3 を利用）。

- 実行 / スケジューラ
  - run_execution.py: 実売買（live）/ペーパートレード（paper_trading）に応じた実行スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせ ExecutionEngine を実行する起動フローを提供。
    - ExecutionEngine 起動前にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバックして警告出力。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計（監視データは共通に記録）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定 / 環境変数管理
  - kabusys.config.Settings を導入し、.env / .env.local / OS 環境変数からの設定取得を統合。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づいて .env ファイルを読み込む。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 形式、引用符（シングル／ダブル）、エスケープ、インラインコメントを考慮した堅牢な実装を提供。
    - 必須環境変数未設定時の明示的エラー（_require）を実装。
    - 各種設定プロパティを提供（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, PAPER_FILL_MODE 検証、PID/KILL フラグパス、しきい値系設定、環境判定ヘルパ等）。

- 監視 / モニタリング
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を起動スクリプトで呼び出し、監視テーブルの存在保証を組み込み。
  - SystemMonitor（監視ロジック本体）との連携を想定した起動/ループ制御を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのソート/上位選出（スコア降順、タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア比率配分（スコア全0時は等分にフォールバック、警告出力）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限の適用（既存ポジションのセクター別エクスポージャ計算、売却予定銘柄の除外、"unknown" セクターの扱い）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知のレジームはフォールバックで 1.0）。
  - portfolio.position_sizing:
    - calc_position_sizes: 重み・候補リスト・利用可能現金等から発注株数を算出。risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）、最大ポジション上限、max_utilization、cost_buffer を考慮したスケーリング（aggregate cap の縮小と残余配分ロジック）を実装。
    - 価格欠損等のケースに対するデバッグログとスキップ処理。

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB 上で計算。
    - calc_volatility: 20日 ATR（true_range の正しい NULL 伝搬考慮）、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算。
    - 各関数はデータ不足時に None を返すことで堅牢性を確保。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト: [1,5,21]）で将来リターンを計算（複数ホライズンを1クエリで取得）。
    - calc_ic / rank / factor_summary: スピアマン順位相関（IC）計算、ランク化ユーティリティ、カラム別統計サマリを標準ライブラリのみで実装。小サンプル時の None フェールセーフあり。

- AI / ニュース NLP
  - ai.news_nlp:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込む処理を実装。
    - ニュース対象ウィンドウの計算（JST 基準前日 15:00 ～ 当日 08:30、内部は UTC naive datetime で扱う）を提供。
    - バッチ処理（最大 20 銘柄／API 呼び出し）、トークン肥大対策（記事数最大・文字数トリム）を実装。
    - API エラー（429・ネットワーク・5xx・タイムアウト）に対する指数バックオフ付きリトライ、レスポンスの厳格なバリデーション、スコアの ±1.0 クリッピング、部分失敗時の既存スコア保護（対象コードを限定して DELETE/INSERT）など、フェイルセーフ設計。
    - OPENAI_API_KEY の未設定時は明示的な ValueError を送出。

- ツール
  - tools.paper_verification_report:
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計して PASS/FAIL 判定を行う CLI レポートを実装。
    - デフォルトしきい値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - 日付フィルタ (--from / --to) と --db オプションをサポート。DB が存在しない場合の明示的エラーメッセージ。

- ユーティリティ
  - utils.process_priority:
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値で設定）。
    - CPU affinity を最初 N コアに固定するヘルパを追加（スレッド数チェック、アクセス拒否等はログでスキップ）。
    - アクセス拒否や未対応機能のフォールバックロギングを実装。
  - utils.__init__ を追加（パッケージ化のための初期化）。

- パッケージエクスポート
  - portfolio / research モジュールの public API を __init__ でエクスポートし、上位コードからの利用を容易に。

### Changed
- 起動時のプロセス優先度設定をデフォルトで "high" にすることで、実行・監視プロセスの優先度を上げる運用前提に変更（run_execution, run_monitoring）。
- .env 読み込みの優先順位を OS 環境変数 > .env.local > .env に明確化。OS 環境変数は保護され、.env.local は上書き可能。

### Fixed
- .env パーサを改良し、引用符内のエスケープ処理、export プレフィックス、インラインコメント判定の改善で意図しない解析エラーを低減。
- DuckDB への executemany 前に空パラメータの確認を想定した注釈（DuckDB 0.10 の制約）をコメントとして残し、部分失敗時のデータ保護を設計上実施（ai.news_nlp の書き込み戦略）。

### Security
- OpenAI API キーの取り扱いは環境変数または明示的引数で解決し、未設定時には例外を出すことで誤動作を防止。
- .env 自動ロードは必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings 経由で必須取得される（未設定だと ValueError）。
  - OPENAI_API_KEY は ai.news_nlp.score_news を使う場合に必須。
- データベース:
  - デフォルトの DuckDB パス: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）。
  - 監視用 sqlite: data/monitoring.db（SQLITE_PATH で上書き可）。run_monitoring は環境に関わらず sqlite_path を使用。
  - ペーパートレード sqlite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。run_execution は paper_trading 環境でこれを使用。
- 実行時:
  - MONITOR_POLL_INTERVAL に 1 以上の整数を指定して監視間隔を変更可能。0 以下・非整数は無視されデフォルト 60 秒にフォールバック。
  - PID / KILL フラグ用のファイルパスは Settings 経由で設定可能（PID_FILE_PATH, KILL_FLAG_PATH 等）。
- 設計上の留意点:
  - price が欠損（0.0）の場合、セクターエクスポージャや position sizing の見積りが過少となる恐れがあり、将来的に価格のフォールバック（前日終値や取得原価）を導入する余地がある。
  - calc_regime_multiplier の bear=0.3 は追加のセーフガードであり、generate_signals が bear 時に BUY を生成しない設計と組み合わせて動作する前提。

---

変更履歴に不明点・追記希望があれば、対象ファイル名や期待するフォーマット（例: 以降のバージョン運用方針）を指定してください。