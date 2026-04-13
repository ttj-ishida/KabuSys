CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。  
日付はコードベースの構成から推測して付与しています。

Unreleased
----------

- （今後の変更点をここに追記）

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリースを追加。KabuSys のコア機能群を含む。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告ログを出力。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を参照して DB に接続する設計。
    - 起動時にプロセス優先度を "high" に設定する処理を導入。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全分離。
    - ブローカークライアントのファクトリ経由で実クライアント / モックを切り替え可能。
    - ExecutionEngine 起動前に OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、実行セッションを開始。
    - 起動時にプロセス優先度を "high" に設定する処理を導入。

- 設定管理
  - config.py
    - 環境変数・.env ファイル読み込みロジックを実装（.env / .env.local、OS 環境変数優先、.env.local は上書き）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索するため CWD に依存しない実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、クォート文字・バックスラッシュエスケープ、インラインコメント処理等に対応。
    - Settings クラスを提供し、各種設定プロパティを型変換・バリデーション付きで取得可能（DB パス、PID ファイルパス、閾値、env の検証等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV の有効値検査（development/paper_trading/live）を実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレーク処理）select_candidates を追加。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（スコア全てが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有エクスポージャー算出、sell_codes を除外、"unknown" セクターは上限除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - 単銘柄・総合の上限や lot_size を考慮した株数決定 calc_position_sizes を実装（risk_based / equal / score の振る舞い、aggregate cap のスケール調整、cost_buffer の考慮、端数処理の再配分ロジックを含む）。

- リサーチ機能
  - research/factor_research.py
    - モメンタム（mom_1m/3m/6m・ma200乖離）calc_momentum を実装（DuckDB を用いた SQL 実装）。
    - ボラティリティ / 流動性（ATR20、ATR 比、20日平均売買代金、出来高比）calc_volatility を実装。
    - バリュー（PER, ROE）calc_value を実装（raw_financials と prices_daily の組合せ）。
    - 各関数はデータ不足時に安全に None を返す設計。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（可変ホライズン、入力検証付き）を実装。
    - スピアマンランク相関（IC）calc_ic、ランク化ユーティリティ rank を実装。
    - factor_summary により列ごとの基本統計量を計算可能に。
    - 標準ライブラリのみで統計処理を行う実装（pandas 等に依存しない）。

- AI / NLP
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を生成し、ai_scores テーブルへ書き込む処理を実装。
    - ニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算する calc_news_window。
    - バッチサイズ、最大記事数・文字数トリム、スコアクリッピング（±1.0）、最大リトライ、指数バックオフなどを備えた堅牢な API 呼び出し設計。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
    - API レスポンス検証・部分失敗時のテーブル保護（更新対象の code を絞って操作）を実装。
    - 実行は DuckDB の raw_news / news_symbols / ai_scores を参照。ルックアヘッドバイアスを避けるため内部で datetime.today() を参照しない方針。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を追加（--from / --to / --db オプション対応）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等を算出。
    - 判定基準（閾値）を定義し、PASS/FAIL 判定を出力（閾値はソース内で定義）。DB が見つからない場合やテーブルがない場合に graceful に扱う。
    - P95 計算、日付フィルタの ISO8601 UTC 変換等を実装。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）を提供。未対応 OS はスキップして警告。
    - CPU affinity 設定用の set_cpu_affinity を実装（N コアにピン留め）。権限不足や未実装環境では警告ログを出してスキップ。
  - パッケージ初期化
    - __init__.py にバージョン 0.1.0 を設定。

Changed
- —（初回リリースのため該当なし）

Fixed
- DB / データ不足時の安全性向上
  - research / tools / ai 等でデータ欠損時に None を返す・例外をキャッチするなど、堅牢性を確保。
  - init_monitoring_db() を呼び出して監視テーブルの存在を冪等に保証する処理を各スクリプトで呼出すようにした（監視テーブルが無くても起動可能）。
  - paper_verification_report はテーブル欠損時や DB 不在時に適切にメッセージ出力して終了する。

Security
- 機密情報の取り扱い
  - J-Quants, kabu-api, OpenAI の API キー / パスワードは環境変数で取得する設計。Settings クラスで必須キーは _require() により未設定時に明示的な例外を投げる。
  - .env ロードは OS 環境変数を保護する仕組み（protected set）を採用。

Notes / Migration
- 環境変数とデフォルトパス
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用、監視サービスは常にこのパスを使用）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - PID_FILE_PATH / KILL_FLAG_PATH 等の監視周りのパスは Settings 経由で取得。
- run_monitoring は監視データのために常に本番 sqlite_path を参照するため、監視のみ別 DB にしたい場合は SQLITE_PATH を調整してください。
- run_execution は KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使用して発注データを本番 DB から分離するよう設計されています。
- OpenAI を使用する ai.news_nlp の実行には OPENAI_API_KEY の設定が必須です。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかに設定してください。無効値は例外になります。

Acknowledgements
- 本リリースはコード内の docstring / コメントおよび実装から仕様を推測して作成しています。実際のプロジェクト方針や運用上の要件に応じて調整してください。