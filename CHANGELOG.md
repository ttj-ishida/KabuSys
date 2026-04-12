# CHANGELOG

すべての注目すべき変更を記録します。本ドキュメントは「Keep a Changelog」に準拠します。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed / Deprecated / Security 等は必要に応じて使用

## [0.1.0] - 初回リリース
最初のリリース。システム全体の主要コンポーネント（設定管理、実行エンジン、監視、ポートフォリオ構築、リサーチ、ニュースNLP、ユーティリティ、ツール群）を実装しました。

### Added
- パッケージ基礎
  - kabusys パッケージ本体を追加。バージョンは __version__ = "0.1.0"。
- 設定管理
  - `kabusys.config.Settings` を実装。環境変数から各種設定を提供。
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env / .env.local の自動読み込み機能を追加。OS 環境変数の保護（protected）や override の挙動を考慮。
  - .env ファイルのパース機能を強化（export プレフィックス対応、クォート文字内のバックスラッシュエスケープ、インラインコメントの扱い）。
  - 設定値検証を導入（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の有効値チェック、必須環境変数未設定時の明確なエラー）。
  - デフォルトパス設定: DuckDB / SQLite / paper_trading DB 等のデフォルトパスを提供。
- 実行 / 監視用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite を使用し MockBrokerClient を利用することを想定（本番 DB と分離）。
    - 実行開始時にプロセス優先度を high に設定。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, DuckDB 連携）を組み立ててセッションを実行。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、0 以下は無効としてフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
    - 起動時にプロセス優先度を high に設定。
- データベース初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` の呼び出しにより、監視用テーブルの存在を保証（冪等操作）。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補を選択、タイブレークに signal_rank を使用。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等金額配分にフォールバックして WARNING を出力）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に新規候補を除外。unknown セクターは制限対象外。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear、未知レジームはフォールバックと WARNING）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じた発注株数算出（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）、cost_buffer を考慮した保守的見積り、残差分を lot 単位で再配分するロジックを実装。
- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX を吸収してプロセス優先度を設定。権限不足や未実装 API を安全に扱う（警告出力でスキップ）。
    - set_cpu_affinity: 指定したコア数への CPU affinity 固定（無指定時はスキップ）。誤った引数に対するバリデーションとエラー処理を実装。
- リサーチ（ファクター計算・特徴量解析）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily を使って計算。
    - calc_volatility: 20日 ATR、ATR の相対値、20日平均売買代金や出来高比を計算（true_range の欠損制御を考慮）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（最新の report_date を選択）。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで計算（ホライズン検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装（欠損 / ties / 少数サンプル処理）。
    - rank / factor_summary: ランク変換と基本統計量（count/mean/std/min/max/median）算出。
  - research.__init__: 主要関数と zscore_normalize をエクスポート。
- ニュース NLP（AI スコアリング）
  - ai.news_nlp
    - OpenAI（gpt-4o-mini + JSON Mode）を用いたニュースセンチメントスコアリング機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して比較）を提供。
    - 記事集約（銘柄ごとに最新 N 件 / 文字数制限を設ける）、最大バッチサイズ、バッチごとの API 呼出し、リトライ（429 / ネットワーク / 5xx に対する指数バックオフ）やレスポンスバリデーション、スコアの ±1.0 クリップなどの堅牢な処理。
    - 成功したスコアのみを対象に ai_scores テーブルへ置換挿入する手順（部分失敗時の保護）。
- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - CLI オプションで日付範囲（--from/--to）と DB パス（--db）を受け取る。DB が存在しない場合のエラーメッセージを提供。
    - 指標算出のための SQL クエリと各種ユーティリティ関数（P95 算出、フォーマット関数）を含む。
- DB
  - DuckDB / SQLite を想定したクエリ実装を多数追加（prices_daily / raw_financials / raw_news / trade_logs / system_status / risk_logs / ai_scores 等の想定テーブルに対する処理）。
- ロギングとエラーハンドリング
  - 主要処理での logging を追加（INFO / DEBUG / WARNING / EXCEPTION 等を用途に応じて使用）。
  - 外部リソース操作（ファイル I/O、DB 接続、API 呼び出し）に対する堅牢な例外処理を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Usage Tips
- 環境変数自動ロードはデフォルトで有効。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途向け）。
- Paper Trading の DB は本番 DB と分離されるよう設計（Settings.paper_sqlite_path / PAPER_TRADING_SQLITE_PATH）。
- ニューススコアリングは OpenAI API キー（api_key 引数または OPENAI_API_KEY 環境変数）が必須です。未設定時は ValueError を送出します。
- MONITOR_POLL_INTERVAL に不正値（0 や負値、非数）を設定するとデフォルト（60 秒）にフォールバックし、警告を出力します。
- process_priority / cpu_affinity の設定は権限や OS に依存し、失敗した場合は警告出力の上で実行を継続します。

---

今後のリリースでは以下のような改善を想定しています（予定）:
- order/position 関連の永続化と詳細ログ強化
- リアルタイム監視のアラート機能（LINE 連携等）
- 個別銘柄ごとの lot_size サポート（stocks マスタ参照）
- ニュースNLP の結果キャッシュや並列化によるパフォーマンス改善

もし特定の変更点（例えばバグ修正や API 仕様変更）について詳細な履歴分割を希望される場合は、その旨を教えてください。必要に応じてバージョンを細分化して追記します。