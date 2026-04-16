CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

[0.1.0] - 2026-04-16
-------------------

### Added
- 初期公開: KabuSys のコア機能群を追加。
  - パッケージ構成: kabusys パッケージ本体（__version__ = 0.1.0）を導入。
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機構を追加（プロジェクトルートを .git または pyproject.toml から探索）。
  - export プレフィックス・クォート・インラインコメント対応を含む堅牢な .env パーサを実装。
  - OS 環境変数を保護する protected オプションを導入（.env.local などでの上書きを制御）。
  - Settings クラスを実装し、各種環境設定（DB パス、API トークン、監視しきい値、動作環境判定など）をプロパティとして提供。値の検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE など）を行う。
- 実行エントリポイント (src/kabusys/run_execution.py)
  - ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler 構成、スレッド実行と停止フラグ検知を実装。
  - paper_trading 環境向けに専用 SQLite DB（data/paper_trading.db）を用いることで本番 DB と分離。
  - デフォルトの RiskManager 設定を提供（max_position_pct, max_utilization, rate_limit_per_sec 等）。
- 監視エントリポイント (src/kabusys/run_monitoring.py)
  - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化処理を行い、停止フラグで安全に終了。
  - 監視は環境に依らず本番 sqlite_path を使用する設計。
- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading の検証レポート生成ユーティリティを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数を集計し PASS/FAIL を判定。コマンドライン引数（--from/--to/--db）をサポート。
  - P95 計算、日付フィルタ組み立て、DB 存在チェック等を実装。
- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - 銘柄選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数: apply_sector_cap（既存保有からセクター別エクスポージャ算出、上限超過セクターの候補除外）、calc_regime_multiplier（bull/neutral/bear の乗数）。
  - 株数決定・リスク制限: calc_position_sizes（risk_based / equal / score の割当方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積）。
- 研究モジュール (src/kabusys/research/*)
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB 経由で prices_daily / raw_financials を参照）。
  - 特徴量探索: calc_forward_returns（任意ホライズン）、calc_ic（スピアマンランク相関）、factor_summary、rank を実装。外部依存を避け標準ライブラリのみで計算。
- ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に格納する仕組みを追加。
  - ニュース収集ウィンドウ（JST 前日15:00〜当日08:30）を計算する calc_news_window、バッチ処理、レスポンスバリデーション、スコアクリップ（±1.0）、リトライ（指数バックオフ）等を実装。
  - OpenAI API キーの明示的指定または環境変数 OPENAI_API_KEY を必須とする。
- ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority と set_cpu_affinity を実装。Windows / POSIX の差分を吸収し、安全に失敗をログに落とす（権限不足等を無視して継続可能）。
- DuckDB / SQLite の初期化補助（monitoring_db 初期化の呼び出し箇所を追加）。

### Changed
- 設計上の分離:
  - paper_trading 環境ではデータ永続化を本番と完全分離（専用 SQLite）する方針を明確化。
- .env 読み込みの優先順位を明文化（OS 環境 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- calc_score_weights がスコア合計 0 の場合に等金額配分へフォールバック（警告ログを出力）。
- calc_position_sizes のスケーリングロジックを保守的に実装（lot 単位で丸め、残余キャッシュで追加配分を行う）。

### Fixed
- 環境変数 MONITOR_POLL_INTERVAL が不正（非整数や <= 0）の場合、デフォルト（60 秒）にフォールバックして警告を出す実装を追加。
- 各種関数でデータ欠損時の安全処理を追加（NULL/欠損価格のスキップ、窓幅不足時に None を返すなど）。
- process_priority の権限エラーや未対応 OS での例外をキャッチして警告ログに変換し、処理を継続するように改善。
- research / feature_exploration の rank/IC 計算で ties・丸め誤差を考慮する実装を追加し安定性を向上。

### Security
- ai/news_nlp の score_news は OpenAI API キーの未設定時に ValueError を送出するようにして、キー漏洩や不意な無条件 API 呼び出しを防止。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（重要環境変数の上書きを防止）。

### Notes / Migration
- 実運用で ExecutionEngine / SystemMonitor を起動する際は環境変数（KABUSYS_ENV, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, OPENAI_API_KEY 等）を適切に設定してください。
- paper_trading 環境は data/paper_trading.db（デフォルト）を使用するため、本番データと完全に分離できます。
- .env の形式は従来の簡単な KEY=val に加え、export プレフィックス・クォート・エスケープ・インラインコメント等に対応しています。複雑な値を .env に置く際はクォートを利用してください。

未完事項 / 今後の改善案
- position_sizing の price 欠損時に前日終値や取得原価でフォールバックする仕組みの追加検討（TODO コメントあり）。
- news_nlp の処理継続時に部分失敗があった場合の運用上の可観測性向上（部分リトライや結果ログの強化）。
- 実行時のログレベル/ログ出力先（ファイル/回転）の設定強化。

-------------------

(この CHANGELOG はソースコードの内容から推測した変更点をまとめたものです。必要に応じて日付・詳細を調整してください。)