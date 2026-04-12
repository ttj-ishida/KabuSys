# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠します。  

※ リリース日やバージョンはコードベースのメタ情報（__version__ 等）と現状の実装から推測して記載しています。

## [0.1.0] - 2026-04-12

### Added
- 基本リリース: KabuSys 初期実装を追加。
  - パッケージメタ情報（src/kabusys/__init__.py）にバージョン `0.1.0` を導入。

- 実行用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、ブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、セッション実行を行う。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db）を使用し MockBrokerClient を利用可能（本番 DB と分離）。
    - RiskManager のデフォルト RiskConfig を実装（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等を含む）。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒、無効値時はデフォルトにフォールバック）。
    - 監視は環境に依らず本番 sqlite_path を使用する点に注意。

- 設定管理
  - config.py: 環境変数/.env ファイルの自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env/.env.local の読み込み順序と override/保護（protected）挙動を実装。
    - 複雑な .env 行のパースを行う `_parse_env_line`（コメント・クォート・export 形式に対応）。
    - Settings クラスを導入し、各種設定（J-Quants, kabu, LINE, DB パス, PID/KILL フラグ, 各種閾値, 環境名検証等）をプロパティ経由で提供。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）や KABUSYS_ENV の検証を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder.py:
    - select_candidates: BUY シグナルからスコア降順で候補抽出。
    - calc_equal_weights / calc_score_weights: 重み計算（スコアが全て 0 の場合は等配分にフォールバック）。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限適用ロジック（既存保有・売却予定の考慮、"unknown" セクター扱い）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear/フォールバック）。
  - position_sizing.py:
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく発注株数計算。lot_size, cost_buffer を考慮した aggregate cap スケーリングアルゴリズムを実装。

- 研究・ファクター計算
  - research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily / raw_financials を参照して定量ファクターを計算。
    - 各関数は不足データに対して None を返す等の堅牢性を保持。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン計算（複数ホライズン対応、入力検証）。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損排除・最小レコード数チェック）。
    - rank / factor_summary: ランキング・統計サマリー実装。
  - research/__init__.py にてエクスポートを整備（zscore_normalize など外部ユーティリティとも統合）。

- AI ニュース NLP
  - ai/news_nlp.py:
    - raw_news -> OpenAI (gpt-4o-mini) を用いたセンチメントスコアリング実装（JSON Mode を期待）。
    - バッチ処理（最大 20 銘柄/回）、記事トリム（最大記事数、最大文字数）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）、部分更新（対象コードのみ DELETE/INSERT）等の設計。
    - calc_news_window ユーティリティ（JST ウィンドウを UTC naive datetime へ変換）を提供。
    - API キー未設定時は明確なエラーを返す。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加。DB から取れる指標（system_status, trade_logs, risk_logs）を集計し、稼働率・注文成功率・送信率・レイテンシ等を判定（閾値: uptime 99% 等）。
    - コマンドライン引数 --from/--to/--db に対応。DB 不在時のメッセージや各種 sqlite の OperationalError に対するフォールトトレランスを実装。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level) を実装（Windows / POSIX (Linux, Darwin, FreeBSD) に対応、失敗時は警告を出力してスキップ）。
    - set_cpu_affinity(cpu_count) を実装（core 固定、利用可能コアを考慮、例外ハンドリング）。
  - 各モジュールにおいて DuckDB / sqlite 接続を受け取る設計で外部 IO を明確化。

### Changed
- 設定読み込みポリシー:
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。プロジェクトルートが見つからない場合は自動ロードをスキップして安全に動作。

- DB 接続の分離:
  - 実行/監視の DB 振る舞いを明確化: run_monitoring は環境にかかわらず本番 sqlite_path を使う一方、run_execution は paper_trading モードで専用 DB を使用する（data/paper_trading.db）。これにより paper_trading と本番データは完全に分離。

### Fixed
- .env パースの堅牢化:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理等に対応し、実運用でよくある .env 形式の差異に耐性を持たせた。

- ポジション算出の端数処理/スケール処理:
  - position_sizing.calc_position_sizes にて lot_size による丸め、aggregate cap を超えた際のスケーリングと残余分の lot 単位追加配分（remainder 処理）を実装し、投下資金超過時の挙動を明確化。

- research / feature_exploration:
  - calc_forward_returns の horizons 入力検証を追加（正の整数かつ <=252 のチェック）。rank 関数は ties を平均ランクで処理し浮動小数点の丸め誤差対策を追加。

- プロセス優先度/CPU affinity の例外処理:
  - アクセス拒否や未実装環境発生時に警告でスキップするよう改善。

### Security
- OpenAI API キーは引数で明示的に渡せる設計とし、環境変数 OPENAI_API_KEY 参照時も未設定時は ValueError を投げることで誤動作を防止。

### Notes / Breaking changes / Migration
- Settings の検証が厳格化されているため、以下の環境変数値が無効な場合は起動時に例外が発生します:
  - KABUSYS_ENV: 有効値は "development", "paper_trading", "live" のみ。
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ。
  - PAPER_FILL_MODE: "instant", "partial", "never", "reject" のみ。
  - MONITOR_POLL_INTERVAL: 0 以下や非数値はデフォルト(60 秒)にフォールバックするが、設定が想定外なら警告が出力される。
- run_monitoring が常に本番 sqlite_path を使用する仕様に注意してください（監視データを paper_trading DB に混ぜたくない場合は現状の設計が安全です）。
- OpenAI を利用する ai/news_nlp の実行には OPENAI_API_KEY が必須。API 呼び出し回数やモデル選定によるコストに注意してください。

### Known limitations / TODO（コード内コメントより）
- position_sizing: lot_size を銘柄別へ拡張する予定（現在は全銘柄共通の単元を仮定）。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少評価される点は将来の拡張（前日終値や取得原価のフォールバック）で対処予定。
- ai/news_nlp.py: スコア書き込み処理など一部ログ・部分失敗時の保護ロジックが重要（実装は存在するが運用での検証が必要）。
- tools/paper_verification_report: DuckDB ではなく SQLite を参照するツールであり、テーブルが存在しない場合に N/A を表示する等のフォールトトレランスを備えるが、DB スキーマの前提に依存する箇所がある。

---

今後のリリースでは、テストカバレッジの強化、ドキュメント（API / 設定 / 運用手順）拡充、銘柄別単元対応、AI モジュールのエラーハンドリング改善やレート制御の強化を予定しています。