# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。フォーマットは主に「Added / Changed / Fixed / Removed / Security」を使用しています。

## [0.1.0] - 2026-04-13
初回リリース。自動売買システム KabuSys のコア機能群を実装および追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 実行用スクリプト
  - run_monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを起動。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告ログ出力。
    - 監視は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB を接続して監視を実行。
  - run_execution 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine のセッション実行エントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。ExecutionEngine, OrderManager, RiskManager, Reconciler を組み立てて実行。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境変数管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み（プロジェクトルート（.git / pyproject.toml）を探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ実装: export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメント処理に対応。
    - OS 環境変数を保護するための上書きロジック（.env.local は override=true だが OS 環境変数は保護）。
    - 必須 env の取得用 _require と各種設定プロパティ（DB パス、PID/KILL フラグ、閾値、env 判定、paper_trading 関連など）。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）と PAPER_TRADING_SQLITE_PATH のサポート。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: score 降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: スコア全0 の場合は等金額配分にフォールバック（警告）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクターエクスポージャーを計算して過剰セクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear を実装、未知レジームは警告の上 1.0 にフォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") をサポート。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積り、残余分の lot_size 配分ロジックを実装。
  - portfolio パッケージエクスポートを整備（src/kabusys/portfolio/__init__.py）。

- 実行補助ユーティリティ
  - プロセス優先度・CPU アフィニティ設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level): Windows と POSIX（Linux/Mac/FreeBSD）に対応。権限不足などを考慮して例外をキャッチし警告でスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定する機能（未指定は全コア使用、エラーは警告でスキップ）。
  - utils パッケージ初期化ファイル追加（src/kabusys/utils/__init__.py）。

- 監視・検証ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
    - P95 計算ユーティリティ、閾値定義（稼働率 >= 99% 等）と PASS/FAIL 判定、DB 存在チェック、期間フィルタ対応。
  - tools パッケージ初期化ファイル追加（src/kabusys/tools/__init__.py）。

- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（DuckDB の prices_daily を参照、ウィンドウ不足時は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials から直近財務を結合して PER / ROE を算出。
    - 実装は DuckDB クエリ中心で高性能集計を想定。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 任意ホライズンの将来リターンを計算（horizons 検証、複数ホライズンをまとめて 1 クエリで取得）。
    - calc_ic: スピアマンランク相関（IC）計算（コード結合、None / 微小分散ハンドリング、3 件未満は None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、各種統計量（count/mean/std/min/max/median）。
  - research パッケージエクスポートを整備（src/kabusys/research/__init__.py）。

- AI ニュース NLP（下書き・実装済み機能）
  - ai/news_nlp モジュールを追加（src/kabusys/ai/news_nlp.py）。
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチで送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書込む処理を実装。
    - ニュース収集ウィンドウ（JST 前日 15:00 ～ 当日 08:30）を計算する calc_news_window。
    - バッチサイズ、1 銘柄あたり記事・文字上限、スコアの ±1.0 クリップ、最大リトライ回数（指数バックオフ）、レスポンス検証などを実装。
    - api_key 解決（引数優先 → OPENAI_API_KEY 環境変数）。未設定時は ValueError を送出。
    - 実装では DuckDB の raw_news/news_symbols/ai_scores を参照／更新する想定。
    - （ファイル中で処理フロー・安全策・部分更新戦略が明記されている。なお、ファイルは大きめの実装で一部が断片のまま存在する可能性あり。）

- データベース初期化フック
  - init_monitoring_db を用いた監視テーブルの冪等初期化呼び出しを run_* スクリプトで行う（監視テーブルが存在しない場合の自動作成を想定）。

### Changed
- なし（初回リリースのため変更履歴は追加事項として記載）。

### Fixed
- なし（初回リリース）。

### Removed
- なし（初回リリース）。

### Security
- OpenAI API キーの取り扱いは引数または環境変数を用いる設計。未設定時は明示的にエラーを出す仕様（誤った公開を防止するための明示的チェック）。

---

補足・設計方針（コードから推測）
- DuckDB をデータ分析用に積極利用し、prices_daily / raw_financials 等の大規模集計は SQL で実施する設計。
- 本番と paper_trading の DB を分離することでテスト・検証と本番運用を明確に区別。
- 自動ロードされる .env 系のパーサは堅牢化（クォート・エスケープ・export 形式・インラインコメント対応）され、OS 環境変数の上書き防止を行う。
- クリティカルな操作（プロセス優先度設定、CPU affinity 設定、外部 API 呼び出し）は権限不足や未対応環境を想定して安全にフォールバックする実装。
- リサーチ/ポートフォリオ関連は純粋関数として設計されており、副作用を持たずユニットテストがしやすい構造。

もし CHANGELOG の形式や対象リリース（例えば Unreleased を使う等）を変更したい場合は指示してください。必要なら各ファイルごとの詳細な変更点（関数一覧・引数・戻り値・既知の制約）も作成します。