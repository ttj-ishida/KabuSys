# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。日付やバージョンはコードベースから推測して作成しています。

## [0.1.0] - 2026-04-12

### Added
- 基本パッケージ初期リリース:
  - パッケージ metadata: `kabusys.__version__ = "0.1.0"` を追加。
- 実行/監視用エントリポイント:
  - run_execution.py
    - ExecutionEngine の起動スクリプト。起動時にプロセス優先度を設定し、SQLite/ DuckDB に接続してエンジンを実行。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite DB を使用して本番 DB と完全に分離。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は本番の `sqlite_path` を環境にかかわらず使用する仕様。
- 環境設定管理:
  - config.py
    - プロジェクトルート自動検出（.git / pyproject.toml を探索）と `.env` / `.env.local` の自動読み込み機能を追加。OS 環境変数を保護する仕組み（protected）がある。
    - `.env` のパーサーはクォート、エスケープ、コメント（inline '#', export 形式）に対応。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化対応。
    - 各種設定プロパティを提供（DB パス、PID/kill flag、閾値、PAPER_FILL_MODE、KABUSYS_ENV, LOG_LEVEL など）。入力値検証（有効値チェック）を実装。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（score 降順・tie-break by signal_rank）。
    - 等重み配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコア 0 の場合は等重みへフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap`（既存ポジションのセクターエクスポージャーを基準に新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear のマッピング、未知レジームは警告のうえフォールバック）。
  - portfolio/position_sizing.py
    - 株数算出 `calc_position_sizes`（risk_based / equal / score の allocation method をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer（手数料・スリッページ考慮）を実装。
    - スケールダウン時に残余キャッシュを再配分するための残差処理を実装（再現性あるソート順）。
- リサーチ／ファクター計算:
  - research/factor_research.py
    - Momentum, Volatility, Value ファクター計算を DuckDB 上の `prices_daily` / `raw_financials` を参照して実装。
    - MA200、ATR20、20日平均出来高、各種ホライズンのリターン等を計算。データ不足時の None 処理を明確化。
  - research/feature_exploration.py
    - 将来リターン計算（`calc_forward_returns`）、IC（Information Coefficient）計算（`calc_ic`）、ファクター統計サマリー（`factor_summary`）、ランク付け `rank` を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research.__init__ に必要なエクスポートを追加。
- AI ニュース NLP:
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini / JSON Mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を実装。
    - 処理は銘柄ごとに記事を集約（上限記事数 / 上限文字数でトリム）、最大バッチ 20 銘柄、429/ネットワーク/5xx に対して指数バックオフでリトライ、レスポンスのバリデーション、スコアの ±1.0 クリップ、部分書換での失敗耐性（特定銘柄のみ削除→挿入）を備える。
    - ニュース収集ウィンドウを JST 基準（前日 15:00 〜 当日 08:30 JST）で定義するユーティリティを実装。
- ユーティリティ:
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収するプロセス優先度設定 (`set_process_priority`) を実装。`set_cpu_affinity` により CPU affinity を最初の N コアに固定可能。
    - 権限不足や未対応 OS の場合は警告ログでスキップする安全処理を実装。
- ツール:
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプト。期間指定可能（--from, --to, --db）。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算して PASS/FAIL を判定するしきい値を定義（稼働率 >=99%、成功率 >=90% 等）。

### Changed
- DB 接続・初期化の挙動:
  - 監視プロセス（run_monitoring）では、環境にかかわらず本番用 sqlite_path（settings.sqlite_path）を使用して監視テーブルを初期化・利用するよう明確化。
  - 実行プロセス（run_execution）では paper_trading 環境時に専用の paper_sqlite_path を使用して本番データと分離。
- .env ロードの優先順位:
  - OS 環境 > .env.local > .env の順で読み込み。`.env.local` は override=True により上書き可能だが OS 環境変数は保護される仕様。
- 設定値検証:
  - `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL` などで不正な値が設定された場合に ValueError を発生させるようにして早期検出を強化。
- 計算ロジックの堅牢化:
  - research / portfolio モジュールでデータ欠損時の None ハンドリングや 0 除算回避を徹底。
  - position_sizing の aggregate cap スケールダウン処理で端数配分の再現性を確保。

### Fixed
- フォールバックとログ出力:
  - MONITOR_POLL_INTERVAL が不正（非整数や 0 以下）の場合、デフォルトにフォールバックして警告ログを出すようにした（run_monitoring）。
  - process priority / cpu affinity 設定で権限不足や未実装メソッドが発生した際に例外を握り潰してアプリケーションを停止させないよう改良（警告ログ）。
- SQL クエリの堅牢化:
  - DuckDB / SQLite を用いたクエリで NULL 値伝播による誤判定を避けるための条件付け（true_range 等）を行い、カウント・平均が過大評価されないよう調整（factor_research.calc_volatility 等）。
- Paper Verification レポート:
  - DB が存在しない/テーブルが欠損している場合に例外で停止しないように、OperationalError を捕捉して N/A 表示や 0 件扱いするフェイルセーフを追加。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーの取り扱い:
  - `ai.news_nlp.score_news` は api_key 引数または環境変数 `OPENAI_API_KEY` のいずれかでキーを解決し、未設定時は ValueError を送出して明示的に失敗させるようにしている（暗黙的な無効化を避ける）。

注記:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートや履歴とは異なる可能性があります。
- ai/news_nlp.py の終端部が途中で切れている箇所があるため（スニペットの末尾）、その部分に関連する細部の挙動（部分的なログ文言や最終的な DB 書き込みの取り扱い）については推測に基づいて説明しています。必要であれば該当箇所の完全な実装をもとに更新できます。