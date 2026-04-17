CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
ソースツリー内の実装内容から推測して記載しています。

なお日付はこのリリースの想定日付です。

[Unreleased]
------------

### Added
- なし（次回リリース予定: ニュースNLPの完全実装、追加テスト、ドキュメント補完）

### Changed
- なし

### Fixed
- なし

### Deprecated
- なし

### Removed
- なし

### Security
- なし

[0.1.0] - 2026-04-17
--------------------

初回公開想定リリース。以下の主要機能とモジュールを実装／追加しています。

### Added
- 基本設定管理（kabusys.config.Settings）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - export 付き行、シングル／ダブルクォート、行内コメント等に対応した .env パーサー実装。
  - 必須環境変数チェック（_require）と各種設定プロパティ（DBパス、APIキー、運用モード判定、閾値など）。
  - PAPER_FILL_MODE の列挙チェックなど入力検証ロジックを追加。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使って本番 DB と分離。
    - BrokerClientFactory に基づくブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を提供。
    - スレッドで engine.run_session を起動し data/stop_requested.flag の検知で安全停止。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼出し）。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動用スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はフォールバックして警告）。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 監視 DB 初期化ユーティリティ（monitoring_db.init_monitoring_db の使用）
  - run_* スクリプト起動時に監視テーブル存在を担保する呼出しが組み込まれている。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) で Windows / POSIX(Linux/Mac/FreeBSD) の差分を吸収して優先度設定。
  - set_cpu_affinity(cpu_count) による CPU ピンニング機能（アクセス権限や未対応プラットフォーム時は警告してスキップ）。
  - アクセス拒否や未実装 API を考慮した例外ハンドリングとログ出力。

- ポートフォリオ構築・リスク調整・ポジションサイジング
  - kabusys.portfolio.portfolio_builder
    - select_candidates, calc_equal_weights, calc_score_weights を提供。score が全て 0 の場合は等金額にフォールバックして警告。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: 既存保有と価格マップからセクター別エクスポージャを算出し、上限超過セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に基づく資金乗数（bull/neutral/bear にマッピング）を提供。未知レジームは警告して 1.0 にフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に応じた発注株数算出。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer を用いた保守的見積り、スケールダウン後の端数処理（remainders を使った追加配分）を実装。
    - 価格欠損・不正値に対するスキップ動作とログ出力。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily テーブルから計算。データ不足時は None を返却。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に扱う実装。
    - calc_value: raw_financials から最新の財務データを結合して PER/ROE を計算。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターンを一括で取得（入力検証あり）。
    - calc_ic / rank / factor_summary: スピアマン順位相関（IC）計算、ランク付け（同順位は平均ランク）、および基本統計量サマリー機能を提供。
  - research パッケージは zscore_normalize を kabusys.data.stats へ委譲してエクスポート。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を解析して検証レポートを標準出力に生成する CLI。
    - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数。
    - パス／日付フィルタ（--from / --to / --db）に対応、閾値による PASS/FAIL 判定（閾値はファイル内定数）。
    - DB テーブルが無い場合や OperationalError はフェイルセーフに扱い N/A や 0 を返す実装。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores テーブルへ書き込む設計を実装。
  - 設計上の特徴:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算関数 calc_news_window を提供。
    - 銘柄ごとの記事集約（記事数/文字数の上限）・最大20銘柄バッチ送信、JSON Mode 出力のバリデーション、スコアクリップ ±1.0、429/5xx 等での指数バックオフリトライなどを想定。
  - 注意: ファイルは途中で切れている（score_news の記事集約処理が未完）。完全実装は今後。

### Changed
- パッケージ初期化でバージョン定義（kabusys.__init__.__version__ = "0.1.0"）を追加。

### Fixed
- .env パーサー改善により以下のケースを正しく処理:
  - export KEY=val 形式の行
  - シングル/ダブルクォート内のバックスラッシュエスケープ
  - クォートなし行の行内コメント扱い（直前にスペース/タブがある場合のみ）

### Security
- OpenAI API キーや各種機密値は環境変数経由で取得する設計。Settings._require による未設定時の明示的エラー通知。

### Known limitations / TODO
- news_nlp.score_news 実装が途中で終了しており、記事集約→API呼び出し→DB書込のフローが未完（ファイル末尾で切れている）。次リリースで完成予定。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価の利用）に関する TODO コメントあり。
- DuckDB 操作は SQL を直接実行する実装であり、将来的に最適化や大規模データ向けのチューニング余地あり。
- run_monitoring は監視 DB に常に本番 sqlite_path を使う設計で、番兵的な分離はされていない（意図的な設計と思われるが運用注意）。

配布・開発者向けメモ
--------------------
- 実行:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数:
  - .env 自動読み込みの挙動や保護（OS 環境変数の上書き防止）に注意。
  - PAPER_TRADING_SQLITE_PATH, SQLITE_PATH, DUCKDB_PATH, OPENAI_API_KEY, KABUSYS_ENV 等を設定して利用。

ライセンス / 著作権
------------------
- この CHANGELOG はソースコードの状態から推測して作成しています。実際のコミット履歴やリリースノートを基にする場合は適宜修正してください。