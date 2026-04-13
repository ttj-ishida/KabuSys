# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
このプロジェクトの現行バージョン: 0.1.0

---

## [Unreleased]

- 現在準備中の変更はありません。

---

## [0.1.0] - 2026-04-13

初回リリース。コードベースから推測される主要な機能追加と振る舞いを以下にまとめます。

### Added
- 全体
  - パッケージ初期版を公開（__version__ = "0.1.0"）。
  - ロギングを利用した実行スクリプト群とユーティリティの整備。

- 設定 / 環境変数管理
  - Settings クラスを導入し、アプリケーション設定を環境変数経由で取得する仕組みを提供。
  - .env / .env.local の自動読み込み（プロジェクトルート判定付き）。OS 環境変数は保護され、.env.local で上書き可能。
  - 複雑な .env パーシング実装（export 句、クォート文字列、インラインコメント処理、保護キー付与）。
  - 各種環境変数プロパティを定義（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / PID/KILL フラグ 等）。
  - KABUSYS_ENV の検証（development / paper_trading / live）とログレベル検証。

- 実行エントリ / ランタイム
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（Mock クライアントを含む想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine.run_session() を実行。
    - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用してログを残す設計（monitoring テーブル初期化を実施）。
    - duckdb 接続もオープンしてモニタが必要とする分析を行う想定。
  - プロセス優先度設定を起動直後に行う（set_process_priority("high") を呼び出し）。優先度設定失敗時は警告ログを出力してスキップ。

- ユーティリティ
  - utils.process_priority:
    - クロスプラットフォームでプロセス優先度を変更する set_process_priority を提供（Windows と POSIX を吸収）。
    - CPU affinity を設定する set_cpu_affinity を提供（必要に応じて最初の N コアにピン留め）。
    - 権限不足や未対応 OS の場合は安全にスキップして警告ログを出す実装。
  - config 側で PID / kill flag のパスや監視閾値（CPU / Memory / Disk）の設定を提供。

- ポートフォリオ構築
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限をチェックし、上限超過セクターの新規候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告の上でフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数決定ロジック（allocation_method: risk_based / equal / score をサポート）。
    - 損切り・リスクベースの算定、単元株（lot_size）で丸め、ポートフォリオ総額に対する aggregate cap によるスケーリング、余剰キャッシュを利用した補正配分を実装。
    - cost_buffer による保守的見積りに対応。

- リサーチ（ファクター計算・解析）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離率を DuckDB SQL ウィンドウ関数で計算。
    - calc_volatility: ATR(20), 相対 ATR, 20 日平均売買代金, 出来高比を計算。NULL の取り扱いに注意。
    - calc_value: raw_financials から直近の財務データを取得して PER / ROE を計算（データ欠損は None）。
    - いずれも data/prices_daily / raw_financials を想定した DuckDB 接続ベース。
  - research.feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターン（LEAD を用いた一括取得）を計算。ホライズン検証（正の整数かつ <= 252）。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。有効レコードが少ない場合は None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算。

- AI / ニュース NLP
  - ai.news_nlp:
    - score_news: raw_news / news_symbols を集約して OpenAI API (gpt-4o-mini) にバッチ送信、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込むフローを実装。
    - バッチ処理（最大 20 銘柄/コール）、記事/文字数のトリミング（最大記事数・最大文字数制限）、429/ネットワーク/5xx 向けの指数バックオフリトライ、レスポンスの JSON バリデーション、スコアの ±1.0 クリップを実装。
    - タイムウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）用ユーティリティを提供。
    - API キーは引数または環境変数 OPENAI_API_KEY を使用し、未指定時は例外を送出。
    - フェイルセーフ設計: API 失敗時はログを出してスキップし、他銘柄のデータ保護を行う。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成 CLI を追加（--from / --to / --db オプション）。
    - system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、P95 レイテンシ等を計算。閾値（稼働率 99%、成功率 90%、送信率 95%、P95 200ms）に基づき PASS/FAIL 判定を出力。
    - P95 の計算、欠損データに対する安全なハンドリング（N/A 表示）を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 不正な MONITOR_POLL_INTERVAL 値（非数値や 0 以下）に対して警告を出し、デフォルト 60 秒へフォールバックする挙動を実装（run_monitoring）。
- 環境によりプロセス優先度 / CPU affinity の設定が失敗するケースに対して、例外を捕捉して警告ログを出しスキップするようにして安全性を向上。

### Deprecated
- 該当なし

### Removed
- 該当なし

### Security
- OpenAI API キーは引数または環境変数で明示的に供給する設計。未設定時は ValueError を投げることで不注意な公開を防止。

---

備考:
- 各モジュールの実装は DB（SQLite / DuckDB）とログテーブル・テーブル構造を前提としています。実行環境で DB スキーマが整備されていることが必要です。
- 一部関数内に TODO コメントが残っており、将来の改善（価格フォールバック、lot_size を銘柄別対応など）が想定されています。