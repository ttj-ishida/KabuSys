# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

最新リリース: 0.1.0

## [Unreleased]

### Added
- 監視・実行周りの運用性改善（想定）
  - プロセス優先度や CPU affinity の設定ユーティリティを追加し、実行時に優先度を上げられるようにした（utils.process_priority）。
  - モニタリング用のポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能にした（run_monitoring）。

### Changed
- 将来的な拡張や堅牢化のための小規模リファクタリング（想定）
  - .env 読み込みの挙動やパース仕様に関する改善案（config._load_env_file / _parse_env_line）を踏まえた運用ルールの検討。

### Fixed
- 既知の小さな問題の調整（想定）
  - 環境変数の検証やデフォルトフォールバックの挙動に関する注意点の明確化。

---

## [0.1.0] - 2026-04-17

初期リリース（コードベースから推測してまとめた主要機能群）。

### Added
- 全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータアクセス基盤を導入（各モジュールが接続を受け取る設計）。

- 実行（Execution）
  - 実取引/ペーパートレーディング用の起動スクリプトを追加（run_execution）。
    - KABUSYS_ENV により paper_trading モードを判別。
    - paper_trading 時は paper 用の SQLite DB（data/paper_trading.db）を使用して本番 DB と分離。
    - Broker クライアント生成をファクトリ経由で行う（BrokerClientFactory）。
    - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler を組み立ててエンジンを起動。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定。

- 監視（Monitoring）
  - SystemMonitor のポーリング起動スクリプトを追加（run_monitoring）。
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用する旨の設計。
    - 停止フラグ検出でループを安全に終了。

- 設定管理（Config）
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順と上書きルールを明示（OS 環境変数は保護）。
  - 環境変数の厳密チェック機能を実装（必須変数取得時に未設定なら例外）。
  - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値など）。
  - PAPER_FILL_MODE や KABUSYS_ENV, LOG_LEVEL のバリデーション実装。

- ポートフォリオ構築（Portfolio）
  - 候補選定・重み計算（portfolio_builder）:
    - select_candidates（スコア降順 + tie-breaker）
    - calc_equal_weights（等金額）
    - calc_score_weights（スコア加重、全スコア0の場合は等配分へフォールバック）
  - リスク調整（risk_adjustment）:
    - apply_sector_cap（セクター集中制限）
    - calc_regime_multiplier（市場レジームに基づく投下資金乗数）
  - ポジションサイズ計算（position_sizing）:
    - calc_position_sizes（risk_based / equal / score の配分方式、ロット丸め、aggregate cap スケーリング、cost_buffer 考慮）

- 研究（Research）
  - ファクター計算（research.factor_research）:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、相対 ATR、20日平均出来高、出来高比）
    - calc_value（PER, ROE：raw_financials と prices_daily の組合せ）
    - 各関数は DuckDB 接続を受け取り SQL で計算する設計
  - 特徴量探索（research.feature_exploration）:
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman ランク相関による IC 計算、最小サンプル数チェック）
    - factor_summary（count/mean/std/min/max/median の統計サマリ）
    - rank（同順位の平均ランク付け、丸めによる ties 対応）

- AI / ニュース（AI）
  - news_nlp モジュールを追加（OpenAI を用いたニュースセンチメントスコアリング）。
    - ニュース収集ウィンドウ算出（JST を UTC に変換して比較）。
    - 銘柄ごとに記事を集約し、バッチ（最大 20 銘柄）で OpenAI に送信する設計。
    - レスポンス検証、スコアの ±1.0 クリップ、失敗時のフェイルセーフを実装。
    - 429 / ネットワーク断 / 5xx に対する指数バックオフリトライを設計。
    - 実装は JSON Mode を想定し、出力フォーマットの厳格化を要求。

- ツール（Tools）
  - Paper Trading 検証レポート生成スクリプトを追加（tools.paper_verification_report）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
    - データの存在チェックや SQLite の OperationalError を考慮した堅牢な集計。
    - 標準出力向けの整形されたレポートを生成。
    - CLI 引数で期間指定（--from, --to）および DB パス指定 (--db) に対応。

- ユーティリティ（Utils）
  - process_priority：プロセス優先度設定（Windows / POSIX の差分吸収）。
    - set_process_priority(level)（high/normal/low）。
    - set_cpu_affinity(cpu_count)（最初の N コアに固定）。
    - 権限不足や未対応 OS に対してはログ警告で安全にスキップ。
  - config の .env パーサはシングル/ダブルクォート、エスケープ、インラインコメント等に対応。

### Changed
- 分離設計
  - Paper Trading と Live を DB レベルで明確に分離（paper_trading 用 SQLite パスを設定可能）。
  - run_monitoring は環境に依らず本番 sqlite_path を参照するポリシーを明示。

- デフォルト値とバリデーション
  - MONITOR_POLL_INTERVAL のデフォルトは 60 秒。0 以下や不正値はログ出力後デフォルトにフォールバック。
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装（不正値は例外）。

- ロギング
  - 起動時に起動環境をログ出力するように統一（run_execution/run_monitoring）。
  - 予期せぬ例外や特定操作の失敗時は logger.exception / logger.warning で詳細を残す設計。

### Fixed
- 堅牢性改善
  - ファクター計算やポジション計算系でデータ欠損に対する None ハンドリングを徹底（例: ma200 の行数不足、ATR の null 伝播制御）。
  - Paper 検証レポートはテーブル未存在や OperationalError を捕捉して N/A を返すようにした。
  - process_priority / set_cpu_affinity は権限不足や未対応環境で例外を握り潰し安全にスキップする。

### Notes
- 現在のコードベースは「データ取得（prices_daily / raw_financials / raw_news 等）→ DuckDB/SQLite で集計 → Execution/Monitoring/Research/AI に渡す」設計を想定しており、外部 API 呼び出し（kabu/station, OpenAI 等）は抽象化（Factory / 設定引数）されています。
- 実運用時は環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）の設定が必須です。Settings._require により未設定時は起動時に明示的なエラーになります。
- news_nlp モジュールは robust なバッチ・リトライ設計を持つ一方で、API キー未設定時は ValueError を送出します。運用時は OPENAI_API_KEY の確実な供給が必要です。
- 今後の改善候補として、銘柄別 lot_size 管理、価格フォールバック（前日終値等）やさらに詳細なエラーレポート、単体テストカバレッジ強化が挙げられます（コード内 TODO コメント参照）。

---

（この CHANGELOG は与えられたソースコードの内容から推測して作成したものです。実際の変更履歴やリリース日付は実プロジェクトの記録に従って調整してください。）