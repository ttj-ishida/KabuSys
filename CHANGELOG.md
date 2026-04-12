CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
バージョン番号はパッケージの __version__ に合わせています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-12
--------------------

Added
- 全般
  - 初回リリース。パッケージメタ情報を `kabusys.__version__ = "0.1.0"` として導入。

- 実行エントリ / 常駐プロセス
  - run_monitoring 起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60秒）。不正値は警告してデフォルトにフォールバック。
    - 起動時にプロセス優先度を "high" に設定（`utils.process_priority.set_process_priority` を利用）。
    - 監視用 SQLite は環境に依らず本番用 `sqlite_path` を使用して接続し、`init_monitoring_db` を呼び出してテーブル準備を行う。
    - `SystemMonitor` の `check_once()` をポーリングループで定期実行し、例外はログに記録してループ継続。KeyboardInterrupt をハンドリングして終了処理を行う。
  - run_execution 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper 専用 SQLite (`paper_sqlite_path`) と Mock ブローカーを使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - `BrokerClientFactory` によりブローカークライアントを生成。`ExecutionEngine` / `OrderManager` / `OrderRepository` / `RiskManager` / `Reconciler` を組み立ててセッションを実行。
    - `RiskManager` に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入し、初期ポートフォリオ値を broker.get_available_cash() から取得。

- 設定管理
  - `kabusys.config` モジュールを追加。
    - プロジェクトルートを `.git` または `pyproject.toml` で探索して自動的に `.env` / `.env.local` をロードする仕組みを実装（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` のパースは export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメントを考慮して堅牢に実装。
    - 環境変数取得のラッパ `Settings` を提供し、必須値チェックや型変換、値検証（`KABUSYS_ENV`, `PAPER_FILL_MODE`, `LOG_LEVEL` 等）を行うプロパティ群を実装。
    - デフォルトの DB パス（`data/monitoring.db`、`data/paper_trading.db`、`data/kabusys.duckdb`）や PID/KILLフラグ設定などのプロパティを提供。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - シグナルのスコア降順選択 (`select_candidates`)。
    - 等金額配分 (`calc_equal_weights`) とスコア加重配分 (`calc_score_weights`)。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中上限チェックで新規候補を排除する `apply_sector_cap` を実装。既存保有時価を考慮し、"unknown" セクターは除外対象外として扱う。
    - 市場レジームに応じた乗数 `calc_regime_multiplier` を実装（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは警告して 1.0 フォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数決定ロジック `calc_position_sizes` を実装。
      - `risk_based` / `equal` / `score` の配分方式に対応。
      - 損切り率・lot_size（単元）丸め、1銘柄上限・全体投下上限（aggregate cap）のスケーリングを実装。スケール後の残差は lot 単位で再配分するアルゴリズムを採用。
      - 価格欠損やゼロ価格を安全に扱う（ログ出力してスキップ）。

- リサーチ／ファクター群
  - `kabusys.research.factor_research`
    - DuckDB 接続に対して利益率・移動平均乖離（MA200）を含むモメンタム計算 (`calc_momentum`) を実装。
    - ATR/相対ATR/平均売買代金/出来高比を含むボラティリティ計算 (`calc_volatility`) を実装。
    - 財務データと株価から PER/ROE を計算するバリュー計算 (`calc_value`) を実装。raw_financials の最新レコード取得は ROW_NUMBER を利用。
  - `kabusys.research.feature_exploration`
    - 将来リターンの計算 (`calc_forward_returns`)、スピアマンランク相関による IC 計算 (`calc_ic`)、ランク付けユーティリティ (`rank`)、ファクター統計サマリー (`factor_summary`) を実装。
    - 外部依存（pandas 等）を用いず標準ライブラリと DuckDB のみで実装。

- AI / ニュース NLP
  - `kabusys.ai.news_nlp` を追加。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）を計算するユーティリティを実装。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、銘柄ごとに上限記事数・文字数でトリムして OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を取得する設計。
    - 最大バッチサイズ、リトライ（429/5xx/ネットワーク断に対する指数バックオフ）、レスポンスのバリデーション、スコアの ±1.0 クリップ、部分失敗に対応する DB 書き換え戦略（対象コード絞り込みで保護）などの設計ガイドラインを組み込む。
    - OpenAI API キー未設定時に明示的にエラーを投げる（安全策）。※（実装の一部はファイル末尾で途切れていますが、全体の設計方針と主要処理は含まれています）

- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を SQL から集計し CLI で出力。期間フィルタ（--from / --to）、DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）に対応。
    - P95 計算、欠損データハンドリング、指標閾値（稼働率 99% 等）と Pass/Fail 判定を実装。
    - DB テーブルが存在しない場合でも堅牢に動作（OperationalError を捕捉してデフォルト値でレポート）。

- ユーティリティ
  - `kabusys.utils.process_priority`
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する `set_process_priority` 実装。psutil を使用し、アクセス権限や未対応 OS を安全にハンドリングして警告ログでフォールバック。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供（入力検証あり、失敗時は警告してスキップ）。

Changed
- .env ロード順の確立
  - OS 環境変数 > .env.local > .env の順でロードされるように実装。OS 環境変数は protected として上書き不可。
- 監視/実行スクリプトの DB 選択ロジック
  - 監視（run_monitoring）は環境に関わらず本番 sqlite_path を使用する方針を明記。実行（run_execution）は paper_trading 環境では paper_sqlite_path を使用することで本番 DB と分離。

Fixed
- ロバストネス向上
  - 各種集計関数や計算でデータ欠損（NULL / 0 / 欠落行）を慎重に扱う実装になっており、ゼロ除算や None 伝播による誤計算を回避。
  - 複数箇所で try/finally による DB 接続クローズを導入。

Security
- 設定値チェック強化
  - 必須環境変数未設定時に早期に ValueError を発生させる `_require` 実装。
  - OpenAI API キーの未設定検出と明確なエラーメッセージ。

Notes / その他
- ドキュメント参照
  - 多くの関数は内部コメントで設計指針（PortfolioConstruction.md, StrategyModel.md 等）や TODO を参照しており、将来的な拡張（lot_size を銘柄別にする等）を想定している。
- テスト / 安全弁
  - 多くの関数は外部副作用を持たない純関数として実装されており、ユニットテストで検証しやすい設計になっている。

今後の予定（提案）
- AI ニュース NLP のレスポンス→DB 書込部分の完全実装とエンド・ツー・エンドの統合テスト。
- モニタリング／エンジン間のメトリクス定義書化（どの指標をどの頻度で採取するか）。
- portfolio / sizing ロジックのパラメータ最適化用ユーティリティ追加。