# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。日付・バージョンはコードベースから推測できる現時点のリリース相当（v0.1.0）としてまとめています。

## [0.1.0] - 2026-04-12

### 追加 (Added)
- 実行エントリ
  - run_execution: 実運用用の ExecutionEngine 起動スクリプトを追加。BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動する。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB を使用して本番 DB と分離する。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。プロセス優先度を上げる処理および DB 初期化を行う。

- 設定管理
  - config: .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml）。.env / .env.local の読み込み、export プレフィックス・引用符・インラインコメント・エスケープ対応のパーサを実装。自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを追加し、環境変数の取得と検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を提供。複数のパス設定（duckdb, sqlite, paper_sqlite, pid/kill フラグ）や閾値設定（CPU/MEM/DISK）を管理。

- ポートフォリオ構築
  - portfolio モジュールを実装:
    - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - position_sizing: 株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウンと残差配分のアルゴリズムを実装。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。

- 研究用ツール
  - research パッケージ:
    - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）。移動平均・ATR 等をウィンドウ関数で計算し、データ不足時の取り扱いも考慮。
    - feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク付けユーティリティを実装。
    - research/__init__.py で公開 API を整備（zscore_normalize を含む）。

- ニュース NLP（OpenAI）
  - ai/news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを生成し ai_scores テーブルへ書き込む処理を実装。以下の特徴を持つ:
    - ニュース収集ウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）
    - 銘柄ごとに記事を集約し文字数・記事数でトリム
    - 最大バッチサイズで API へ送信、429/タイムアウト/5xx を指数バックオフでリトライ
    - レスポンス検証とスコアの ±1.0 クリップ、部分成功時の DB 更新戦略（該当コードのみ置換）

- ユーティリティ
  - utils/process_priority: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、権限不足時には警告を出してスキップする。

- 運用ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成コマンドラインツールを追加。SQLite の trade_logs / system_status / risk_logs 等から稼働率・注文成功率・送信率・レイテンシを集計し、閾値に基づいて PASS/FAIL を判定する。--from / --to / --db オプションをサポート。DB 存在チェックやテーブル欠損時のフォールバックを実装。

### 変更 (Changed)
- run_monitoring の動作
  - 監視処理は KABUSYS_ENV にかかわらず「本番用 sqlite_path」を使用するようになっている（監視データの集約先は本番 DB が想定される点に注意）。

- run_execution の DB 接続
  - paper_trading 環境（Settings.is_paper が True）では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離するように変更。

- env ファイルの読み込み優先順位
  - OS 環境変数 > .env.local > .env の順で読み込み、.env.local は上書き（override=True）される。OS 環境変数は protected として上書きされない。

- エラー処理の堅牢化
  - run_monitoring のポーリングループで monitor.check_once() の例外をキャッチしてログを残し次回ポーリングへ継続するようにした（単一障害でループ停止しない）。
  - paper_verification_report は SQL 実行時の sqlite3.OperationalError を捕捉して、欠損テーブルがあってもレポート生成でクラッシュしないようにしている。

### 修正 (Fixed)
- 環境変数パーサの改善
  - .env のパース処理で引用符付き値のエスケープ処理や export プレフィックス、インラインコメントの扱いを改善。不正な行をスキップする仕様により読み込みの堅牢性を向上。

- position_sizing の配分ロジック
  - aggregate cap 超過時のスケールダウン処理で残差を lot_size 単位で再配分するロジックを実装し、端数処理の再現性（安定ソート）と安全弁（_max_per_stock の上限）を追加。

- research モジュールの NULL / データ不足処理
  - 移動平均・ATR 等でウィンドウ内の行数が不足する場合は None を返すようにし、誤った値計算を防止。

- utils/process_priority の例外ハンドリング
  - psutil による優先度設定や cpu_affinity 設定で権限不足や未実装 API が発生した場合に警告して処理を続行するようにした（クラッシュ回避）。

### 既知の問題 / 注意点 (Known issues / Notes)
- run_monitoring は明示的に本番 sqlite_path を使うため、開発環境や paper_trading 環境で監視データを分離したい場合は設定を見直す必要があります。
- ai/news_nlp の実装は API 呼び出し周りの堅牢化や DB 書き込みの完全なトランザクション処理まで含めてあるが、部分的に未表示/未掲載の実装がある（コード断片のため、実動作確認が必要）。
- PAPER_FILL_MODE 等の一部環境変数は厳格に検証されるため、既存の .env の値が無効な場合は起動時に例外が発生することがあります（設定ファイルの確認を推奨）。

### セキュリティ (Security)
- 特になし（コードから明示的に検出できるセキュリティ修正は無し）。

---

今後のリリース案内（例）
- 次のバージョンでは ai/news_nlp のリトライロジックの詳細ログ、API レート制御のより細かな制御、及び run_monitoring/run_execution のユニットテストを強化する予定です。