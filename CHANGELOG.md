Changelog
=========

すべての注目すべき変更をまとめます。  
このファイルは "Keep a Changelog" のスタイルに準拠します。

[Unreleased]
------------

- （現在なし）

[0.1.0] - 2026-04-16
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
- 実行エントリ/デーモン類
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - 停止制御はプロジェクトルート/data/stop_requested.flag を参照。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視用 DB の一貫性確保）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db、環境変数で上書き可）と MockBrokerClient を使用して本番 DB と完全に分離。
    - Engine は別スレッドで実行され、停止フラグ検知で安全に停止する。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用途）。
    - export KEY=val 形式やクォート付き値（バックスラッシュエスケープ対応）、インラインコメントルール等に対応した .env パーサを実装。
    - Settings クラスを追加し、主要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス類、監視閾値、KABUSYS_ENV 等）をプロパティ経由で取得・検証する API を提供。
    - PAPER_FILL_MODE の有効値検証（instant/partial/never/reject）や KABUSYS_ENV の検証（development/paper_trading/live）を実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - 銘柄候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全てが 0 の場合は等分にフォールバックし、警告ログを出力。
  - portfolio.risk_adjustment
    - セクター集中制限を適用する apply_sector_cap を実装（sell_codes により当日売却予定銘柄を除外可能、"unknown" セクターは除外しない挙動）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング）を実装。未知レジームはフォールバック。
  - portfolio.position_sizing
    - 株数計算 calc_position_sizes を実装:
      - allocation_method: "risk_based" / "equal" / "score" に対応。
      - 単元株（lot_size）丸め、max_position_pct による per-stock 上限、available_cash による aggregate cap を実装。
      - コストバッファ (cost_buffer) を考慮した保守的見積り、スケールダウン時の残差配分ロジック実装。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度を設定する set_process_priority を実装（Windows / POSIX に対応、失敗時は警告を出してスキップ）。
    - set_cpu_affinity を追加し、カレントプロセスを最初の N コアにピン固定可能（アクセス権限不足や未実装環境では安全にスキップ）。

- リサーチ / ファクター計算
  - research.factor_research
    - DuckDB を用いたファクター計算関数を実装: calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（ATR20、相対 ATR、出来高系）、calc_value（PER, ROE）。
    - SQL ベースで高速に銘柄毎のファクターを計算し、欠損条件は None で扱う。
  - research.feature_exploration
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、horizons 検証あり）。
    - IC（Spearman）算出 calc_ic、ランク化ユーティリティ rank、ファクター統計 summary 関数 factor_summary を実装。
  - research パッケージは zscore_normalize を外部モジュールからエクスポートする仕組みを用意。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成スクリプトを追加（CLI から実行可能）。
    - 指標: 稼働率（uptime）、注文成立率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。閾値はソース内定義（稼働率 99% 等）。
    - DB 存在チェック、期間フィルタ、各種クエリの例外ハンドリングにより堅牢にレポートを生成。

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news テーブルを OpenAI（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込む処理の骨格を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST、内部は UTC で扱う）、記事のトリム (_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK)、バッチ送信（_BATCH_SIZE=20）やレスポンス検証、±1.0 でのクリップ、リトライ戦略（指数バックオフ）等を設計。
    - OPENAI_API_KEY の未設定チェックを実装（未設定時は ValueError）。

Changed
- パッケージ初回リリースのため履歴は追加主体。設計上の重要点:
  - 監視プロセス（run_monitoring）は常に本番の sqlite_path を使う（KABUSYS_ENV に依存しない）点に注意。テスト環境で監視を分離したい場合はファイルパス周りを上書きする必要あり。
  - .env 読み込みの既定動作により、プロジェクトルートの .env/.env.local が起動時に環境変数を設定するため、既存の OS 環境変数との優先順位に注意。

Fixed
- 多数の入力検証とフォールバックを実装して不整合・欠損データに対する堅牢性を向上:
  - MONITOR_POLL_INTERVAL が不正な値だった場合にデフォルトへフォールバック。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値検証を追加し、不正時に明示的な例外を送出。
  - DuckDB / SQLite クエリ周りでデータ不足時に None を返す等の保護ロジックを追加（ツール／リサーチ系）。

Security
- OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数から解決する仕様。キー未設定時は処理が失敗するため、呼び出し側で取り扱いに注意。

Breaking Changes / Notes for Migration
- 監視プロセスが常に production sqlite_path を参照する点は意図的な設計だが、既存環境で監視データを分離していた場合は挙動が変わる可能性があります。テストや paper_trading 向けに監視 DB を分離したい場合はコードまたは環境変数でパスを切り替えてください。
- .env 自動ロード機能がデフォルトで有効化されています。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings のプロパティは未設定や不正な値で ValueError を発生させます。デプロイ環境では必須環境変数の設定を確認してください（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

開発者向けメモ
- 実装済みだが外部参照されるコンポーネント（例: monitoring_db, SystemMonitor, ExecutionEngine 内部の詳細、BrokerClientFactory の具象実装など）はこの変更履歴の記載対象外のため、個別で確認してください。
- ai.news_nlp の一部（データ取得・API 呼び出しループの続き）はファイル末尾で切れているため、完全動作させるには続きの実装・テストが必要です。

--- 

以上。必要であればリリースノートを英語版に翻訳したり、各モジュールごとの詳細な変更差分（関数一覧・API 仕様）を別途作成します。どの形式がよいか指示ください。