# CHANGELOG

すべての注目すべき変更を記録します。  
このプロジェクトは Keep a Changelog の方針に沿って変更履歴を管理します。

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージ情報
  - パッケージの初期バージョンを設定（kabusys.__version__ = "0.1.0"）。

- 環境/設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml から検出）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
  - 柔軟な .env パーサ実装（export プレフィックス、クォート、エスケープ、インラインコメントの扱いに対応）。
  - 必須環境変数取得ヘルパー (_require) と各種設定プロパティを提供（DB パス、API トークン、監視閾値、環境判定等）。
  - 環境変数のバリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の許容値チェック）。

- 実行エントリ (src/kabusys/run_execution.py)
  - ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
  - 起動時にプロセス優先度を "high" に設定。
  - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 等の組み立て。
  - RiskManager 用の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を提供。
  - DuckDB および SQLite の接続確保、監視テーブルの初期化（init_monitoring_db）を実行。

- 監視エントリ (src/kabusys/run_monitoring.py)
  - SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60秒）。不正値はデフォルトにフォールバックし警告を出力。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
  - 起動時にプロセス優先度を "high" に設定し、例外はログに記録してポーリングを継続するフェイルセーフ。

- ユーティリティ: プロセス優先度 / CPU affinity (src/kabusys/utils/process_priority.py)
  - cross-platform（Windows / POSIX）でプロセス優先度を設定する set_process_priority を提供。
  - CPU affinity を最初 N コアに固定する set_cpu_affinity を追加。
  - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップする実装。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - 銘柄選定と配分計算（portfolio_builder）
    - select_candidates: スコア降順＋タイブレークで候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。全スコアが 0 の場合は等金額にフォールバックして警告。
  - セクター制約・レジーム乗数（risk_adjustment）
    - apply_sector_cap: 既存保有に基づくセクター集中チェックと候補除外（unknown セクターは除外対象にしない）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に応じた乗数を返却、未知値は警告して 1.0 にフォールバック。
  - 株数決定・リスク制限（position_sizing）
    - risk_based / equal / score の allocation_method をサポート。
    - 損切り率・リスク率に基づく株数算出、単元株（lot_size）丸め、1銘柄上限・集計上限（aggregate cap）を実装。
    - cost_buffer（手数料・スリッページ見積り）を加味した保守的コスト見積りと、利用可能現金に合わせたスケーリングロジックを実装。
    - スケーリング後の端数処理は lot_size 単位で残差が大きい順に追加配分する再現性あるアルゴリズム。

- 研究モジュール (src/kabusys/research/*)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離率を計算。
    - calc_volatility: ATR(20)、ATR 比率、平均売買代金、出来高比率を計算。
    - calc_value: EPS/ROE を用いた PER/ROE 計算（raw_financials から最新レコードを取得）。
    - DuckDB を用いた SQL ベースの高速実装。営業日ベースのウィンドウとデータ不足ハンドリングを考慮。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを計算（horizons のバリデーションあり）。
    - calc_ic: Spearman ランク相関に基づく IC 計算（3 銘柄未満で計算不能は None を返す）。
    - rank / factor_summary: ランク付けユーティリティと基本統計量（count/mean/std/min/max/median）を計算。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約し OpenAI API（gpt-4o-mini）でセンチメントを算出、ai_scores テーブルに書き込む処理を実装。
  - 日時ウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）とそれに基づく記事抽出。
  - 1 銘柄あたりの最大記事数 / 最大文字数制限（トークン肥大化対策）。
  - 最大 20 銘柄ずつのバッチ送信、JSON Mode を前提とした厳密なレスポンスバリデーション。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ（最大回数指定）。
  - スコアを ±1.0 にクリップし、部分失敗時にも既存データを保護するための差分更新戦略（DELETE → INSERT をコードで絞って実行）。
  - API キーは引数または OPENAI_API_KEY 環境変数から取得。未設定時は ValueError。

- ツール: Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
  - paper_trading DB を読み取り、稼働率・注文成功率・送信率・P95 レイテンシ等を算出して標準出力にレポート出力する CLI を追加。
  - CLI オプション: --from, --to（YYYY-MM-DD）および --db（SQLite ファイルパス）。環境変数 PAPER_TRADING_SQLITE_PATH も参照。
  - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を出力。
  - DB のテーブルが存在しない場合のフォールバック処理および欠測値対応を実装。

### Changed
- なし（初回リリースに相当するため、全て「追加」として扱っています）。

### Fixed
- なし（初回リリース）。

### Security
- OpenAI API キー等の機密情報は環境変数経由で受け渡す設計。自動 .env ロードは OS 環境変数優先かつ保護機能を持たせている。

Notes / 注意事項
- run_monitoring は監視データとして常に本番 sqlite_path を使用する設計です（KABUSYS_ENV に依らない挙動）。
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされます（配布パッケージ等で安全に動作するため）。
- 一部の機能（プロセス優先度 / CPU affinity）は OS 権限やプラットフォームに依存し、失敗時は警告ログを出してスキップします。
- DuckDB / SQLite / OpenAI クライアント等の外部依存があるため、実行環境に応じて事前にライブラリと環境変数の設定が必要です。

今後の予定（例）
- テストカバレッジの拡充、エンドツーエンドの統合テスト追加。
- 銘柄別 lot_size 対応や手数料モデルの高度化。
- ニュース NLP のスコア品質向上とキャッシュ戦略の追加。