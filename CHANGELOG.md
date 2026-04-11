CHANGELOG
=========

すべての主要な変更はこのファイルに記録します。  
（以下はリポジトリ内のソースコードから挙動を推測して作成したリリースノートです。）

[0.1.0] - 2026-04-11
--------------------

Added
- 初期リリース相当の機能群を追加。
  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。環境（KABUSYS_ENV）が paper_trading の場合は専用の paper_trading DB を使用する仕組みを導入。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 両スクリプトとも起動直後にプロセス優先度を "high" に設定する処理を組み込み（utils/process_priority.set_process_priority）。
  - 設定管理
    - kabusys.config.Settings: 環境変数/.env の読み込みと各種設定プロパティを提供。自動 .env ロード（.env, .env.local）・保護キー処理・.env 構文（export、クォート、コメント）のパース機能を持つ。
    - 設定プロパティにバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
    - PID ファイル、kill フラグ、閾値（CPU/MEM/DISK）など監視用設定を提供。
  - ポートフォリオ構築（純粋関数）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 各銘柄の発注株数計算（risk_based / equal / score）、lot_size（単元）丸め、aggregate cap によるスケーリング、手数料/スリッページの保守的見積り（cost_buffer）対応。
  - リサーチ／特徴量
    - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を直接 SQL で参照）。
    - research.feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）、統計サマリ、ランク変換ユーティリティ。
    - これらは DuckDB の prices_daily / raw_financials テーブルのみを参照し外部 API を呼ばない設計。
  - AI 関連
    - ai.news_nlp: raw_news から銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し、ai_scores テーブルへ書き込む機能を追加。バッチ処理（最大 20 銘柄/回）、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリッピング（±1.0）、部分失敗耐性のための部分的な DELETE→INSERT トランザクション処理を実装。
    - ai.regime_detector: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を判定・市場レジームテーブルへ冪等書き込みする機能を追加（OpenAI 呼び出しは独立実装、失敗時はフェイルセーフで継続）。
    - OpenAI 呼び出し箇所はテスト容易性を考慮し差し替え可能（news_nlp._call_openai_api をモック可能）。
  - DB 初期化
    - monitoring.monitoring_db.init_monitoring_db を（run_execution/run_monitoring から）呼んで監視用テーブルの存在を保証する処理を追加。
  - ユーティリティ
    - utils.process_priority: Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度と CPU affinity を設定するユーティリティを追加。権限不足や未対応 OS に対するワーニングを出力して安全にスキップする。

Changed
- データベース取り扱いの分離
  - run_execution では paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離して動作する。
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用する仕様（監視は常に本番 DB を参照）。
- 時間・データ参照の設計方針
  - AI/リサーチ系モジュールは datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。target_date を明示的に受け取る API を採用。
- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env と .env.local を自動ロード。OS 環境変数はデフォルトで保護され上書きされない。自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。

Fixed
- レジリエンス強化
  - AI 呼び出し（news_nlp）のレスポンス不正や JSON パース失敗時に例外を投げずログ記録して該当チャンクのみスキップすることで処理継続可能に。
  - score_news の DuckDB への書き込みは部分失敗に備え、影響範囲を最小化する（対象コードのみ DELETE → INSERT を行う）。
  - process_priority / set_cpu_affinity は権限不足や未実装 API に対して安全にスキップし、ワーニングを出力。

Security
- OpenAI API キーの取り扱い
  - ai.news_nlp.score_news と ai.regime_detector 系は api_key 引数または環境変数 OPENAI_API_KEY を参照。未設定時は呼び出し元に ValueError を送出し明示的に失敗させる（無意識の公開や無断送信を防止）。
- .env 読み込み時の保護
  - OS 環境変数は protected として扱い、.env の上書きから保護（override の挙動が明確化）。

Notes / Implementation details
- デフォルト・環境変数（主なもの）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。1 未満や不正値は警告ログを出してデフォルトにフォールバック。
  - KABUSYS_ENV: 有効値は development / paper_trading / live（小文字）。無効値は ValueError。
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ有効。
  - PAPER_FILL_MODE: instant/partial/never/reject のみ有効。
  - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH / PID_FILE_PATH / KILL_FLAG_PATH など多数のデフォルトパスを設定。
- ポジションサイジング等の設計方針はドキュメント（PortfolioConstruction.md, StrategyModel.md）に準拠する旨の注釈がソース内にあり、将来的拡張（銘柄別 lot_size 等）を想定した設計になっている。
- DuckDB を用いた SQL 実装（Window 関数等）によりファクター計算を DB 側で効率的に実行する設計。
- news_nlp と regime_detector は gpt-4o-mini を想定したプロンプト設計・JSON モードの利用を行っているが、不整合に備えた復元処理（外側の {} を抽出してパース）も実装。

Unreleased
- なし（本ファイルはリポジトリの現状コードから推測して作成した CHANGELOG の初期版です）。

備考
- 本 CHANGELOG はソースコードからの挙動推測に基づいて作成しています。実際のリリースノートや変更履歴はリポジトリのコミット履歴・リリース運用に合わせて調整してください。