# Changelog

すべての重要な変更履歴をここに記載します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-16

### Added
- 全体
  - 初期リリース。パッケージメタ情報は `kabusys.__version__ = "0.1.0"` に設定。

- 起動スクリプト
  - run_monitoring（`src/kabusys/run_monitoring.py`）
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 停止制御はリポジトリルート配下の `data/stop_requested.flag` ファイルを監視して行う。
    - 監視処理実行時に例外が発生してもループを継続する（ログ出力して次回ポーリングまで待機）。
    - Monitoring は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用する設計。

  - run_execution（`src/kabusys/run_execution.py`）
    - ExecutionEngine 起動用スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）に記録して本番 DB と分離。
    - 停止フラグ（`data/stop_requested.flag`）の検知で実行エンジンを安全に停止。
    - 実行時の PID ファイルを書き出す（`data/execution.pid` を想定）。

- 設定・環境変数管理
  - `src/kabusys/config.py`
    - Settings クラスを追加。環境変数経由での設定取得をラップ。
    - 自動 .env ロード機能を追加（プロジェクトルートを `.git` または `pyproject.toml` で探索し、`.env` → `.env.local` の順で読み込み）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサ実装（`export ` プレフィックス対応、クォート付き値のエスケープ、インラインコメント処理、上書き制御、保護キー処理）。
    - 各種設定プロパティを実装：`duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, `kill_flag_path`, `cpu_threshold_pct` 等。
    - 入力値検証（`PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL` 等）。不正な値は例外を送出して早期に検知。

- モニタリング DB 初期化
  - `monitoring_db.init_monitoring_db` を呼び出して、起動時に監視用テーブルが存在することを保証する（冪等）。

- ユーティリティ
  - `src/kabusys/utils/process_priority.py`
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX の差を吸収）。
    - `set_process_priority(level: "high"|"normal"|"low")` を実装。アクセス権限等の失敗は警告出力してスキップ。
    - `set_cpu_affinity(cpu_count: int | None)` を実装（指定なしは何もしない）。権限不足や未対応プラットフォームは警告でフォールバック。

- ポートフォリオ構築（純関数）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 `select_candidates`、等金額配分 `calc_equal_weights`、スコア重み付け `calc_score_weights` を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックし WARNING を出力。

  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap` を実装（既存保有のセクター比率が閾値を超える場合に新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を実装（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知はフォールバック1.0）。

  - `src/kabusys/portfolio/position_sizing.py`
    - 株数決定ロジック `calc_position_sizes` を実装（risk_based / equal / score の各配分方式、単元株丸め、単銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り等）。
    - lot_size（単元）や cost_buffer の扱い、スケーリングのための残余配布アルゴリズムを実装。

  - `src/kabusys/portfolio/__init__.py` で公開 API を整備。

- リサーチ機能（DuckDB ベース）
  - `src/kabusys/research/factor_research.py`
    - モメンタム（1M/3M/6M）・MA200 乖離（ma200_dev）を計算する `calc_momentum` を実装。
    - ATR 等を利用したボラティリティ / 流動性指標を計算する `calc_volatility` を実装。
    - 財務データと株価から PER / ROE を計算する `calc_value` を実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン、入力検証あり）。
    - IC（スピアマンのρ）計算 `calc_ic`（欠損・データ件数チェックを行う）。
    - ランキングユーティリティ `rank`（同順位は平均ランクで処理）。
    - ファクター統計サマリ `factor_summary`（count/mean/std/min/max/median）。

  - `src/kabusys/research/__init__.py` で主要関数と zscore_normalize を公開（`kabusys.data.stats` から提供）。

- AI ニュース NLP（OpenAI 連携）
  - `src/kabusys/ai/news_nlp.py`
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（`gpt-4o-mini` を想定）でセンチメントを算出して ai_scores テーブルへ書き込む処理を実装。
    - 処理フロー、ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST = UTC に換算）計算 `calc_news_window` を実装。
    - バッチ送信（最大 `_BATCH_SIZE`）、記事数・文字数トリム（1銘柄あたり最大記事数・最大文字数）でトークン肥大化を抑制。
    - 429/ネットワーク/5xx に対するエクスポネンシャルバックオフリトライと最大リトライ回数を実装。
    - API キー引数または環境変数 `OPENAI_API_KEY` でキーを取得。未設定時は ValueError を送出。
    - レスポンスの厳密な JSON フォーマット検証、スコアの ±1.0 クリッピング、部分成功時に既存スコアを保護するための部分置換戦略（DELETE WHERE → INSERT）などを設計。

- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 検証レポート生成スクリプトを追加。
    - コマンド例:
      - python -m kabusys.tools.paper_verification_report
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - Paper Trading DB（`PAPER_TRADING_SQLITE_PATH` 環境変数または `--db` オプション、デフォルト `data/paper_trading.db`）からデータを集計。
    - 指標と閾値（稼働率、注文成功率、送信率、P95 レイテンシ等）に基づく PASS/FAIL 判定を出力。
    - 実装したクエリは system_status / trade_logs / risk_logs テーブルを参照し、欠損テーブルに対しては安全に N/A を返す。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Notes / Usage Tips
- 環境変数関連
  - 自動 .env 読み込みはプロジェクトルートの検出に依存する（`.git` または `pyproject.toml` が存在するディレクトリ）。配布後などでプロジェクトルートが特定できない場合、自動ロードはスキップされます。
  - OS 環境変数は `.env` 自動ロード時に保護され、`.env.local` による上書きは OS 環境変数を上書きしないよう配慮されています（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使えば自動ロード自体を無効化可能）。
  - `PAPER_FILL_MODE` は "instant" | "partial" | "never" | "reject" のいずれかである必要があります。無効な値は例外になります。
  - `KABUSYS_ENV` は "development" | "paper_trading" | "live" のいずれかを指定する必要があります。

- 実行・運用
  - 監視（run_monitoring）と実行エンジン（run_execution）はそれぞれ停止フラグファイルによる外部制御を想定しています（`data/stop_requested.flag`）。
  - run_execution は paper_trading 環境時に DB を完全分離するため、本番 DB に影響を与えません。
  - プロセス優先度設定は起動直後に行われますが、権限不足等で実施できない場合は警告ログを出して継続します。

### Breaking Changes
- なし（初回リリース）。

--- 

将来的なリリースでは、各コンポーネント（AI スコアリングの完全実装、実行エンジンの詳細、監視テーブル仕様、テストカバレッジ、ドキュメントの充実など）について個別に詳細な変更点を記載していきます。