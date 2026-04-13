# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。リリース日はコードベースから推測して記載しています。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 基本アプリケーション構成
  - パッケージのバージョンを設定 (kabusys.__version__ = "0.1.0")。
  - Settings クラスによる環境変数/ .env ファイルからの設定読み込み機構を実装。
    - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml 検出）を基準に `.env` → `.env.local` を読み込む（OS 環境変数を保護）。
    - 自動ロードを無効化するための env: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - 必須変数取得ヘルパー `_require()` を提供し、未設定時は ValueError を送出。

- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動するワークフローを実装。
    - プロセス起動時にプロセス優先度を `high` に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に依らず本番用の sqlite パス (`SQLITE_PATH` デフォルト `data/monitoring.db`) を使用。

- 環境変数・設定項目（Settings）
  - DB 関連: `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`
  - 監視関連: `PID_FILE_PATH`, `KILL_FLAG_PATH`, `KILL_FLAG_CLEAR_ON_START`
  - リソース閾値: `CPU_THRESHOLD_PCT`, `MEMORY_THRESHOLD_PCT`, `DISK_THRESHOLD_PCT`
  - Paper Trading 挙動: `PAPER_FILL_MODE`（有効値: "instant" | "partial" | "never" | "reject"、未定義/不正値は例外）

- Portfolio 構築モジュール（純粋関数群）
  - candidate 選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順、signal_rank でタイブレーク
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア正規化配分（全スコア 0 の場合は等金額配分へフォールバック）
  - セクター制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有エクスポージャが指定閾値を超えるセクターの新規候補を除外（"unknown" セクターは制限対象外）
    - calc_regime_multiplier: market regime に基づく投下資金乗数（"bull":1.0、"neutral":0.7、"bear":0.3。未知は 1.0 にフォールバック）
  - 発注株数決定（kabusys.portfolio.position_sizing）
    - calc_position_sizes: `risk_based` / `equal` / `score` の allocation_method をサポート
    - 単元株（lot_size）、cost_buffer（手数料・スリッページ見積）を考慮した集計上限（available_cash）に対するスケーリング処理を実装
    - portfolio_value に基づく per-stock 上限、単元丸め、残差処理による追加配分ロジックを実装

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。
  - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアにピン留め（None で無効）。
  - 権限不足や未対応プラットフォーム時には警告を出して処理をスキップするフォールトトレラントな実装。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB の prices_daily から算出
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を算出（欠損時は None）
    - calc_value: raw_financials から EPS/ROE を結合し PER/ROE を算出
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）で将来リターンを計算（horizons の入力検証あり）
    - calc_ic: スピアマンランク相関（IC）計算（有効レコード < 3 の場合は None）
    - factor_summary / rank: 基本統計量とランク変換ユーティリティ

- Tools
  - tools.paper_verification_report: Paper Trading 向け検証レポート生成 CLI を追加
    - CLI 引数: `--from`, `--to`, `--db`
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計し PASS/FAIL 判定を行う
    - P95 計算・各種 SQL クエリと堅牢なエラー処理を実装（テーブル未存在時は適切に N/A を返す）

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し OpenAI （gpt-4o-mini）を用いて銘柄別センチメントスコアを算出・ai_scores テーブルへ書き込む仕組みを実装
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、記事/文字数上限 (_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK)
    - 429 / ネットワーク / 5xx に対するエクスポネンシャルバックオフおよびリトライ
    - レスポンスの厳密な JSON 検証、スコア ±1.0 にクリップ
    - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` で指定

### 変更 (Changed)
- 監視 DB 初期化の冪等化
  - run_execution.py / run_monitoring.py 内で init_monitoring_db() を呼び、monitoring 用テーブルが存在することを保証（存在チェックの冗長化を回避）。

### 修正 (Fixed)
- 環境変数パーサの耐障害性向上（kabusys.config）
  - .env のパースでクォート文字のエスケープやインラインコメント処理に対応。`export KEY=val` 形式もサポート。
  - 不正な env 値（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）に対して明示的な ValueError を送出することで、起動時の早期検出を実現。

- ポーリング間隔指定の堅牢化
  - `MONITOR_POLL_INTERVAL` が 0 以下、または整数以外の場合はデフォルト（60 秒）へフォールバックし、警告をログ出力。

- position sizing の aggregate cap スケーリング
  - total_cost が available_cash を超える場合に縮小するロジックで、小口分配の端数処理と lot_size 単位での再配分を実装してより安定した発注量算出を実現。

### 注意 (Notes) / 既知の挙動
- run_monitoring は KABUSYS_ENV に関わらず本番用 `SQLITE_PATH` を使用します。監視データを paper_trading と分離したい場合は運用上の対処が必要です。
- set_process_priority / set_cpu_affinity は OS 権限やプラットフォームの機能に依存するため、失敗時は警告を出してスキップします（例: 一般ユーザーでの nice 値設定拒否）。
- apply_sector_cap は `sector_map` に存在しないコード（"unknown"）についてはセクター制限を適用しません（設計上の意図）。price が欠損（0.0）の場合はエクスポージャが過小評価される可能性があり、将来的にフォールバック価格の導入を想定しています。
- research モジュールの集計範囲は「営業日ベース」の窓を想定し、カレンダー日でのバッファを取る設計です。

### 破壊的変更 (Breaking Changes)
- なし（初期リリース相当）。ただし以下は運用上の注意点:
  - `PAPER_FILL_MODE` に不正値をセットすると Settings のアクセス時に例外が発生します。
  - `MONITOR_POLL_INTERVAL` の不正値はデフォルトにフォールバックしますが、意図しないポーリング間隔になる可能性があります。

### セキュリティ (Security)
- OpenAI API キーは環境変数 `OPENAI_API_KEY` または関数引数で受け取ります。ログや出力に API キーを露出しないように注意してください。

---

今後の改善案（参考）
- monitoring 用 DB を環境別に切り替える設定の追加（現状は常に本番パスを使用）。
- position_sizing の price フォールバックロジック（前日終値や取得原価）を導入し、price 欠損時の不具合を軽減。
- tools と ai の処理結果を自動化するための CLI / scheduler 統合（例えば daily cron の wrapper）。
- tests（ユニットテスト・統合テスト）およびモック対応の強化。