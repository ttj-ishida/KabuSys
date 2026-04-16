CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードベース（スナップショット）から推定したリリース日を使用しています。

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-16
-----------------

Added
- 実行／監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、エンジンのデーモン実行を実装。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止可能。PID ファイル出力サポート。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視データは環境に依らず本番の sqlite_path を使用する設計（監視テーブル初期化含む）。
    - 停止フラグでループ終了、KeyboardInterrupt のハンドリング、各種 DB クローズ処理を実装。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の優先順位（OS 環境変数 > .env.local > .env）と上書き制御（protected set）を実装。
  - .env 行パーサ改善: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなどに対応。
  - Settings クラスを導入し、各種環境変数取得をプロパティ化（バリデーション付き）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）
    - PID / KILL フラグパス、kill_flag_clear_on_start、監視閾値（CPU/MEM/DISK）
    - KABUSYS_ENV / LOG_LEVEL の許容値検証
  - settings インスタンスをデフォルトエクスポート。

- ポートフォリオ構築関連（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights、全スコアが 0 の場合は等配分にフォールバック）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier、未知レジームは警告を出して 1.0 にフォールバック）。
  - position_sizing: 発注株数計算（calc_position_sizes）を実装。  
    - risk_based / equal / score 各方式対応。lot_size（単元）対応、stop_loss_pct に基づくリスク算出、max_position_pct や max_utilization による上限管理。
    - aggregate cap のスケーリングと、スケールダウン後の lot_size 単位での再配分ロジック（端数の扱い）を実装。
    - cost_buffer（手数料・スリッページ見積り）対応。

- リサーチ機能（kabusys.research）
  - factor_research: Momentum / Volatility / Value ファクター計算を追加（DuckDB 経由で prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（十分な履歴が無い場合は None）。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比など。
    - calc_value: PER / ROE 計算（raw_financials の最新レコードを参照）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）。
    - calc_forward_returns は複数ホライズンを同一クエリで取得しパフォーマンス配慮。
    - calc_ic は Spearman ランク相関を実装（同順位は平均ランク）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント化し ai_scores テーブルへ書き込む処理の基盤を実装。
    - ニュース集約ウィンドウ計算（JST ベースで前日 15:00 〜 当日 08:30 を UTC に変換）。
    - 銘柄ごとの記事トリム（最大記事数・文字数）、バッチ送信（最大 20 銘柄）、レスポンスの検証、スコアの ±1.0 クリップ、部分更新戦略（成功したコードのみ差し替え）を設計。
    - 再試行（429/ネットワーク/5xx）に対する指数バックオフ方針、API キーの引数/環境変数解決。
    - （注）ファイル末尾で処理が途中で切れているため一部実装が未完。

- ツール: Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - Paper Trading DB を対象に稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力する CLI を追加。
  - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200ms）と Pass/Fail 判定、日付フィルタ（--from/--to）、DB パス指定オプションを提供。
  - SQL の実行失敗（テーブル不存在等）に対する保護とデフォルト値フォールバックを実装。

- ユーティリティ（kabusys.utils）
  - process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。アクセス拒否や未対応 OS 時は警告を出してスキップ。
  - CPU affinity 設定関数（set_cpu_affinity）を追加。cpu_count のバリデーションと例外処理あり。

- パッケージメタ情報
  - __version__ = "0.1.0"。パッケージの __all__ に主要サブパッケージを追加。

Changed
- DuckDB / SQLite を組み合わせたデータアクセス設計を標準化（分析用に DuckDB、監視/発注ログに SQLite を使用）。
- run_* スクリプト起動時にプロセス優先度を最初に "high" にセットするように変更（プロセスの一貫性向上）。

Fixed
- .env パーサの不正入力やクォート処理、コメント処理の不整合を修正（エスケープ・引用符内の # を無視など）。
- 設定値のバリデーションを強化（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。
- ポートフォリオ重みが全て 0 の場合にゼロ除算や不正な重み配分が起きる問題を回避するフォールバックを追加（calc_score_weights）。
- ポーリング間隔取得処理で 0 や負値、非数が指定された場合にデフォルトへフォールバックするように改善（MONITOR_POLL_INTERVAL）。

Security
- （該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Notes / TODO
- news_nlp モジュールは設計が整っているが、コード末尾が途中で切れているため完全実装と細部テストが残る箇所がある（API 呼び出しの実装・DB 更新の最終化など）。
- position_sizing の price 欠損時の扱い（価格 0.0 のフォールバック）は TODO コメントあり。前日終値や取得原価を使う拡張を検討中。
- 将来的に lot_size を銘柄別に扱うための拡張（stocks マスタ参照）を想定。

以上が今回の初期リリース（推定）の主要な追加・改善点です。テスト、ドキュメント、未完成箇所の実装・検証を経て次バージョンでの改良を推奨します。