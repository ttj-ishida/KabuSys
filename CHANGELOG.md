# Changelog

すべての変更は「Keep a Changelog」スタイルに従って記載しています。重大な変更のみを列挙しています。

## [0.1.0] - 2026-04-17

初回リリース（ベース機能群を実装）

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `__version__ = "0.1.0"`。
  - パッケージ公開用の主要モジュール構成（data, strategy, execution, monitoring 等の名前空間エクスポート）。

- 設定 / 環境変数読み込み (`kabusys.config`)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 行パーサーを実装し、`export KEY=val` 形式、クォート／エスケープ、行内コメントの取り扱いをサポート。
  - OS 環境変数を保護するための上書きルール（protected set）を実装。
  - 自動ロードを無効にする `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - Settings クラスを実装し、各種設定値をプロパティとして提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, 各種閾値、`env` / `is_live` / `is_paper` 等）。
  - 設定値のバリデーションを実装（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等）。

- 実行 / 監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を設定し、SQLite / DuckDB に接続。
    - `paper_trading` 環境向けに専用 SQLite（`data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine 起動を実装。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）による起動制御を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する設計。

- 監視 DB 初期化
  - `init_monitoring_db` を呼び出して監視用テーブルを冪等に初期化する処理を run_* スクリプトで組み込み（DuckDB/SQLite 両対応のワークフロー）。

- ユーティリティ (`kabusys.utils.process_priority`)
  - クロスプラットフォームでプロセス優先度（Windows と POSIX）を設定する `set_process_priority(level)` を実装。
  - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を実装（権限不足や未対応環境では警告してスキップ）。
  - 失敗時に例外を投げずログ警告でフォールバックする堅牢な実装。

- ポートフォリオ構築 (`kabusys.portfolio`)
  - 銘柄選定・重み付け (`portfolio_builder`) を実装
    - `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）
    - `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等分配にフォールバック）
  - リスク調整 (`risk_adjustment`) を実装
    - `apply_sector_cap`（セクター集中上限チェック、売却予定銘柄の除外、"unknown" セクターは免除）
    - `calc_regime_multiplier`（market regime に応じた投下資金乗数。`bull`/`neutral`/`bear` を定義、未知の値は警告して 1.0 にフォールバック）
  - ポジションサイジング (`position_sizing`) を実装
    - `calc_position_sizes`：`risk_based` / `equal` / `score` の割当方式をサポート
    - 単元（lot）丸め、per-stock 上限、aggregate cap（利用可能現金に収まるようスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した安全な配分ロジック
    - スケーリング後の余剰キャッシュを残差（fractional remainder）に基づき安定的に配分するアルゴリズム

- リサーチ / ファクター計算 (`kabusys.research`)
  - `factor_research` を実装
    - `calc_momentum`（1M/3M/6M リターン、MA200 乖離）
    - `calc_volatility`（ATR20、相対ATR、平均売買代金、出来高比）
    - `calc_value`（PER、ROE（raw_financials から最新を取得））
    - DuckDB の SQL ウィンドウ関数を活用した効率的な実装
  - `feature_exploration` を実装
    - `calc_forward_returns`（複数ホライズンの将来リターンを一括計算、horizons の検証）
    - `calc_ic`（スピアマンのランク相関による IC 計算、データ不足で None を返す）
    - `rank`, `factor_summary`（ランク付けと基本統計量サマリ）

- AI ニュース NLP (`kabusys.ai.news_nlp`)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化して `ai_scores` に書き込む処理を実装
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事集約、1 銘柄あたりの文字数・記事数制限、銘柄ごとのバッチ（最大 20 銘柄）で API 呼び出し
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（リトライ）を実装、API キー未設定時は明示的なエラー
  - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護するための限定 DELETE→INSERT 戦略を採用
  - `calc_news_window(target_date)` を提供（UTC naive datetime のウィンドウ計算）

- ツール (`kabusys.tools.paper_verification_report`)
  - Paper Trading の検証レポート生成ツールを追加（コマンドライン実行可能）
  - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等
  - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）
  - 日付フィルタ（--from / --to）をサポート、DB パスは引数または環境変数で指定可能
  - レポートは標準出力に人間向けフォーマットで出力

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- 環境変数パース・ロード時の細かな不具合対策を実装
  - 空行・コメント行（#）・export プレフィックス・クォート付き値・エスケープシーケンスに対応。
  - override フラグと protected キーを用いた上書き制御で OS 環境変数の保護を実現。
- run_monitoring のポーリング間隔取得時に不正値を検出するとログ警告を出しデフォルトにフォールバック（time.sleep に負の値を渡さないための保護）。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

---

注意:
- 多くのモジュールは DuckDB / SQLite のスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等）を前提としています。実行には適切な DB を用意してください。
- run_execution/run_monitoring/run の各スクリプトは OS 権限（プロセス優先度設定やファイル作成）に依存する箇所があります。権限不足時は警告でフォールバックする設計ですが、本番運用時は必要な権限を確認してください。