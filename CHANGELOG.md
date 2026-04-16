Keep a Changelog に準拠した CHANGELOG.md を日本語で作成しました。

CHANGELOG.md
=============
すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-16
--------------------

Added
- コア初期リリース。
  - パッケージ情報
    - kabusys パッケージ初回リリース。バージョン: 0.1.0
  - 実行 / 監視用エントリポイント
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用の SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）へ記録して本番 DB と完全分離。
      - 実行中は data/execution.pid に PID を記録、data/stop_requested.flag により停止を検知して安全に終了。
      - スレッドで ExecutionEngine を実行し、停止フラグ検知時に engine.stop() を呼ぶ構成。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
      - 監視処理は環境にかかわらず本番 sqlite_path を使用（監視データは本番側 DB に記録される点に注意）。
      - data/stop_requested.flag による停止検知を実装。
  - 設定管理
    - config.Settings を実装。環境変数・.env ファイルからの値取得を一元化。
    - 自動 .env 読み込み:
      - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロード（OS 環境変数が優先）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能。
      - .env パーサは export プレフィックス、クォート文字（'"/エスケープ）やインラインコメントを考慮。
    - 各種設定プロパティを提供（例: sqlite_path, duckdb_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/メモリ/ディスク閾値等）。
    - 入力検証: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の妥当性チェックを実装。
  - Portfolio 構築関連（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
      - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして WARNING を出力。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、レジームに応じた乗数（calc_regime_multiplier）。
      - calc_regime_multiplier は既知レジーム（bull/neutral/bear）をサポートし、不明時は 1.0 でフォールバック（警告ログ）。
    - portfolio.position_sizing: 発注株数計算（calc_position_sizes）。
      - risk_based / equal / score の割当方法をサポート。
      - 単元株丸め（lot_size）、ポートフォリオ上限・per-position 上限、cost_buffer を用いた保守的見積り、aggregate キャップに応じたスケーリングと残余キャッシュによる端数配分を実装。
  - Research / ファクター計算
    - research.factor_research:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。
      - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比率を計算。
      - calc_value: PER, ROE を raw_financials と prices_daily から計算（最新レポートを銘柄ごとに取得）。
    - research.feature_exploration:
      - calc_forward_returns: 将来リターン（任意ホライズン）計算。
      - calc_ic: スピアマンランク相関（IC）計算。
      - rank / factor_summary: ランク変換、基本統計量サマリ機能。
    - いずれも DuckDB 接続を受け取り SQL と Python の組合せで実行（外部 API には依存しない設計）。
  - AI ニュース NLP
    - ai.news_nlp: raw_news から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込む機能を追加。
      - バッチサイズ、トークン過剰対策（記事数・文字数上限）、JSON モード厳格性、最大リトライ回数と指数バックオフ、429/ネットワーク/5xx に対するリトライ戦略を実装。
      - OpenAI API キーは引数か環境変数 OPENAI_API_KEY で指定。未指定時は例外を送出。
      - news の収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を提供する calc_news_window。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
      - 稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を計算し、閾値に基づく PASS/FAIL 判定を出力。デフォルト DB は data/paper_trading.db。
  - ユーティリティ
    - utils.process_priority:
      - set_process_priority(level) で Windows / POSIX(Linux/Mac/FreeBSD) に対応した優先度設定を抽象化。
      - set_cpu_affinity(cpu_count) による CPU 固定（利用可能なコア未満指定を安全に処理）。
      - 例外時（権限不足等）は警告を出し処理をスキップ。

Changed
- .env 自動ロードの挙動を明確化。
  - OS 環境変数は保護され上書きされない（ただし .env.local は override=True で上書き可能だが、OS 環境変数は protected により保護される）。
- init_monitoring_db() を run_execution/run_monitoring 起動時に呼び出して監視テーブルの存在を保証（冪等処理）。

Fixed
- .env パーサの堅牢化:
  - export プレフィックスに対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
  - クォートなし値のインラインコメント処理を改善（'#' の直前が空白/タブの場合のみコメント扱い）。
- MONITOR_POLL_INTERVAL の不正値（0 や負の数、非整数）に対してログを出力しデフォルトにフォールバックするように変更。time.sleep に渡して ValueError になるのを防止。
- calc_score_weights: 全スコアが 0 のケースで等配分にフォールバックし警告を出すよう改善。
- position_sizing の aggregate スケーリングで端数処理を改良。残余キャッシュで lot_size 単位の追加割当ロジックを追加して再現性を確保。

Security
- 重要: AI モジュールは OpenAI API キーを必要とします。キーの取り扱いは環境変数または安全なシークレット管理を推奨します。

Notes / Runtime considerations
- 監視（run_monitoring）は環境（KABUSYS_ENV）に関わらず Settings.sqlite_path（本番監視 DB）を使用します。Paper Trading 用監視を分離したい場合は別途構成が必要です。
- Paper Trading 実行時は settings.is_paper==True で paper_sqlite_path（data/paper_trading.db）を使用します。
- .env 自動ロードを抑止したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_nlp.score_news を使用する際は OPENAI_API_KEY を設定してください。未設定だと ValueError を送出します。
- calc_regime_multiplier の未定義レジームはフォールバック（1.0）しますが、警告が出ます。

Deprecated
- なし

Removed
- なし

-----