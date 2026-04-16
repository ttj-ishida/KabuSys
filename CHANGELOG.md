CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。

Unreleased
----------

- なし

0.1.0 - 初回リリース
--------------------

Added
- 実行／監視用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 SQLite（data/paper_trading.db を既定）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine のスレッド実行。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理（data/execution.pid）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出で安全にループ終了、KeyboardInterrupt 対応。

- 環境/設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み優先度管理、OS 環境変数を保護する protected 機構。
    - .env パースの改善:
      - export KEY=val 形式対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ対応
      - インラインコメントの取り扱い（クォート外かつ直前がスペース/タブの '#' をコメントと判定）
    - Settings クラスで各種環境変数のラッパーを提供（検証付き）
      - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須チェック
      - PAPER_FILL_MODE の有効値検証（instant/partial/never/reject）
      - KABUSYS_ENV の有効値検証（development/paper_trading/live）
      - デフォルトパス値（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）
      - 監視設定（PID ファイルパス、しきい値等）

- 監視・ツール
  - monitoring_db の初期化呼び出しを run 系から実施（存在確認・冪等に保証）。
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成コマンドラインツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - CLI オプション: --from / --to / --db。PAPER_TRADING_SQLITE_PATH 環境変数にも対応。
    - P95 計算、日付フィルタ生成、DB の存在チェックとエラーハンドリング実装。
    - 既定の閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重（スコア全て 0 の場合は等分配にフォールバックし警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター別エクスポージャー上限チェック（sell_codes を除外して計算）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金倍率（bull/neutral/bear、未知レジームは警告して 1.0 フォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。
    - 単元株（lot_size）で丸め、per-position と aggregate のキャップ、cost_buffer を加味したスケールダウンと端数処理（残余配分アルゴリズム含む）。
    - 各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer）を受け取り柔軟に設定可能。

- リサーチ／因子計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算（DuckDB を利用）。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率の計算。
    - calc_value: PER・ROE の計算（raw_financials + prices_daily）。
    - SQL ウィンドウ関数を利用した効率的実装とデータ不足時の None 処理。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）の計算。
    - calc_ic: スピアマンランク相関による IC 計算（結合／欠損除外／最小サンプル数チェック）。
    - rank / factor_summary: ランク付け、基本統計量（count/mean/std/min/max/median）集計。
    - 標準ライブラリのみでの実装、DuckDB 接続前提。

- AI ニュース NLP（部分実装）
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込むための機能を追加。
    - ニュース収集ウィンドウ計算（JST->UTC 変換）、記事トリミング（最大記事数・最大文字数）、バッチ送信（最大 20 銘柄）、エクスポネンシャルバックオフによるリトライ、レスポンスバリデーション、スコアクリップ（±1.0）等の設計方針を実装。
    - OpenAI API キーは引数または OPENAI_API_KEY 環境変数から解決。未設定時は ValueError を送出。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX（Linux, macOS, FreeBSD）に対応してプロセス優先度を設定。アクセス権限や未対応 OS では警告を出力してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 設定、検証とエラーハンドリング実装。
    - psutil を利用したクロスプラットフォーム対応。

Changed
- ログ出力とエラー処理を強化
  - run系スクリプトと各モジュールで例外発生時に logger.exception/ logger.warning を利用して詳細を残す実装。
  - run_monitoring の MONITOR_POLL_INTERVAL の不正値処理で警告後デフォルトにフォールバック。

Fixed
- .env パーサーの細かい仕様改善（export 形式、クォート内エスケープ、インラインコメントの扱い）により .env の互換性を向上。
- DuckDB/SQLite の接続と初期化順序の明確化（monitoring DB の初期化を起動時に確実に行う）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーや各種シークレットは Settings 経由で必須チェックを行い、未設定時は明示的にエラーを出すようにして、キーの存在を起動時に検出可能にした。

Notes / その他
- run_monitoring と run_execution は停止フラグ（data/stop_requested.flag）に依存しており、外部からの停止制御を想定した設計になっています。
- Paper Trading 用処理は本番 DB と明確に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH により上書き可能）。
- ai/news_nlp.py は記事集約からスコア書き込みまでのフロー設計が定義されていますが、スニペットは途中で切れているため実装が完了していない可能性があります。実運用前に score_news の最終処理（記事取得→API呼び出し→DB書き込み）の実装完了を確認してください。

How to Contribute
- 変更はこのファイルに記録してください。重要な変更はカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）に分けて記述してください。