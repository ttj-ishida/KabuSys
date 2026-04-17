# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-04-17
初期リリース。

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定（src/kabusys/__init__.py）。

- 実行用スクリプト
  - run_monitoring: SystemMonitor のポーリングループを起動する CLI スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート下の `data/stop_requested.flag` によるフラグ検知で行う。
    - 監視（monitoring）用 DB は環境に依らず本番 `sqlite_path` を使用する。
    - 起動時にプロセス優先度を "high" に設定する。
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用 DB（`data/paper_trading.db` など）に記録して本番 DB と分離。
    - 停止フラグ（`data/stop_requested.flag`）を検知して安全に停止する。
    - 実行中の PID を `data/execution.pid` に記録する想定の設定を反映。
    - 起動時にプロセス優先度を "high" に設定する。

- 環境設定管理
  - 自動 .env ロード機能実装（src/kabusys/config.py）。
    - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索して自動で `.env` / `.env.local` を読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
    - .env パーサーはコメント行、`export KEY=val` 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮。
  - Settings クラスを実装し、各種環境変数アクセスをプロパティで提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, 閾値設定など）。
  - Paper Trading 向けの設定:
    - `PAPER_TRADING_SQLITE_PATH`、`PAPER_FILL_MODE`（"instant"|"partial"|"never"|"reject"）をサポート。
  - 監視・閾値設定:
    - `CPU_THRESHOLD_PCT`, `MEMORY_THRESHOLD_PCT`, `DISK_THRESHOLD_PCT` を Settings で取得可能。
  - ログレベル・環境値のバリデーション（`KABUSYS_ENV` は "development" / "paper_trading" / "live"、`LOG_LEVEL` の有効値チェック）。

- モニタリング DB 初期化ユーティリティ参照
  - run スクリプトから `init_monitoring_db` を呼び出し、監視テーブルが存在することを保証（冪等に実行）。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でブレーク）
    - 等金額配分 `calc_equal_weights`
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバック）
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中制限 `apply_sector_cap`（既存保有からセクターごとの時価を計算し上限超過セクターの新規候補を除外、未分類 "unknown" は制限除外）
    - 市場レジームに応じた乗数 `calc_regime_multiplier`（"bull":1.0、"neutral":0.7、"bear":0.3、未知は警告の上で 1.0 にフォールバック）
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - 株数算出 `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score" をサポート）
    - 単元（lot_size）考慮、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）、cost_buffer による保守的見積り
    - aggregate cap 超過時のスケーリング処理（スケールダウンと lot_size 単位での再配分ロジックを実装）

- Execution コンポーネント（ランナー内で組み立て）
  - ExecutionEngine 起動フロー（src/kabusys/run_execution.py）における依存コンポーネントの組み立てを反映:
    - BrokerClientFactory によるブローカークライアント生成
    - OrderRepository / OrderManager / RiskManager / Reconciler の連携
    - RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）をサンプルとして設定

- 監視・プロセスユーティリティ
  - process_priority ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - Windows と POSIX（Linux/macOS/FreeBSD）に対応したプロセス優先度設定 `set_process_priority`（"high"|"normal"|"low"）
    - CPU affinity 設定 `set_cpu_affinity`（最初の N コアにピン留め）
    - 権限不足や未サポート環境では警告を出して安全にスキップ

- 研究（Research）モジュール
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200 乖離率）、Volatility（ATR20、相対 ATR、20日平均売買代金、出来高比率）、Value（PER, ROE）ファクターを DuckDB の SQL と Python を組み合わせて計算する関数を実装
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン算出 `calc_forward_returns`（複数 horizon を同時クエリで取得）
    - IC（Spearman ランク相関）算出 `calc_ic`
    - ファクター基本統計 `factor_summary`
    - ランキングヘルパ `rank`
  - research パッケージの公開 API を整備（zscore_normalize を含む）

- ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を対象に検証レポートを生成する CLI スクリプトを追加
    - デフォルトの合格基準を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）
    - system_status、trade_logs、risk_logs テーブルから指標を集計し、PASS/FAIL 判定および要因を出力

- ニュース NLP（AI）モジュール
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し OpenAI API（デフォルトモデル gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を計算して ai_scores テーブルへ書き込む処理を実装
    - 処理設計:
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を定義して記事を抽出
      - 1 回の API コールで最大 20 銘柄までをバッチ送信
      - レスポンス検証、スコア ±1.0 のクリップ、429/ネットワーク/5xx に対する指数バックオフリトライを実装
      - 部分成功時にも既存スコアを保護するため、対象コードのみ DELETE→INSERT で置換
    - OpenAI API キーは引数 `api_key` または環境変数 `OPENAI_API_KEY` から解決

### 変更
- なし（このバージョンは初回リリースのため変更履歴はありません）。

### 修正
- なし（初回リリースのため既存バグ修正履歴はありません）。

### 注意点 / 既知の制約
- news_nlp の実装は API 呼び出し・DB 書き込み周りで外部依存があり、実行環境に OpenAI API キーと対象テーブルが存在することが前提。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。
- position_sizing の lot_size は現状全銘柄共通の仮定（将来的に銘柄別の単元対応を予定）。
- 一部の TODO / 将来的な拡張コメントがソース内に残っている（例: price フォールバック、銘柄別 lot_size）。

### セキュリティ
- 外部 API（OpenAI）キーの取り扱いは環境変数ベースになっているが、運用上の安全対策（シークレット管理）は利用者側で行ってください。