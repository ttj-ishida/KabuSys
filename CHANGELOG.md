# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-16
初回リリース。本リリースでは日本株自動売買システムのコア機能群（実行・監視・ポートフォリオ構築・リサーチ・ツール・ユーティリティ・AI ニューススコアリング）を実装しています。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイントを実装。
    - KABUSYS_ENV が `paper_trading` の場合、専用の paper_trading SQLite DB を使用して本番 DB と完全分離する挙動をサポート。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の非同期実行（スレッド）を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による外部停止ハンドリングを実装。
    - RiskManager の設定に初期ポートフォリオ値取得（broker.get_available_cash()）を導入。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きに対応（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は常に本番用 sqlite_path を使用する設計（環境に依存しない監視DB接続）。
    - stop flag ファイル検出による安全終了と例外ハンドリングを導入。
    - 起動直後にプロセス優先度を "high" に設定する動作を追加。

- 設定管理
  - config.py
    - 環境変数 / .env(.local) の自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env ファイルパーサを実装（export 形式対応、引用符あり／なしの扱い、エスケープ処理、インラインコメントの取り扱い）。
    - .env のロードは OS 環境変数を保護（protected）し、.env.local は上書き可能に設定。
    - Settings クラスを提供し、各種設定取得をプロパティで提供（DB パス、paper_trading DB パス、PID ファイルパス、監視しきい値、環境判定など）。
    - 入力値検証を実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の許容値チェック）。未設定の必須変数は明示的に例外を送出。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補選定（スコア降順、signal_rank で同点タイブレーク）select_candidates を実装。
    - 等金額配分 calc_equal_weights と スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター時価を計算し、上限超過セクターの新規候補を除外、unknown セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - position sizing 実装（allocation_method: risk_based / equal / score）。
    - risk_based: 損切り率・リスク許容率からベース株数算出、単元株（lot_size）で丸め、最大保有比率で制限。
    - equal/score: 重みに基づく個別配分、max_utilization と per-position 上限を考慮。
    - aggregate cap の実装：全銘柄合計コストが利用可能現金を超える場合、スケールダウンして単元株丸め、端数は fractional_remainder に基づき残余キャッシュで補正。
    - コストバッファ（cost_buffer）を考慮して保守的にコストを見積もるロジックを実装。
  - portfolio/__init__.py による公開 API の整理。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算群を実装（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）、データ不足時は None を返す仕様。
    - calc_volatility: 20 日 ATR、ATR の相対値（atr_pct）、20 日平均売買代金、volume_ratio を計算（NULL 伝播制御等を考慮）。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（target_date 以前の最新財務データを銘柄毎に取得）。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度に取得する効率的なクエリを実装（horizons のバリデーションあり）。
    - calc_ic: ファクター値と将来リターンの Spearman（ランク）相関を計算する実装（ties の平均ランク、最小レコード数チェック）。
    - rank, factor_summary: ランク付け、基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - research/__init__.py による公開 API の整理。
  - 設計指針として DuckDB と標準ライブラリのみを用いることを明記。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント（-1.0〜1.0）を評価し、ai_scores テーブルへ書き込む処理の骨子を実装。
    - ニュース収集ウィンドウ（JST ベース）を計算する calc_news_window を実装（UTC 変換の説明含む）。
    - API バッチサイズ、トークン肥大化対策（記事数・文字数制限）、レスポンスの JSON バリデーション、スコアの ±1.0 クリップ、最大リトライ/指数バックオフ等の設計を実装。
    - フェイルセーフ設計: API 失敗時は個別チャンクをスキップし、他の銘柄処理を継続。
    - （注）ファイル末尾はコード断片で終わっているため、実働部分は今後の完成を想定。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを実装。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - P95 計算、閾値による PASS/FAIL 判定、日付フィルタ（--from / --to / --db オプション）対応。
    - DB が存在しない場合やテーブルが無い場合のフォールバック（例外捕捉）を実装。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォームに依存しないプロセス優先度設定ユーティリティを実装（Windows: HIGH_PRIORITY_CLASS、POSIX: nice 値）。
    - CPU affinity 設定関数 set_cpu_affinity を追加（利用可能なコア数を超える指定は全コア使用へフォールバック）。
    - アクセス権限不足や未対応 OS に対する警告処理を実装。
  - utils パッケージ初期化ファイルを追加。

- パッケージ管理
  - kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- DB 関連
  - SQLite と DuckDB の併用設計: 監視・トレードログ等のトランザクションは SQLite、分析用途は DuckDB を使用する方針がコード全体で採用されています。
- 安全性・フェイルセーフ
  - 外部 API 呼び出し（OpenAI・ブローカー等）は失敗時にシステム全体が停止しないよう設計されています（例: リトライ、部分スキップ、例外ログ）。
- 設定読み込み
  - .env 自動読み込みはデフォルトで有効。テストなどで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 未完 / TODO
  - ai/news_nlp.py の末尾が断片で終了しており、記事集約・API 呼び出しの最終ループ以降の完全実装は今後の作業が想定されます。
  - position_sizing の price 欠損時の扱いについては TODO コメントで改善案（前日終値や取得原価のフォールバック）を残しています。

----

メジャーな機能追加や API 変更を行う際は、この CHANGELOG を更新してください。