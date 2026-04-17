# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
重大な変更、追加された機能、既知の制約等は下記を参照してください。

※日付は本コードベース解析日（2026-04-17）を使用しています。

## [Unreleased]

### 注意事項
- 本ファイルは現行ソースコードの内容から推測して作成した CHANGELOG です。実際のコミット履歴が存在する場合はそちらを優先してください。
- ソース内に "TODO" や未完了の実装注記が残っている箇所があります（詳細は「既知の制約」参照）。

---

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として導入。

- 実行エントリ / 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定する処理を導入。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB（`data/paper_trading.db` デフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を定義。
    - 実行エンジンはスレッドで起動し、プロジェクトルートの `data/stop_requested.flag` を監視して安全に停止可能。

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応（デフォルト 60 秒、無効値は警告を出してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する設計（環境による監視 DB 切替を行わない仕様）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（`data/stop_requested.flag`）によるループ終了制御を実装。

- 設定 / 環境変数管理
  - config.py: Settings クラスを導入し、環境変数を集中管理。
    - .env / .env.local の自動読込機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化に対応。
    - .env パーサ実装（export 形式、引用符付き値、コメントの扱い、エスケープ処理等に対応）。
    - 多数のプロパティを追加（J-Quants / kabu API / LINE API / DB パス / 監視閾値 / 環境種別検証など）。
    - `PAPER_FILL_MODE` の検証（有効値: instant|partial|never|reject）や `KABUSYS_ENV` の検証（development|paper_trading|live）を実装。
    - Settings インスタンス `settings` をモジュールレベルで提供。

- ユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。
    - set_process_priority(level: "high"|"normal"|"low") を提供。Windows の優先度クラス / POSIX の nice 値に対応。
    - set_cpu_affinity(cpu_count: int | None) を追加（指定コア数に固定）。権限不足や未対応プラットフォームは警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を制限する候補フィルタ（既存保有比率に基づき新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based/equal/score）に基づいて発注株数を計算。lot_size 単位で丸め、aggregate cap によるスケールダウンと余剰割当ロジックを実装。手数料・スリッページ見積り用 cost_buffer を考慮。

- 研究 (research)
  - research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB 接続を受け取り prices_daily / raw_financials テーブルからファクターを算出。
    - 計算に必要なウィンドウ長（MA200, ATR20 等）や不足データ時の None 扱いを実装。
  - research/feature_exploration.py:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括で取得。
    - calc_ic: スピアマンランク相関（IC）計算を実装（結合／欠損値除外／有効データが 3 件未満で None）。
    - factor_summary, rank: 基本統計量サマリ、同順位の平均ランク処理（丸めで ties 検出漏れ対策）。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news から銘柄別に記事を集約し、OpenAI API（gpt-4o-mini）を用いたセンチメントスコアを ai_scores テーブルへ書き込む処理を導入。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を実装（UTC への変換）。
    - 1 銘柄あたりのトークン肥大化対策（最大記事数・最大文字数トリム）、最大バッチサイズ（20銘柄）やレスポンス JSON 検証、スコア ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライ等を設計に含める。
    - API キー参照は引数優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を SQLite の paper_trading DB（デフォルト: data/paper_trading.db）から集計して標準出力にレポート。閾値（稼働率99%、成功率90% 等）に基づく PASS/FAIL 判定を実装。
    - コマンドライン引数 --from/--to/--db をサポート。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db が呼び出される形で、監視テーブルの存在を保証する処理を run_monitoring / run_execution で導入（冪等）。

### Changed
- （初版リリースのため特記事項なし）

### Fixed
- （初版リリースのため特記事項なし）

### Removed
- （初版リリースのため特記事項なし）

### Security
- OpenAI API キーや重要なトークン等は Settings 経由で環境変数から取得する設計。自動 .env ロードは OS 環境変数を保護する仕組み（protected set）を持つ。

### Known issues / Limitations
- ai/news_nlp.py の末尾が解析時点で未完（ソースが途中で切れているように見える箇所が存在）。モジュールは概念設計および多くの関数を含むが、実行前に残りの実装（記事取得関数や API 呼び出しループの完結）が必要です。
- apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントがあり、フォールバック価格（前日終値など）を使う改良が予定されています。
- position_sizing:
  - lot_size を将来的に銘柄別にする拡張が TODO として記載されている。
- process_priority / set_cpu_affinity:
  - 実行環境によっては権限不足で設定に失敗する場合があり（例: nice の変更や CPU affinity の設定）、その場合は警告を出してスキップする設計。
- run_monitoring:
  - 監視は環境にかかわらず本番 sqlite_path を使用する仕様のため、開発・検証環境でのデータ分離が必要な場合はコードまたは環境変数で明示的に対応する必要があります。
- .env パーサ:
  - 複雑なネストや特殊なシェル展開（$(...) や `...` 等）には対応していない。基本的な export 形式、引用符、バックスラッシュエスケープ、インラインコメント（スペース直前の #）に対応。

---

参考・その他:
- 実行スクリプトはプロセス優先度を起動直後に "high" に設定する設計になっています。運用環境では権限や OS による影響を確認してください。
- DuckDB を研究・AI・集計処理に広く使用しているため、DuckDB のファイルパス（Settings.duckdb_path）やバージョンに依存する箇所がある点に注意してください。

もし実際のコミットログやリリースノート（タグ付け）が存在する場合、その情報を提供いただければ本 CHANGELOG をコミット履歴に合わせて精密化します。