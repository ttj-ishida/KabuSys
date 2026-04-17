# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載します。慣例により重要度の高い変更は上に記載しています。

現在のリリース
----------------

[0.1.0] - 2026-04-17
Added
- 初期公開（v0.1.0）。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine の起動フローを実装。以下を含む:
    - プロセス優先度を起動時に "high" に設定。
    - 環境に応じた SQLite パス選択（paper_trading 環境では専用 DB を使用）。
    - BrokerClientFactory を使ったブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による安全なシャットダウン。
    - RiskConfig の既定値（max_position_pct 等）と初期ポートフォリオ値を broker.get_available_cash() から取得。
- 監視用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。0 以下は無効としてデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - process priority を高く設定してから起動。
    - SQLite / DuckDB 接続を開いて監視ループを回す（例外はロギングして継続）。
- 設定管理
  - config.py:
    - .env / .env.local の自動ロード実装（OS の環境変数が優先、.env.local は .env を上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
    - Settings クラスで各種環境設定をラップ（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境種別検証 等）。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
    - 環境種別（KABUSYS_ENV）は development / paper_trading / live のみ許可。
- ポートフォリオ構築機能（純粋関数）
  - portfolio/portfolio_builder.py:
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。スコア全0 の場合は等配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）。既存保有をセクター別に集計し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた乗数（calc_regime_multiplier）：bull/neutral/bear をマップし未知値は 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py:
    - position sizing ロジック（risk_based / equal / score）。ロット単位丸め、単銘柄上限・アグリゲート上限の適用、cost_buffer を考慮したスケールダウンと残余配分アルゴリズムを実装。
    - lot_size 共通想定（TODOで将来的拡張を示唆）。
- 研究（research）モジュール
  - research/factor_research.py:
    - モメンタム（1M/3M/6M）、MA200乖離、ATR20、20日平均売買代金、出来高比率、PER/ROE（raw_financials 結合）を DuckDB に対する SQL/ウィンドウ関数で計算する関数を実装。
    - データ不足時の None ハンドリングや計算窓のバッファ設計などを考慮。
  - research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman ランク相関）やファクター統計要約（factor_summary）を実装。外部依存（pandas等）を使わず標準ライブラリで実装。
  - research/__init__.py で主要関数をエクスポート。
- AI ニュース NLP（骨格）
  - ai/news_nlp.py:
    - ニュース収集ウィンドウ計算（calc_news_window: 前日15:00 JST〜当日08:30 JST に対応）。
    - OpenAI（gpt-4o-mini）を想定したスコアリング設計（バッチ処理、JSON Mode, スコアクリップ、リトライ戦略、最大記事数・最大文字数トリム等）。
    - score_news の冒頭で API キー検証を実装（api_key 引数または OPENAI_API_KEY 環境変数）。
    - ※ ファイル末尾で処理の一部が切れており実装途中（後述の既知課題参照）。
- ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度を設定するユーティリティ（Windows は psutil の定数、POSIX 系は nice 値）。失敗時は警告してスキップ。
    - CPU affinity 設定関数 set_cpu_affinity を実装（cpu_count 引数に基づいて最初の N コアに固定）。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを実装。稼働率 / 注文成功率 / 送信率 / レイテンシ（AVG/MAX/P95）等を計算し PASS/FAIL 判定を出力。
    - デフォルトで PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）を参照。--from/--to/--db CLI オプションに対応。
    - 各種閾値（稼働率99%、注文成功率90%、送信率95%、P95 200ms）を定義。
- バージョン情報
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- プロジェクトルート探索:
  - config._find_project_root() が __file__ を基点に上位ディレクトリを走査し .git または pyproject.toml を探す実装に変更（CWD に依存しない自動 .env ロード）。

Fixed
- env ファイルパーサの堅牢化:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い、空行/コメント行の無視等に対応。
- calc_forward_returns の horizons バリデーション追加（正の整数・252 以下等）。

Deprecated
- なし（初期リリースのため）。

Removed
- なし（初期リリースのため）。

Security
- OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数で渡すことを要求。未指定時は score_news が ValueError を送出して処理を中止。

既知の課題 / 注意点
- run_monitoring は説明にもある通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します。開発環境で誤って本番 DB を上書きする可能性があるため、運用時は SQLITE_PATH の指定や起動環境に注意してください。
- ai/news_nlp.py の score_news 実装がファイル末尾で途中で切れており、記事取得部分や API 呼び出しループ以降の実装が未完です。現状ではニューススコアの書き込みまで到達しません（要実装・テスト）。
- portfolio/position_sizing.py と portfolio/risk_adjustment.py に TODO コメントあり:
  - 単銘柄の lot_size を銘柄別に持たせる拡張（現状は全銘柄共通 lot_size を想定）。
  - apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題。将来的に前日終値や取得原価をフォールバックする想定。
- process_priority.set_process_priority / set_cpu_affinity は psutil に依存し、権限不足や未サポート OS の場合はスキップされる（警告ログ）。
- DuckDB executemany に関する注意（ai/news_nlp の設計コメントやコードベース全体で考慮済み）：空のパラメータ配列で実行すると DuckDB の古いバージョンでエラーになるため、実行前に空チェックが必要。
- 一部関数はデータ不足（過去データが少ない等）を None で返します。呼び出し側で None ハンドリングが必要です。

移行／運用メモ
- 環境変数の優先順位: OS 環境 > .env.local > .env。OS 環境は保護され .env ファイルで上書きされません（ただし .env.local は override=True のため .env の値を上書く）。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境等で推奨）。
- Paper Trading 環境（KABUSYS_ENV=paper_trading）では別 SQLite（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用する設計。実運用で本番 DB と分離して検証可能。
- MONITOR_POLL_INTERVAL は正の整数を期待します。不正な値を設定するとデフォルト（60 秒）に戻ります。

今後の予定（想定）
- ai/news_nlp の残実装（記事集約 → OpenAI 呼び出し → レスポンス検証 → DB 書き込み）の実装と単体テスト。
- portfolio の lot_size を銘柄別対応へ拡張。
- apply_sector_cap の price フォールバックロジック実装。
- DuckDB / SQLite のマイグレーション/スキーマ管理ユーティリティ追加。

脚注
- 各モジュール内の docstring・コメントに設計意図や注意事項を多く含めています。実装の挙動を変更する場合はコメントと docstring も合わせて更新してください。