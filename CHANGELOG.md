# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

※このファイルは、リポジトリ内のコードから推測して作成した想定の変更履歴です。

## [Unreleased]

（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-04-12

初回リリース。システム監視・実行・ポートフォリオ構築・リサーチ・ツール群・ユーティリティを含む基本機能を実装。

### Added
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。環境変数 KABUSYS_ENV に応じて paper_trading モード用の専用 SQLite DB を使用する機能を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。

- 設定/環境変数管理
  - config.py: .env 自動読み込み（.env → .env.local の優先順位）と、プロジェクトルート自動検出（.git / pyproject.toml 基準）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスで各種環境設定をラップ（DB パス、PID / kill フラグ、閾値、PAPER_FILL_MODE 等の妥当性検証を含む）。

- 監視/実行周りの DB 初期化
  - monitoring_db の初期化処理を呼び出して監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコアが全て 0 の場合は等金額配分にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に対応した株数計算、単元株丸め、aggregate cap によるスケーリング、cost_buffer の考慮等を実装。
  - portfolio.risk_adjustment
    - apply_sector_cap: 同一セクターの既存保有が最大比率を超える場合に新規候補を除外する機能。
    - calc_regime_multiplier: 市場レジームに応じたレバレッジ乗数（bull/neutral/bear）を実装。

- リサーチ・ファクター計算
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials テーブルを用いた各種ファクター計算を実装（移動平均・ATR・リターン等）。
  - research.feature_exploration
    - calc_forward_returns: 将来リターンの計算（複数ホライズン対応）。
    - calc_ic / rank / factor_summary: スピアマンランク相関(IC)・ランク変換・統計サマリー等のユーティリティを実装。
  - research.__init__ で zscore_normalize（data.stats から）を公開。

- AI ニュース NLP スコアリング
  - ai.news_nlp
    - raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメント（-1.0〜1.0）を生成・ai_scores に書き込むバッチ処理を実装。
    - バッチサイズ、文字数上限、記事数上限、スコアのクリップ、最大リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）などの耐障害仕様を実装。
    - calc_news_window: JST ベースのニュース収集ウィンドウ算出ユーティリティを実装。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL 判定を出力。
  - CLI 引数（--from/--to/--db）をサポート。

- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX（Linux, macOS, FreeBSD）に対応したプロセス優先度設定（psutil 利用）。未対応 OS は警告でスキップ。
    - set_cpu_affinity: カレントプロセスの CPU affinity を設定する関数を追加。引数検証・アクセス権限失敗時の警告対応あり。

- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- DB 分離の設計
  - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 monitoring DB と完全に分離する設計を採用。

- 監視ループの堅牢化
  - MONITOR_POLL_INTERVAL の無効値（非整数・0 以下）に対して警告を出してデフォルト（60秒）へフォールバックする仕様を追加。
  - SystemMonitor.check_once() 内での例外を捕捉し、ログ出力後に次のポーリングを継続するようにした（フェイルセーフ）。

- .env ファイルパーサの強化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、行内コメントの限定的扱いなど、.env の多様な書式へ頑健に対応。
  - OS 環境変数は protected として .env.local の上書きから保護する挙動を実装。

- レポート/集計ロジック
  - paper_verification_report の集計に P95 計算・NULL 安全処理を追加。テーブルが存在しない場合のフェールセーフ（OperationalError ハンドリング）を含む。

### Fixed
- 安全な初期化/クローズ処理
  - run_execution/run_monitoring で DuckDB/SQLite 接続を作成後、最後に必ず close() してリソースを解放するように実装。

- スコア重み計算のフォールバック
  - calc_score_weights: 全スコアが 0 の場合にゼロで割る問題を回避し、等金額配分にフォールバックして警告を出すよう修正。

- セクター上限チェックの挙動
  - apply_sector_cap: sector_map に存在しないコードは "unknown" 扱いとし、unknown セクターは上限制約の対象外にすることで誤除外を防止。

- レジーム乗数の既定値
  - calc_regime_multiplier: 未知のレジーム値に対して警告を出し、1.0（Bull 相当）でフォールバックするようにした。

### Notes / Implementation details
- DuckDB は分析系処理（ファクター計算・ニュース NLP の集約・AI スコア書き込みなど）に使用する想定。
- OpenAI 統合は API キーの明示的提供（関数引数）または環境変数 OPENAI_API_KEY を想定。未設定時は ValueError を投げる。
- 実行および監視プロセス起動時にプロセス優先度を最初に上げる（set_process_priority("high")）設計により、低レイテンシ運用を意識。
- 一部関数は設計書（PortfolioConstruction.md, StrategyModel.md, 等）に基づく実装である旨の注釈が付いており、将来的な拡張点（銘柄別 lot_size、価格フォールバックなど）が明記されている。

---

履歴の不備や補足情報の要望があれば、対象ファイルの変更点に基づいて追記・修正します。どの形式（セマンティックバージョニング、日付の変更など）で管理したいか指示いただければ、それに合わせて整形します。