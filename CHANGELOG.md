Changelog
=========
（このファイルは Keep a Changelog 準拠で作成されています。重要な変更点・追加機能を日付順に記録します。）

Unreleased
----------
- 現在なし。

[0.1.0] - 2026-04-13
--------------------

Added
- パッケージの初期公開。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 設定・環境変数管理（src/kabusys/config.py）
  - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env ロードを実装。
  - .env / .env.local の優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - .env パースの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメント処理（クォートなしは '#' の直前がスペース/タブのときのみコメントと認識）。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）取得用メソッドと妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や監視ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）等のプロパティを整備。
- 実行系（src/kabusys/run_execution.py）
  - ExecutionEngine の起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。MockBroker 使用想定。
  - 実行開始前にプロセス優先度を high に設定（src/kabusys/utils/process_priority.py を利用）。
  - 依存コンポーネント組み立て例を実装（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）。
  - RiskManager のデフォルト設定（max_position_pct 等）を明示。
- 監視系（src/kabusys/run_monitoring.py, src/kabusys/monitoring/*）
  - SystemMonitor ポーリングループの起動スクリプトを追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
  - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する仕様（監視データは本番 DB を参照/書込）。
  - 起動時にプロセス優先度を high に設定。
  - SQLite / DuckDB 接続の確立とクリーンアップを実装。
- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates（スコア降順＋signal_rank タイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、全スコア 0 の場合は等配分にフォールバック）
  - risk_adjustment:
    - apply_sector_cap（既存保有のセクター別エクスポージャーに基づく候補除外。unknown セクターは除外対象外）
    - calc_regime_multiplier（market regime に応じた投下資金乗数。未知レジームは警告して 1.0 にフォールバック）
  - position_sizing:
    - calc_position_sizes（risk_based / equal / score の各 allocation_method をサポート。単元株（lot_size）丸め、aggregate cap によるスケールダウンと端数処理を実装）
    - cost_buffer による保守的見積り対応
    - いくつかの挙動は設定可能（risk_pct, stop_loss_pct, max_position_pct, max_utilization 等）
- リサーチ（src/kabusys/research/*）
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離率）
    - calc_volatility（ATR20、ATR/close、20日平均売買代金、出来高比率）
    - calc_value（EPS/ROE に基づく PER/ROE。raw_financials から直近報告を参照）
    - DuckDB を用いた SQL 実装、営業日スライドウィンドウを想定したスキャン範囲バッファ
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン。horizons の入力検証あり）
    - calc_ic（スピアマンランク相関による IC 計算、最低レコード数チェック）
    - factor_summary / rank（基本統計量・ランク付けユーティリティ）
  - research パッケージ __init__ で主要関数をエクスポート
  - pandas 等外部ライブラリに依存しない実装方針
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄単位の ai_scores を生成して書き込む機能を実装。
  - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST の記事）を計算する calc_news_window 実装。
  - 1バッチ最大 20 銘柄、1銘柄あたり最大記事数/文字数制限（トークン肥大化対策）。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ（上限あり）。
  - レスポンス検証、スコアを ±1.0 にクリップ、部分更新（該当コードのみ DELETE→INSERT）で部分失敗耐性を確保。
  - OpenAI API キー未設定時は ValueError を送出。
- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading の検証レポート生成 CLI を追加。
  - コマンドライン引数 --from/--to/--db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB パス上書き可能。
  - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ による PASS/FAIL 判定基準とデフォルト閾値（README 相当の基準をコード内定義）。
  - P95 計算・各種集計クエリ、DB がない場合のエラーメッセージを実装。
- ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority（Windows / POSIX の差を吸収して優先度設定。対応 OS: Windows, Linux, Darwin, FreeBSD。アクセス権限や未実装 API にはフォールバックして警告出力）
  - set_cpu_affinity（最初 N コアに固定。引数検証と例外ハンドリングあり）

Fixed
- .env 読み込みの堅牢化:
  - export プレフィックスやクォート内のエスケープを正しく処理することで、複雑な環境変数の記述に対応。
  - .env.local の override 実装時、OS 環境変数を保護する protected set を導入（重要な OS 環境変数が .env により上書きされるのを防止）。
- calc_score_weights: 全銘柄スコアが 0 の場合に等金額配分へフォールバック（警告ログ出力）。

Changed
- 設計方針の明文化:
  - リサーチ・ファクター計算は DuckDB + SQL ベースで実装し、外部 API や発注系にはアクセスしない（安全に再現可能なオフライン計算）。
  - CLI/ツール・研究機能は pandas 等に依存しない純標準ライブラリ実装を目標とする。

Known issues / Notes / TODO
- position_sizing.calc_position_sizes:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされてしまう可能性があり、将来的に前日終値や取得原価でのフォールバックを検討（TODO コメントあり）。
  - 将来的な拡張: 銘柄別 lot_size をサポートする設計への改修予定（現在は全銘柄共通 lot_size）。
- DuckDB 側の注意:
  - 一部実装（ai.news_nlp／score の DB 書き込み等）で executemany 前に params が空でないことを確認するコード設計になっている（DuckDB 0.10 の制約対策）。
- AI API 周り:
  - OpenAI API の呼び出しは外部依存であり、キー（OPENAI_API_KEY）・レート制限・コストに注意。API 失敗時はフェイルセーフでスキップする設計。
- プロセス優先度・CPU affinity:
  - 実行環境（OS・権限）によっては設定が失敗し、警告が出力されるが処理は継続する。
- 監視（SystemMonitor）:
  - run_monitoring は監視用 DB に本番 sqlite_path を使うため、開発環境での誤操作に注意。

Security
- 必須のシークレット類は Settings._require を通じて明示的に要求（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。README/.env.example を参照の上、環境変数の管理に注意してください。
- OPENAI_API_KEY が未設定の場合、AI ニューススコア機能は ValueError を送出する仕様。

Notes for operators / developers
- 実行例:
  - 監視ループ: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を調整可能（不正な値はデフォルト 60 秒へフォールバック）。
  - 実行エンジン: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB に切り替わる。
  - Paper 検証レポート:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db で DB を指定可能、未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db を参照。

-----

（今後のリリースではテストカバレッジ、より細かいコンフィグ分離、lot_size の銘柄別対応、価格フォールバックの実装、AI 呼び出しの更なる堅牢化を予定しています。）