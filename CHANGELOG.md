# Changelog

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

- なし

## [0.1.0] - 初回リリース (初期実装)

最初の安定実装。システム監視・実行エンジン・ポートフォリオ構築・リサーチ・AIニューススコアリング・ツール群を含むフルスタックな自動売買支援ライブラリを提供します。

### 追加 (Added)

- パッケージ基本情報
  - kabusys パッケージを追加。バージョン __version__ = "0.1.0" を定義。

- 設定管理 (src/kabusys/config.py)
  - Settings クラスを追加し、環境変数経由で各種設定を取得する統一 API を提供。
  - 自動 .env ロード機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順序: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env 行パーサー（クォート・エスケープ・コメント対応）を実装。
  - 多数の設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値など）。
  - 設定値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。不正値時は ValueError を送出。

- プロセス制御ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) により OS を吸収してプロセス優先度（high/normal/low）を設定。
  - set_cpu_affinity(cpu_count) によりプロセスを指定コア数に固定（未指定は何もしない）。
  - サポート外 OS や権限不足時は警告ログを出して安全にスキップ。

- 実行エントリ (src/kabusys/run_execution.py)
  - ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成を想定。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
  - プロセス優先度を最初に "high" に設定。
  - duckdb 接続の利用（DuckDB を分析用 DB として使用）。

- 監視エントリ (src/kabusys/run_monitoring.py)
  - SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
  - 監視用 DB は環境に関係なく本番 sqlite_path を使用する設計。
  - monitor.check_once() の例外はキャッチしてログ出力し、次ポーリングへ継続（フェイルセーフ）。
  - KeyboardInterrupt による正常終了処理、DB 接続クローズを保証。

- 監視 DB 初期化フック
  - init_monitoring_db(sqlite_conn) を呼び出して監視用テーブルが存在することを冪等に保証（run_execution/run_monitoring で利用）。

- ポートフォリオ構成 (src/kabusys/portfolio/)
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・タイブレークロジックで選択。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコア0 の場合は等配分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限を評価し、上限超過セクターの新規候補を除外（"unknown" セクターは上限適用しない）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear。また未知は 1.0 でフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。lot_size（単元）丸め、per-position/max aggregate cap、cost_buffer を考慮したスケーリング（残差処理ロジック含む）。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算する実装（最新財務レコードの取得）。
    - 全関数は DuckDB 接続を受け取り SQL ベースで高性能に実行。
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得（入力検証、最大ホライズン上限 252）。
    - calc_ic: スピアマンランク相関（IC）を実装（最低有効レコード数 3）。
    - rank / factor_summary: ランク化・統計サマリー（count/mean/std/min/max/median）。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約し OpenAI API (gpt-4o-mini) を用いて銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を追加。
  - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（最大記事数・最大文字数）、JSON モードによる厳密なレスポンス想定。
  - リトライ戦略（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）。
  - calc_news_window: ターゲット日のニュース収集ウィンドウ（JST 基準 → UTC 変換）を提供。
  - API キー未設定時は ValueError を送出。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status, trade_logs, risk_logs からシステム稼働率・注文成功率・送信率・レイテンシ指標を集計。
    - P95 計算、各指標に対する Pass/Fail 基準を実装（稼働率 99.0%, 成功率 90.0% など）。
    - コマンドライン引数 --from/--to/--db に対応。PAPER_TRADING_SQLITE_PATH 環境変数を使用可能。
    - DB 存在チェック・OperationalError の安全ハンドリングを実装。

### 変更 (Changed)

- なし（初回リリース）

### 修正 (Fixed)

- なし（初回リリース）

### 注意点 / 実装上の制約 (Notes)

- .env パーサーは複数のケース（export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント）に対応しているが、完全な dotenv 互換性を目指すものではない点に留意。
- apply_sector_cap は "unknown" セクターの既存保有を計算から除外するため、銘柄の sector_map が不完全な場合は意図せずブロックが緩くなる可能性がある（将来的に価格フォールバック等の改善をコメントで示唆）。
- position_sizing の aggregate スケーリングでは lot_size 単位で再配分するロジックを採用（端数処理のための remainder ソートを利用）。
- ai/news_nlp のスコア付与は OpenAI API に依存するため、API の利用制限・費用に留意。API キーは env か明示的引数で提供する必要あり。
- run_monitoring/run_execution は起動時にプロセス優先度を "high" に設定しようとする（権限不足時は警告ログを出してスキップ）。

### セキュリティ (Security)

- なし

---

作成日: 2026-04-12
（この CHANGELOG は現在のコードベースから推測して生成しています。実際のリリース履歴に合わせて適宜編集してください。）