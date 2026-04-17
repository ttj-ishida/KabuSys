CHANGELOG
=========

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※ リリース日付はコードベースから推測して付与しています。

Unreleased
---------

- （なし）

0.1.0 - 2026-04-17
-----------------

Added
- 初期リリース。以下の主要機能・モジュールを追加。
  - 実行／監視ランチャー
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory 経由でブローカクライアントを生成。OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine をスレッドで実行。
      - data/stop_requested.flag による外部停止フラグの監視、実行時 PID ファイル管理（data/execution.pid）に対応。
      - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - run_monitoring.py
      - SystemMonitor のポーリングループを起動するスクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。0 以下や不正値はデフォルトにフォールバックして警告を出力。
      - 監視は KABUSYS_ENV にかかわらず監視用の sqlite_path（Settings.sqlite_path）を使用。
      - 停止フラグ（data/stop_requested.flag）検知でループ終了。例外発生時はログ出力して次サイクルへ継続。
  - 設定管理
    - kabusys.config.Settings
      - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
      - .env/.env.local のパースを独自実装（export プレフィックス、クォートやエスケープ、インラインコメント処理に対応）。OS 環境変数を保護する protected 上書きポリシーを導入。
      - 多数のプロパティを提供: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE（バリデーションあり）、PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEMORY/DISK 閾値、LOG_LEVEL、KABUSYS_ENV（development/paper_trading/live の検証）など。
      - settings = Settings() の単一インスタンスをエクスポート。
  - ポートフォリオ構築（純関数群）
    - kabusys.portfolio.portfolio_builder
      - select_candidates(): スコア降順で候補選定（タイブレークに signal_rank を使用）。
      - calc_equal_weights(), calc_score_weights(): 等配分・スコア正規化配分（スコアが全て 0 の場合は等配分へフォールバック）。
    - kabusys.portfolio.risk_adjustment
      - apply_sector_cap(): セクター集中上限 (max_sector_pct) の適用、既存保有のセクターエクスポージャー計算（売却予定銘柄を除外できる）、unknown セクター挙動の明示。
      - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告を出して 1.0 でフォールバック）。
    - kabusys.portfolio.position_sizing
      - calc_position_sizes(): risk_based / equal / score の配分方式をサポート。ロットサイズ単位で丸め、単銘柄上限・合計上限（available_cash）に基づくスケールダウン、cost_buffer を考慮した保守的見積り、端数処理（残差に基づく追加配分）を実装。
  - 研究（research）モジュール
    - kabusys.research.factor_research
      - calc_momentum(), calc_volatility(), calc_value(): DuckDB の SQL を用いたファクター計算を実装。窓幅やデータ不足時の取り扱い（NULL / None）に注意。
    - kabusys.research.feature_exploration
      - calc_forward_returns(): 任意ホライズンの将来リターンを一括取得。入力検証（horizons の範囲）あり。
      - calc_ic(): スピアマンのランク相関（Information Coefficient）を実装。有効レコードが少ない場合は None を返す。
      - rank(), factor_summary(): ランク作成と基本統計サマリ（count/mean/std/min/max/median）。
    - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
  - ニュース NLP（AI スコアリング）
    - kabusys.ai.news_nlp
      - raw_news を OpenAI（gpt-4o-mini）でセンチメント分析し、ai_scores テーブルへ書き込むワークフローを追加。
      - バッチ処理（_BATCH_SIZE=20）、トークン肥大対策（記事数・文字数トリム）、JSON Mode 出力のバリデーション、スコアを ±1.0 にクリップ。
      - 429/ネットワーク/5xx に対する指数バックオフリトライ（上限あり）を実装。API キー未設定時は ValueError。
      - calc_news_window(): JST ベースのニュース収集ウィンドウ計算ユーティリティを提供（前日15:00 JST〜当日08:30 JST）。
      - 部分失敗時でも既存スコアを保護するため、更新対象コードを限定して DELETE→INSERT を行う設計。
  - ツール
    - kabusys.tools.paper_verification_report
      - Paper Trading 用 SQLite を解析して検証レポートを標準出力に出力する CLI を追加。
      - オプション: --from, --to, --db と期間/DB 指定が可能。デフォルト DB: data/paper_trading.db / 環境変数 PAPER_TRADING_SQLITE_PATH からも指定可。
      - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数。閾値（PASS/FAIL）を定義して判定を出力。
  - ユーティリティ
    - kabusys.utils.process_priority
      - set_process_priority(level): Windows/POSIX の差分を吸収してプロセス優先度を設定。権限不足等は警告出力してスキップ。
      - set_cpu_affinity(cpu_count): 指定コア数への affinity 固定（エラー時は警告してスキップ）。
  - パッケージ基礎
    - __init__.py に __version__ = "0.1.0" を追加。主要サブパッケージを __all__ で公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から取得する設計。未設定時は明示的にエラーにすることで誤った動作を防止。

Notes / Implementation details
- DuckDB をデータ解析エンジンとして採用しており、research / ai モジュールは DuckDB 接続経由でテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores など）を参照する想定です。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。OS 環境変数の保護（.env.local で上書きが必要な場合でも OS 環境変数が優先される）を行います。
- run_monitoring/run_execution は起動時にプロセス優先度を上げようと試みます（プラットフォームや権限により失敗する場合は警告で継続）。
- paper_verification_report の閾値や出力形式はコード内の定数（THRESHOLD_*）で定義されています。必要に応じて変更可能です。

問い合わせ / 追記
- 実装の詳細やリリースノートの追記が必要な場合は変更履歴（コミットログ）や意図したバージョニング方針を共有してください。