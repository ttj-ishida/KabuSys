# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

全ての非公開変更や細かな内部実装はここに含まれない場合があります。コードから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期リリース相当の機能群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 実行・監視ランナー
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、SQLite/ DuckDB 接続、ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行と停止フラグ監視を実装（src/kabusys/run_execution.py）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知、監視 DB 初期化（src/kabusys/run_monitoring.py）。

- 設定管理
  - Settings クラスを提供し、環境変数や .env/.env.local ファイルから設定を読み込む自動ロード機能を実装。プロジェクトルート検出（.git または pyproject.toml）に基づく .env 読み込み、OS 環境変数保護の仕組み、キー必須チェック関数 _require を実装（src/kabusys/config.py）。
  - 各種設定プロパティを提供（DB パス、Paper Trading 用設定、監視しきい値、ログレベル、環境判定等）。

- ポートフォリオ構築
  - 銘柄選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を追加（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）を追加（src/kabusys/portfolio/risk_adjustment.py）。
  - ポジションサイズ計算（calc_position_sizes）を追加。単元株丸め、リスクベース/等配分/スコア加重方式、aggregate cap によるスケールダウンを実装（src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージのエクスポートを整備（src/kabusys/portfolio/__init__.py）。

- リサーチ / ファクター計算
  - Momentum / Volatility / Value などのファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。DuckDB を用いて prices_daily / raw_financials テーブルを参照し、各種ウィンドウ集計・欠損扱いを実装（src/kabusys/research/factor_research.py）。
  - 将来リターン計算（calc_forward_returns）、IC（calc_ic）・ランク変換（rank）、ファクター統計サマリ（factor_summary）を追加（src/kabusys/research/feature_exploration.py）。
  - research パッケージのエクスポートを整備（src/kabusys/research/__init__.py）。

- AI / ニュース NLP
  - raw_news を集約して OpenAI（gpt-4o-mini）に送信し、銘柄別のセンチメントスコアを ai_scores に書き込むニュース NLP モジュールを追加。バッチ処理、API キー解決、スコアクリッピング、リトライ（エクスポネンシャルバックオフ）、レスポンスバリデーションの設計を含む（src/kabusys/ai/news_nlp.py）。
  - ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を実装。

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出して標準出力にレポートを出す（src/kabusys/tools/paper_verification_report.py）。

- ユーティリティ
  - process_priority: プラットフォームを意識せずプロセス優先度（Windows の HIGH_PRIORITY_CLASS / POSIX nice）や CPU affinity を設定するユーティリティを追加（set_process_priority, set_cpu_affinity）（src/kabusys/utils/process_priority.py）。

### Changed
- DB と環境分離
  - Paper Trading 環境 (KABUSYS_ENV=paper_trading) 時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離する設計を採用（run_execution / config）。

- ロギング・フェイルセーフ
  - 監視 / 実行起動時にプロセス優先度を最初に設定するようにし、起動ログに KABUSYS_ENV を出力。
  - run_monitoring のポーリングループで check_once() が例外を投げてもループ継続し、例外内容を logger.exception で記録するように変更。

- .env 読み込みルール
  - .env パーサで export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い、クォートなしのコメント認識（直前がスペース/タブの場合のみ）等を丁寧に扱うよう改良（src/kabusys/config.py）。
  - デフォルトの読み込み優先順位を OS 環境 > .env.local > .env として、.env.local を override=True で上書きできるようにした。

- エラーハンドリング・入力検証
  - MONITOR_POLL_INTERVAL の不正値（非数値 / 0 以下）に対してデフォルトにフォールバックし警告を出す処理を run_monitoring に追加。
  - Settings の各種列挙値（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）に対するバリデーションを追加し、不正値で ValueError を送出するようにした。
  - research.calc_forward_returns で horizons の入力値検証（正の整数かつ最大 252 日）を追加。

### Fixed
- 数学 / 統計の堅牢化
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし、警告を出すように修正（src/kabusys/portfolio/portfolio_builder.py）。
  - factor_research / feature_exploration: 欠損データやウィンドウ不足時に None を返す扱いを徹底し、SQL 側でも行数チェックや CASE 式で安全化（src/kabusys/research/*）。
  - feature_exploration.rank: 同順位（ties）は平均ランクで扱い、丸め誤差による ties 検出漏れを防ぐため round(v, 12) を使用。

- 運用安全性
  - run_execution/run_monitoring: 停止フラグファイル（data/stop_requested.flag）を検知して安全に停止する処理を追加。run_execution は起動前に既にフラグが立っている場合は起動を中止。
  - run_execution: スレッド join を短いタイムアウトでループする実装にし、停止フラグを検知したら engine.stop() を呼ぶことでグレースフルに停止可能（src/kabusys/run_execution.py）。
  - init_monitoring_db を呼んで監視テーブルの存在を保証（冪等）するようにした（run_monitoring / run_execution）。

- レポート / 指標
  - paper_verification_report: P95 の計算、日付フィルタ構築、テーブル存在時のフォールトトレランス（OperationalError ハンドリング）を追加。指標のフォーマット関数（_fmt_float/_fmt_int）で None を 'N/A' 表示に統一（src/kabusys/tools/paper_verification_report.py）。

- process_priority の互換性
  - 未対応 OS や権限不足（psutil.AccessDenied など）の場合に警告を出して処理をスキップする安全策を追加（src/kabusys/utils/process_priority.py）。
  - set_cpu_affinity が指定コア数を超える場合の挙動や引数検証を追加。

### Security
- OpenAI API キーの取り扱いについて、api_key 引数または環境変数 OPENAI_API_KEY のいずれかを必須とするバリデーションを追加。未設定時は ValueError を送出し誤使用を防止（src/kabusys/ai/news_nlp.py）。

### Notes / Limitations
- news_nlp の実装は API 呼び出しや結果処理の骨組みを設計しているが、実行時の細部（例: チャンク分割の実装や DB 書き込みロジックの続き）が完成途中の場合があるため、本番運用前にエンドツーエンドでのテストが必要。
- Portfolio / Position sizing の単元株（lot_size）や価格欠損時の振る舞いに関する TODO コメントあり（将来的に銘柄別 lot_size 対応や前日終値によるフォールバック等を検討）。
- DuckDB の executemany に関する制約を意識した実装方針がある（空 params の送信回避等）。

---

今後のリリースでは、ニュース NLP のバッチ送信実装完了、ExecutionEngine 内のリスク管理ロジックの詳細、テストケース整備、CI/デプロイ手順の明記を予定しています。