# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
解釈: 主要な追加・変更点・修正を記録しています。

## [Unreleased]

## [0.1.0] - 2026-04-13

初回リリース。本リポジトリに含まれる主要機能と挙動を以下にまとめます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 実行エントリ・起動スクリプト
  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視処理は環境にかかわらず本番の `sqlite_path` を使用する設計。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。
  - run_execution:
    - ExecutionEngine の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用の SQLite DB（`PAPER_TRADING_SQLITE_PATH`, デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - Broker クライアントのファクトリ利用、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のセッション実行フローを追加。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートの判定: `.git` または `pyproject.toml` を探索）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
  - `.env` / `.env.local` 読み込みルール（override/protected）を実装。export 形式やクォート／コメントに対応したパーサを提供。
  - 必須環境変数チェック (`_require`) を実装（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` 等）。
  - 各種設定プロパティを提供（DuckDB/SQLite パス、PID / kill flag パス、閾値、環境名・ログレベルの検証、paper trading 関連設定等）。
  - `PAPER_FILL_MODE` のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。

- 監視 DB 初期化ユーティリティ呼び出し
  - `init_monitoring_db` を実行して監視用テーブルの存在を保証（冪等）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - シグナル選定 (`select_candidates`)、等重配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。スコアが全て 0 の場合は等金額配分にフォールバックして警告を出す。
  - risk_adjustment:
    - セクター集中制限を行う `apply_sector_cap` を実装（既存保有からセクター別エクスポージャーを計算し上限超過セクターの新規候補を除外。`unknown` セクターは上限適用外）。
    - 市場レジームに基づく乗数 `calc_regime_multiplier` を実装（"bull":1.0、"neutral":0.7、"bear":0.3、未知レジームは警告後 1.0 でフォールバック）。
  - position_sizing:
    - 発注株数算出ロジックを実装（`allocation_method` により "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）で丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合はスケールダウン）を実装。スケールダウン時は残差に基づく優先配分を行う。
    - `cost_buffer` による保守的コスト見積りを加味。

- 研究用・ファクター計算（kabusys.research）
  - factor_research:
    - momentum / volatility / value のファクター計算関数を実装（DuckDB 接続を受け取り SQL ウィンドウ関数等で計算）。
    - MA200 乖離、ATR、平均売買代金、volume ratio、PER/ROE 等を計算。
  - feature_exploration:
    - 将来リターン計算 (`calc_forward_returns`)、IC（スピアマン ρ）計算 (`calc_ic`)、ファクター統計サマリ (`factor_summary`)、ランク付けユーティリティ (`rank`) を実装。
    - 外部ライブラリに依存せず標準ライブラリで実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（`gpt-4o-mini`）でセンチメント評価し `ai_scores` テーブルへ書き込む `score_news` を実装。
  - 処理の概要:
    - 対象時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算して記事を集約。
    - 銘柄ごとに記事数 / 文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を適用。
    - 最大バッチ 20 銘柄で API 送信、429/ネットワーク/5xx に対する指数バックオフによるリトライ実装。
    - レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ。
    - 成功した銘柄群のみを対象に部分的に DB の置換（DELETE → INSERT）して他銘柄の既存データ保護を考慮。
  - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` で指定。未設定時は ValueError を送出。

- ユーティリティ
  - process_priority:
    - プロセス優先度設定 (`set_process_priority`) を実装（Windows と POSIX に対応し、未対応 OS はスキップ）。
    - CPU affinity 設定 (`set_cpu_affinity`) を実装。権限不足や未サポート環境では警告を出してスキップ。
    - 失敗時に AccessDenied 等を捕捉して警告ログ。

- ツール
  - tools/paper_verification_report:
    - Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを算出し、定義済み閾値で PASS/FAIL を判定（しきい値はソース内定数で定義）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。デフォルト DB は `data/paper_trading.db`。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数で API キーやパスを扱う設計。必須のシークレット（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY）は設定チェックを行うよう実装。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings 経由で必須チェックされます。未設定だと起動時に ValueError。
  - OPENAI_API_KEY は news_nlp の `score_news` 呼び出し時に必要。
- .env 自動読み込み:
  - プロジェクトルート検出に .git または pyproject.toml を使用するため、配布後に cwd が変わっても既定の .env 読み込みは保たれます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB の取り扱い:
  - 監視（run_monitoring）は常に `Settings.sqlite_path`（本番想定）を使用します。paper_trading の分離が必要な場合は run_execution を `paper_trading` 環境で実行してください（run_execution は paper 環境で専用 DB を使用）。
  - `init_monitoring_db` は起動時に呼び出され監視テーブルの存在を保証します（冪等）。
- OpenAI 利用:
  - `score_news` は OpenAI のモデル `gpt-4o-mini` を想定。API レスポンスの形式が仕様と合致しない場合は該当チャンクをスキップする設計です。
- 既知の注意点:
  - position_sizing の `_max_per_stock` は価格が 0 または欠損の場合 0 を返すため、その場合はその銘柄はスキップされます。将来的には価格フォールバックの追加を検討。
  - apply_sector_cap は sector_map に無い銘柄を "unknown" 扱いにし、上限適用対象外とします。

---

（今後のリリースでは、Breaking changes / Deprecations / Fixed を適宜追記してください。）