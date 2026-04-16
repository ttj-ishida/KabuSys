# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初回公開リリースとして以下を記録します。

## [0.1.0] - 2026-04-16

### 追加 (Added)
- 基本パッケージ情報を追加
  - kabusys.__version__ = "0.1.0" を設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) を監視して安全にループを抜ける実装。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を利用したブローカークライアント作成、ExecutionEngine をスレッドで実行、停止フラグで優雅に停止するロジックを実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境読み込み
  - config.Settings クラスを追加。環境変数から各種設定値を安全に取得するプロパティ群を提供。
    - DB パス (DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH)
    - PID / kill flag path
    - 監視閾値 (CPU / Memory / Disk)
    - KABUSYS_ENV 検証 (development, paper_trading, live)
    - PAPER_FILL_MODE 検証 (instant/partial/never/reject)
    - LOG_LEVEL 検証
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - .env 自動読み込み機構を実装
    - プロジェクトルート（.git または pyproject.toml を探索）を基に .env と .env.local を読み込む。
    - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの強化
    - export KEY=val 形式のサポート、クォートされた値のエスケープ処理、インラインコメントの扱いを実装。
    - protected 引数により既存 OS 環境変数の上書きを防止。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で重み算出。スコア合計が 0 の場合は等分配にフォールバック（warning 出力）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を抑えるための候補フィルタ。sell_codes（当日売却予定）を除外して判定。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をマッピング、未知は 1.0 で警告）。
  - portfolio.position_sizing
    - calc_position_sizes: 複数の allocation_method ("risk_based", "equal", "score") に対応した株数算出ロジック。
      - 単元株（lot_size）丸め、ポジションごとの上限、aggregate cap（available_cash）によるスケールダウン処理、cost_buffer を用いた保守的見積りを実装。
      - スケールダウン後の端数配分を残差（fractional remainder）に基づき公平に配分する仕組み。

- リサーチ / ファクター計算（DuckDB ベース）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算。
    - calc_value: raw_financials と prices_daily を使った PER・ROE の算出（最新の report_date を参照）。
    - DuckDB SQL を用いた高効率な実装。
  - research.feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターン（LEAD）を計算。
    - calc_ic: スピアマンのランク相関（IC）を計算（同順位は平均ランクで処理）。有効レコードが 3 未満の場合は None。
    - factor_summary / rank: 基本統計量とランク化ユーティリティを実装。
  - research.__init__ で主要関数と zscore_normalize をエクスポート。

- ニュース NLP（AI スコアリング）骨格
  - ai.news_nlp モジュールを追加（OpenAI クライアントを利用）。
    - タイムウィンドウの計算（JST ベース → UTC 変換）。
    - 銘柄ごとの記事集約、1 銘柄あたり最大記事数・文字数トリムの方針。
    - OpenAI へ銘柄を最大 20 件ずつバッチ送信する設計、429/ネットワーク/5xx に対する指数バックオフ再試行。
    - レスポンスの JSON 検証とスコアの ±1.0 クリップ、ai_scores テーブルへの部分置換（DELETE + INSERT）方針。
    - API キー未設定時に ValueError を送出。
    - （注）モジュールは API 呼び出し・DB 書き込みの骨格と安全性設計を含む実装。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。
    - コマンドライン引数で期間指定 (--from / --to) と DB パス指定 (--db) を受け付け。
    - system_status, trade_logs, risk_logs テーブルから稼働率・注文成功率・送信率・P95 レイテンシなどを集計し、閾値（稼働率 99%、成功率 90% 等）に基づき PASS/FAIL 判定を出力。
    - P95 計算、欠損時の N/A 表示、SQLite の存在チェックを実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）を抽象化してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定（アクセス拒否や未実装は警告でスキップ）。
    - psutil を利用。失敗時は例外を送出せず警告ログでフォールバック。

- DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を run スクリプトで呼び出して監視テーブル存在を保証（冪等）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- .env パーサーの耐性向上
  - クォート内のバックスラッシュエスケープ対応、コメント扱いの厳密化により .env ファイルの誤解析を低減。

- position_sizing の配分ロジック
  - aggregate cap によるスケーリングと lot_size に基づく端数処理を導入し、過剰発注や非整数単位の発注を防止。

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キー（ai.news_nlp）は引数または環境変数 OPENAI_API_KEY で供給するよう明示。未設定時は ValueError を発生させ、誤った無条件送信を防止。

---

注記:
- 本 CHANGELOG はソースコードからの推測に基づき作成しています。実際の動作や外部依存（OpenAI, ブローカー API 等）については運用環境での検証を推奨します。
- ai.news_nlp モジュールは API 呼び出しや DB 書き込みの詳細実装（例: _fetch_articles の完全な実装やエラー分岐の全網羅）が別途必要な場合があります。運用前にテストを行ってください。