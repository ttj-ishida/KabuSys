CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成しています。

Unreleased
----------

- （現在の開発中または未リリースの変更はここに記載します）

0.1.0 - 2026-04-12
------------------

Added
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - 起動時にプロセス優先度を高優先度に設定。
    - KABUSYS_ENV により paper_trading モードをサポート（MockBrokerClient を利用し paper_trading 用 DB に記録して本番と分離）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて engine.run_session() を呼び出す。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env/.env.local の読み込みルール（OS 環境変数は保護、.env.local は上書き）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
    - .env 行パーサ（export 形式、クォート文字列、インラインコメントの取り扱い）を実装。
    - Settings クラス：J-Quants / kabu API / LINE / DB /監視/システム関連のプロパティを提供し、値検証（有効な KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を行う。

- 監視・レポートツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を実行。
    - 日付範囲フィルタ（--from/--to）と DB パス指定（--db）に対応。
    - DB 存在チェックや SQLite の OperationalError 耐性を組み込み。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、同点は signal_rank でタイブレーク）。
    - 等金額配分、スコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/position_sizing.py
    - risk_based / equal / score の各配分方式に対応した株数計算。
    - 単元株（lot_size）丸め、per-position 上限 / aggregate cap（利用可能現金に対するスケーリング）を実装。
    - cost_buffer による手数料・スリッページ見積りを考慮。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存保有を基にセクターごとの時価を計算し上限超過セクターを候補から除外。
    - レジーム乗数（calc_regime_multiplier）："bull"/"neutral"/"bear" に応じた投下資金乗数を返す。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り momentum / volatility / value ファクター（mom_1m/3m/6m, ma200_dev, atr_20, atr_pct, avg_turnover, per, roe など）を計算。
    - ウィンドウ不足時の None 扱いなど堅牢な実装。
  - research/feature_exploration.py
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関による IC 計算、ファクター統計サマリー、ランク付け実装。
    - 標準ライブラリのみで実装（pandas 等非依存）。
  - research/__init__.py で主要関数をエクスポート（zscore_normalize を含む）。

- AI ニューススコアリング
  - ai/news_nlp.py
    - DuckDB の raw_news / news_symbols / ai_scores を使い、OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores に書き込む処理を実装。
    - タイムウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を提供。
    - バッチサイズ制御、1 銘柄当たりの最大記事数・文字数トリム、API エラー（429 / ネットワーク / 5xx / タイムアウト）に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップを実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) で Windows と POSIX を吸収した優先度設定を実装（psutil 利用）。
    - set_cpu_affinity(cpu_count) による CPU affinity 固定機能を追加。
    - 例外（権限不足・未サポート機能）時は警告ログを出してスキップする堅牢な実装。

Changed
- 監視・実行の起動処理でプロセス優先度を最初に設定するよう統一（set_process_priority("high")）。
- run_execution と run_monitoring で DuckDB 接続と SQLite 初期化処理を導入（init_monitoring_db を呼び出して監視テーブルの存在を保証）。
- 設定ロードの優先順位を明文化（OS 環境 > .env.local > .env）し、OS 環境変数は保護されるように実装。

Fixed
- MONITOR_POLL_INTERVAL の不正値に対するフォールバック（0 以下や非整数が指定された場合にデフォルト 60 秒を使用）を実装。
- .env パーサのクォート処理とインラインコメント処理を改善し、複雑な値やエスケープを正しく読み取るようにした。
- Paper Trading モードでは専用の SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番データと完全分離するように修正。

Deprecated
- なし

Removed
- なし

Security
- .env 自動ロード時に OS 環境変数を上書きしないよう保護（protected set の導入）。
- OpenAI API キーは明示的に引数で与えるか環境変数 OPENAI_API_KEY を参照。未設定時は例外を発生させ安全に失敗する仕様。

Notes / Known issues / TODO
- portfolio.position_sizing の価格欠損時の扱い（price が 0.0 の場合にエクスポージャーが過少見積りされる点）は TODO コメントとして残してあり、将来的に前日終値や取得原価でのフォールバックを検討予定。
- 単元株数 lot_size は現状グローバル固定（既定 100）。将来的に銘柄別の lot_map を導入する予定。
- news_nlp の OpenAI コールは JSON Mode を前提に実装されているため、API のレスポンス仕様変更やレート制限ポリシーに注意が必要。

署名
----
この CHANGELOG はリポジトリ内のソースコードから機能や修正内容を推測して作成しています。実際のリリースノートや運用上の記録と差異がある場合は、プロジェクト管理者の記述を優先してください。