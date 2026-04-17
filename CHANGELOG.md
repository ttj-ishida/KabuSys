# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-17

Added
- パッケージ初期リリース（__version__ = 0.1.0）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止はプロジェクト配下 data/stop_requested.flag によるフラグ検知で制御。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定（utils 内 set_process_priority を使用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、ExecutionEngine のスレッド起動と停止フラグ監視を実装。
    - 起動時にプロセス優先度を "high" に設定し、実行用 PID ファイル出力の仕組み（data/execution.pid）に対応。

- 設定管理
  - config.Settings（自動 .env ロード機能）
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 各種環境変数をプロパティで公開（J-Quants / kabu / LINE / DB パス / 監視しきい値 / システム設定など）。
    - 値検証を実装（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の検証など）。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE をサポート。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を追加（Windows・POSIX 差分を吸収）。
    - set_cpu_affinity(cpu_count) を追加（プロセスの CPU affinity 固定、権限不足や非対応 OS ではワーニングでスキップ）。

- ポートフォリオ構築モジュール（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を提供。
    - スコアが全て 0 の場合のフォールバック（等金額配分）やタイブレークロジックを実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有比率に基づく候補除外）を実装。unknown セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を実装（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ保守見積）に対応。
    - aggregate cap によるスケーリングと残差処理（lot 単位での追加配分）を実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200乖離を計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算（target_date 以前の最新財務データを使用）。
    - DuckDB 接続を受け取る SQL ベースの実装。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンに対する将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic: Spearman ランク相関（IC）計算（欠損・データ不足時は None）。
    - rank, factor_summary: ランク化・統計サマリユーティリティ（外部依存なし）。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news から銘柄別に記事を集約し、OpenAI (gpt-4o-mini) を用いたセンチメントスコアリングを実装。
    - バッチ（最大 20 銘柄）処理、トークン肥大対策（記事数・文字数制限）、429/ネットワーク/5xx への指数バックオフ再試行、レスポンス検証、スコアの ±1.0 クリップ、ai_scores テーブルへの置換的書き込み（DELETE→INSERT）などを想定した堅牢化方針を導入。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得（未設定時は ValueError）。

- CLI ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加。
    - コマンドライン引数 --from / --to / --db をサポート。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシなどを算出し PASS/FAIL 判定（デフォルト閾値をソースに明記）。
    - DB が存在しない場合のエラーメッセージや、テーブル欠如時の堅牢なフォールバックを実装。

Changed
- （初回公開のため該当なし）

Fixed
- （初回公開のため該当なし）

Deprecated
- （初回公開のため該当なし）

Removed
- （初回公開のため該当なし）

Security
- OpenAI の API キーに関する扱いは明示（env/引数での渡し方）。公開リポジトリでは .env 等に秘密情報を置かない運用を推奨。

Notes / 備考
- 設計上の重要点・制約
  - 多くのモジュール（portfolio / research / ai）は外部ブローカーや本番 API にはアクセスしない想定（DuckDB / SQLite / メモリ内計算中心）。
  - run_monitoring は監視用 DB へ常に本番 sqlite_path を使う設計（環境に依らず監視対象が一意になるよう意図）。
  - run_execution は paper_trading 環境で本番 DB と完全分離することで検証安全性を確保。
  - process_priority / set_cpu_affinity は権限不足や非対応プラットフォームで安全にスキップするようエラーハンドリング済み。
  - PAPER_FILL_MODE 等の環境変数は許容値チェックを行うため、運用時に誤設定を早期検出できる。
- 今後の改善候補（コード内 TODO に記載）
  - position_sizing: 銘柄別の lot_size を持たせる拡張（現状は共通 lot_size）。
  - risk_adjustment.apply_sector_cap: price 欠損時のフォールバック価格処理（前日終値や取得原価の利用）を検討。

--- 

（このファイルはコードベースのコメント・実装から推測して作成しています。実際のリリースノートとして使用する際は、変更履歴やリリース日などを正式な運用実績に合わせて修正してください。）