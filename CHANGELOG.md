# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日や詳細はソースから推測して記載しています。

## [Unreleased]

### Added
- 全体
  - パッケージ初期版を追加。モジュール群（execution / monitoring / portfolio / research / ai / tools / utils / config 等）を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルトポーリング間隔は 60 秒。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能。不正値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 起動時にプロセス優先度を "high" に設定。停止はプロジェクト直下の `data/stop_requested.flag` によって検知。
    - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - DuckDB と SQLite の接続を組み合わせて利用。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジン起動・実行中は `data/stop_requested.flag` により停止処理を行う。PID ファイルを設定してプロセス管理。

- 設定管理
  - config.Settings クラスを導入。環境変数から各種設定を取得するユーティリティ。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーは以下に対応:
    - 空行 / コメント行（`#`）の無視
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの場合のインラインコメント処理（`#` の直前が空白/tab のとき）
  - 各種設定プロパティを提供（DB パス、OpenAI / Kabu API 関連、監視閾値、PID/kill フラグパスなど）。
  - `PAPER_FILL_MODE` の検証（有効値: "instant" | "partial" | "never" | "reject"）。不正値は例外を送出。
  - `KABUSYS_ENV` / `LOG_LEVEL` の検証と補助プロパティ（is_live / is_paper / is_dev）。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（タイブレークに signal_rank）でソートして上位 N を返す。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分を提供。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、セクター集中超過のセクターから候補銘柄を除外する。売却予定銘柄を計算から除外するオプションを実装。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）を返す。未知レジームは警告して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method (`risk_based`, `equal`, `score`) に基づいて発注株数を計算。単元株（lot_size）丸め、1銘柄上限、aggregate cap（投下資金が available_cash を超える場合のスケーリング）、コストバッファ（手数料/スリッページ想定）を実装。
    - aggregate スケーリング時の残差配分（lot 単位）を fractional remainder に基づき再配分して再現性を確保。

- 研究（research）
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照して各種ファクター（モメンタム、MA200乖離、ATR、平均売買代金、PER/ROE 等）を計算。
    - スキャン範囲のバッファと窓サイズを明示してデータ不足時は None を返す設計。
  - research.feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得。horizons の検証（正の整数かつ <= 252）を実施。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。データが不足（有効レコード < 3）の場合は None を返す。
    - rank / factor_summary: 同順位の平均ランク付け、カラムごとの基本統計量（count/mean/std/min/max/median）を実装。None と非有限値を除外して計算。

- ニュース NLP（AI）
  - ai.news_nlp
    - raw_news を集約して OpenAI（デフォルト model: gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込むロジックを実装。
    - スコアは ±1.0 にクリップ。1 回の API で最大 20 銘柄を処理するバッチング、記事数・文字数トリム（1銘柄あたり最大記事数と最大文字数）を導入。
    - API エラー（429, ネットワーク, タイムアウト, 5xx）に対して指数バックオフでリトライ（上限回数あり）。
    - レスポンスのバリデーションを実施し、部分失敗時でも既存の他銘柄のスコアを保護するための差分置換（DELETE/INSERT の工夫）で DB 書き込みを行う設計。
    - target_date に対するニュース収集ウィンドウ計算ユーティリティ（JST→UTC 変換）を提供。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite（`data/paper_trading.db` を想定）から検証レポートを生成する CLI を実装。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等。閾値を定義して PASS/FAIL を判定する自動判定ロジックを実装。
    - P95 計算、日付フィルタ、DB 存在チェック、各種 SQL クエリのフェールセーフ（テーブル未存在時の扱い）を実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を提供。Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。権限不足や未対応環境では警告を出して安全にスキップ。
    - set_cpu_affinity(cpu_count) を提供し、最初の N コアにプロセスをピン留めする機能を追加（引数検証あり）。失敗時は警告を出してスキップ。

### Changed
- .env 自動ロードの動作を明確化
  - OS 環境変数は保護され、`.env.local` は `.env` の上書きに使われる。ただし保護された OS 環境変数は上書きされない。
- DB 初期化
  - run_execution と run_monitoring の起動フローで、監視用テーブルの初期化（init_monitoring_db）を冪等に呼ぶことで起動時に監視テーブルが存在することを保証。

### Fixed
- 環境変数パースの堅牢化
  - クォート内のエスケープや export プレフィックス、インラインコメントの扱いを改善し、.env の実運用で起こる様々な形式に耐性を持たせた。
- ポーリング間隔の健全性チェック
  - `MONITOR_POLL_INTERVAL` が不正（非数値や 0/負）な場合にデフォルトへフォールバックしてログ出力するようにした（time.sleep での ValueError 回避）。
- position_sizing のスケーリングと端数処理
  - aggregate cap を超えた場合のスケーリング処理を改善し、lot_size 単位での端数再配分（残余キャッシュに基づく）を行ってより安定した配分を実現。
- 多くの箇所で例外やエラー時にログを残してフェイルセーフに継続するよう改善（monitoring の check_once() 中の例外捕捉、AI API エラーのリトライとスキップ等）。

### Security
- OpenAI API キーの取り扱い
  - score_news は引数の api_key または環境変数 `OPENAI_API_KEY` を参照し、未設定時は ValueError を投げることで鍵が明示的に設定されていることを要求。

### Notes / Known limitations
- ai.news_nlp は大量テキストを扱うためトークン増大対策（記事・文字数トリム）を導入しているが、実運用ではさらにトークン数・料金最適化の検討が必要。
- position_sizing の価格欠損時（price が 0.0 や欠損）に関する注釈を残しており、将来的に前日終値や取得原価を用いたフォールバックを検討する旨の TODO コメントあり。
- research モジュールは DuckDB に対するテーブル構成（prices_daily / raw_financials 等）が前提。データ不足時は None を返すことで上位レイヤーでのハンドリングを促す設計。

---

## [0.1.0] - 2026-04-16
- 初回公開リリース。上記「Added」に記載の機能群を含む。

----------

参考:
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/