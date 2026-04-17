# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。

※本 CHANGELOG は、コードベース（src/ 以下）から推測して作成しています。

## [0.1.0] - YYYY-MM-DD
最初の公開相当のリリース。自動売買システム KabuSys の基礎機能群を追加しました。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非整数）はデフォルトにフォールバックし、警告を出力。
    - 停止フラグファイル（data/stop_requested.flag）を監視し、検知時に安全にループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用する実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に分離して記録。
    - 停止フラグ（data/stop_requested.flag）を検知してエンジンを停止。
    - 実行中の PID を管理する PID ファイル（data/execution.pid）を利用。

- 設定 / 環境管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env / .env.local の自動読み込み機能を追加。OS 環境変数は保護され、デフォルトで上書きされない。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサは次の機能をサポート:
      - `export KEY=val` 形式
      - シングル/ダブルクォートされた値（バックスラッシュエスケープ対応）
      - クォートなし値のインラインコメント処理（直前がスペース/タブの場合に # をコメントと認識）
    - Settings クラスを提供。多数のプロパティを環境変数から取得:
      - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject"、不正値は例外）
      - 監視・閾値設定（cpu/memory/disk の閾値、PID ファイルパス、kill flag の設定等）
      - KABUSYS_ENV 値検証（development / paper_trading / live）
      - LOG_LEVEL 検証

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソート、同点時は signal_rank 小さい方を優先。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分。全スコアが 0 の場合はスコア配分が等金額にフォールバックし WARNING を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター露出が閾値を超える場合に、新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を提供（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）をサポート。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer（手数料/スリッページ見積り）対応。risk_based はリスク額に基づく株数算出を実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算。
    - calc_value: EPS/ROE を用いた PER/ROE 計算（raw_financials と prices_daily を使用）。
    - DuckDB を使った SQL ベースの実装で、prices_daily / raw_financials テーブルのみ参照。
  - research/feature_exploration.py
    - calc_forward_returns: 任意ホライズン（検証済み: 正値・252 以下）に対する将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。レコード不足時は None。
    - factor_summary / rank: ファクターの基本統計量計算、ランク付けユーティリティ。
  - research/__init__.py に主要関数をエクスポート。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加。CLI で期間指定可能（--from / --to / --db）。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計し、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づき PASS/FAIL 判定を出力。
    - DB のテーブルが存在しない場合は OperationalError をハンドリングして N/A を出力するなど堅牢化。

- AI ニュース NLP（下地実装）
  - ai/news_nlp.py
    - ニュース記事を OpenAI（gpt-4o-mini）でセンチメントスコアリングし ai_scores テーブルへ書き込む設計を追加。
    - ニュース収集ウィンドウの計算（JST ベース: 前日 15:00 〜 当日 08:30）を提供する calc_news_window。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコア ±1.0 クリップ、部分更新（成功した銘柄のみ置換）などを設計文書として実装。
    - （ファイル末尾で処理が途中で切れているため一部未完成の可能性あり）

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX（Linux / Darwin / FreeBSD）でのプロセス優先度設定を抽象化。権限エラーなど失敗時は警告してスキップ。
    - set_cpu_affinity: 指定コア数に CPU affinity を固定する関数を追加（引数検証・エラー耐性あり）。

### Changed
- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ で公開。

- DB 初期化
  - run_monitoring/run_execution 起動時に init_monitoring_db() を呼び出して監視テーブルの存在を保証（冪等）。

### Fixed / Robustness
- 多くの場所で I/O / DB / API 呼び出しに対して例外処理を追加・強化:
  - run_monitoring の polling loop で monitor.check_once() が例外を投げてもループ継続（例外ログ出力）。
  - paper_verification_report はテーブル不存在（OperationalError）を個別に捕捉してレポートを生成。
  - process_priority や CPU affinity 設定での AccessDenied 等を捕捉して警告出力。

### Notes
- 環境変数の取り扱い:
  - 自動 .env ロードはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 各設定プロパティは厳密な検証を行うため、環境変数の値が不正な場合は ValueError が発生します（起動時に明示的に失敗させることで早期検出を狙う設計）。
- Paper Trading と Live の DB 分離:
  - paper_trading 用に専用 SQLite（PAPER_TRADING_SQLITE_PATH / デフォルト data/paper_trading.db）を使用することで、本番データと検証データを完全に分離します。
- AI ニュースモジュールは API キー（OPENAI_API_KEY）必須。実行時はキーを渡すか環境変数で設定してください。
- 一部ファイル（ai/news_nlp.py の末尾など）で実装が途中で切れている可能性があるため、実運用前の追加のレビュー・テストを推奨します。

### Removed
- なし（初期リリース相当のため該当なし）。

### Security
- OpenAI API キー等の機密情報は .env に保持する想定（.env.local を優先して上書き可能）。自動ロードで OS 環境変数は上書きされないよう保護しています。

---
今後の予定（例示）
- ai/news_nlp.py の完全実装（DB からの記事集約、API コール実装、ai_scores 書き込み処理の完成）。
- テストカバレッジの追加（parsers, position sizing, risk adjustments, research functions）。
- ドキュメント（API/設計ドキュメント、運用ガイド）の充実。