# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴ではなく、ソースコードに現れる機能追加・振る舞い・制約等を要約しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-16
初回リリース相当。システム全体のコア機能（設定読み込み、監視・実行の起動スクリプト、ポートフォリオ構築、ポジションサイズ計算、リスク調整、研究用ファクター計算、ニュースNLP スコアリング、ユーティリティ）が追加されています。

### Added
- 全体
  - パッケージバージョンを追加: `kabusys.__version__ = "0.1.0"`。
  - DuckDB / SQLite を用いたデータ処理基盤を利用する設計を導入（各種モジュールが接続を受け取って処理する）。

- 設定管理（kabusys.config）
  - 環境変数自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml から検出して .env / .env.local を読み込む）。
  - .env のパーサー実装：
    - export KEY=val 形式に対応。
    - シングル・ダブルクォートのエスケープ処理を考慮した値のパース。
    - クォート無し値のインラインコメント処理（'#' の前が空白/タブの場合のみコメントとして扱う）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
  - 必須環境変数取得用ヘルパー `_require()` を実装（未設定時に ValueError を送出）。
  - 各種設定プロパティを追加（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, 各種閾値、`env`, `log_level` 等）。
  - `PAPER_FILL_MODE` のバリデーションを実装（有効値: "instant" | "partial" | "never" | "reject"）。
  - `KABUSYS_ENV` のバリデーション（"development", "paper_trading", "live"）。

- 実行 / エンジン起動（run_execution）
  - `ExecutionEngine` 起動スクリプトを追加。
  - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離する動作を導入。
  - Broker クライアントのファクトリ利用（`BrokerClientFactory.create(settings)`）。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて `ExecutionEngine` を起動するフローを実装。
  - エンジン用 PID ファイルの取り扱い・停止フラグ (`data/stop_requested.flag`) による外部停止制御を導入。
  - 例外発生時にも DB 接続をクローズする安全な finally 処理。

- 監視（run_monitoring）
  - `SystemMonitor` をポーリング実行する起動スクリプトを追加。
  - 環境にかかわらず「本番」用 `sqlite_path` を参照する（監視は常に本番 DB を使う設計）。
  - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。無効値時はデフォルトにフォールバックして警告を出す。
  - 停止フラグファイル (`data/stop_requested.flag`) によるループ終了、KeyboardInterrupt による graceful shutdown を実装。
  - プロセス優先度を高に設定して起動する（後述のユーティリティを使用）。

- 監視 DB 初期化
  - `init_monitoring_db(sqlite_conn)` を利用して監視用テーブルの存在を保証（冪等に初期化）。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用検証レポート生成ツールを追加。コマンドラインから日付範囲指定（--from/--to）や DB パス指定（--db）が可能。
  - 検証指標・閾値を定義:
    - 稼働率 >= 99.0%
    - 注文成功率（Fill Rate） >= 90.0%
    - 送信率（Send Rate） >= 95.0%
    - P95 レイテンシ <= 200 ms
  - system_status / trade_logs / risk_logs などのテーブルから指標を集計し、Pass/Fail 判定を出力。
  - P95 の算出ロジックを実装、欠損値ハンドリングを実装。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定・重み算出（portfolio_builder）を追加:
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等分配にフォールバックし警告）。
  - セクター集中度制限・レジーム乗数（risk_adjustment）を追加:
    - apply_sector_cap: 既存保有のセクター暴露を計算し上限超過セクターの候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック。
  - ポジションサイジング（position_sizing）を追加:
    - 複数 allocation_method をサポート ("risk_based", "equal", "score")。
    - 単元株（lot_size）単位で丸め、1 銘柄上限・aggregate 上限・手数料/スリッページのバッファ考慮（cost_buffer）。
    - aggregate cap 超過時のスケーリングと端数（fractional remainder）に基づく再配分ロジックを実装。
    - price 欠損時のスキップやログ出力を行う。

- 研究モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（window バッファ採用）。
    - calc_volatility: ATR20、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と株価から PER / ROE を算出（最新財務レコードを target_date 以前から取得）。
    - すべて DuckDB 接続を受け取り SQL で集計・計算する設計。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンに対する入力検証あり。
    - calc_ic: Spearman 相当のランク相関（Information Coefficient）を実装（同順位は平均ランク処理）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
    - rank ユーティリティを提供（同順位の平均ランク処理）。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news から銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別の ai_score を ai_scores テーブルへ書き込む処理を追加。
  - 特徴的な設計:
    - タイムウィンドウは JST ベースで前日 15:00 ～ 当日 08:30（内部は UTC 変換）。
    - 1 銘柄当たり最大記事数 / 文字数を制限（トークン膨張対策）。
    - 1 API 呼び出しで最大 20 銘柄をバッチ処理。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（上限あり）。
    - レスポンスは厳密な JSON を期待（{"results":[...]}）。スコアは ±1.0 でクリップ。
    - API キー未指定時は例外を送出。
    - 部分失敗時の DB 更新の安全策（対象コードを限定して DELETE -> INSERT を実行）を意図。

- ユーティリティ（kabusys.utils.process_priority）
  - プロセス優先度設定ユーティリティを追加:
    - set_process_priority(level): Windows / POSIX を吸収して優先度（high/normal/low）を設定。アクセス権限不足や未対応 OS では警告を出しスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにピン留め。引数検証と例外ハンドリングあり。
  - run_monitoring / run_execution 起動時にプロセス優先度を "high" に設定する呼び出しを追加。

### Changed
- （初版のため該当なし）  
  - 設計上の決定点（監視が常に本番 DB を見る、paper_trading は専用 DB）を明示的に反映。

### Fixed
- （初版のため該当なし）  

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーが未設定の場合は明示的にエラーを出すことで、秘密鍵の未設定運用ミスを検知しやすくしています。

## 注意事項 / マイグレーションノート
- 監視（run_monitoring）は常に `Settings.sqlite_path`（デフォルト `data/monitoring.db`）を使用します。paper_trading 環境でも監視は本番 DB を参照する設計になっているため、環境ごとの DB 分離を期待する場合は運用ルールを確認してください。
- Paper Trading 実行 (`KABUSYS_ENV=paper_trading`) 時は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）が用いられ、本番 DB と完全に分離されます。検証レポートツールもこの DB を対象に動作します。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後に自動ロードを望まない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `PAPER_FILL_MODE` など一部環境変数は値のバリデーションが厳密化されています（無効値は ValueError）。運用環境の .env を確認してください。
- OpenAI 連携機能を利用する場合は `OPENAI_API_KEY` の設定が必須です。API 呼び出しのレート制限や費用に注意してください。

もし特定モジュール（例: position_sizing の挙動、news_nlp の完全なフロー、ExecutionEngine の詳細な停止シーケンスなど）についてより詳細な CHANGELOG 行や注記を追加したい場合は、対象ファイルや実際のコミット差分を提供してください。