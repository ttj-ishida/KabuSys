Keep a Changelogフォーマットに準拠した CHANGELOG.md を以下に作成しました。コードベースの実装内容から推測して記載しています。必要があれば日付や項目の追加・修正を指示してください。

---------------------------------------------------------------------
CHANGELOG.md
---------------------------------------------------------------------

# Changelog

すべての notable な変更はここに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

- リリースバージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-04-13

### Added
- 初期リリース: KabuSys 自動売買フレームワークの基礎機能を追加。
  - パッケージバージョン: 0.1.0
- 設定管理（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み順序: OS 環境 > .env.local（上書き） > .env（未設定のみ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサーは export 形式、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントをサポート。
  - 必須環境変数検査（_require）と複数の設定プロパティ（DB パス、PID/kill フラグパス、閾値、環境種別判定等）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 実行エントリスクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を起動直後に High に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント抽象化。
    - OrderRepository、OrderManager、RiskManager、Reconciler の組み立てと ExecutionEngine の session 実行。
    - RiskConfig の初期設定（max_position_pct, max_utilization, rate_limit 等）。initial_portfolio_value は broker.get_available_cash() から取得。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視は環境に関係なく本番 sqlite_path を使用（監視データは単一の監視 DB に集約）。
    - 起動時にプロセス優先度を High に設定、DuckDB と SQLite の接続を初期化しポーリングループを実行。
- 監視 DB 初期化ユーティリティ（init_monitoring_db 呼び出しを実行スクリプトで利用）。
- ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。
  - Windows / POSIX(Linux, Darwin, FreeBSD) を吸収する実装。権限不足や未対応 OS では警告ログでスキップする安全設計。
- Portfolio 構築（src/kabusys/portfolio/*）
  - 銘柄選定: select_candidates（スコア降順、tie-break に signal_rank）。
  - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化、スコア合計 0 の場合は等金額にフォールバック）。
  - セクター集中対策: apply_sector_cap（既存ポジションからセクター別エクスポージャ計算、売却予定銘柄を除外するオプション）。
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear マッピング、未知レジームは警告して 1.0 フォールバック）。
  - ポジションサイズ計算: calc_position_sizes
    - risk_based / equal / score の複数の allocation_method をサポート。
    - 単元（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮。
    - aggregate cap 時のスケーリングと lot 単位での端数処理（残余キャッシュで余剰配分）。
- 研究モジュール（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（行ウィンドウ、データ不足ハンドリング）。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（target_date 以前の最新報告を取得）。
    - すべて DuckDB の prices_daily / raw_financials テーブルを利用する SQL 実装。
  - 特徴量解析（feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得（LEAD を利用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（ランク付けは同順位で平均ランク）。
    - rank / factor_summary: ランキングと基本統計量（count/mean/std/min/max/median）。
    - 外部依存（pandas 等）を使わず標準ライブラリ + DuckDB で実装。
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む機能を追加。
  - スコアリング設計:
    - ニュースウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（UTC に変換）を対象。
    - バッチサイズ、記事数上限、文字数上限によるトークン肥大化対策（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - エラー（429, ネットワーク, タイムアウト, 5xx）に対する指数バックオフリトライ。
    - レスポンスのバリデーション、スコアを ±1.0 にクリップ。
    - 書き込み前に対象コードのみを DELETE → INSERT することで部分失敗時の既存スコア保護。
    - OpenAI API キー未設定時は ValueError を発生させる安全チェック。
    - ルックアヘッドバイアスを防ぐため datetime.today()/date.today() を参照しない設計。
- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用検証レポート生成スクリプトを追加。
  - CLI: python -m kabusys.tools.paper_verification_report（--from/--to/--db をサポート）。
  - 稼働率・注文成功率・送信率・リスク却下数・API レイテンシ（avg/max/P95）等を算出し PASS/FAIL 判定を出力。
  - P95 算出のユーティリティ実装。DB テーブル存在チェックと OperationalError に対するフォールバック処理あり。

### Changed
- 監視・実行起動の共通動作
  - 起動直後にプロセス優先度を High に設定するように統一。
  - 監視実行は本番の sqlite_path を常に参照するポリシーを明示（環境に依らず監視は本番 DB を参照する）。
- .env の読み込み動作
  - .env.local は .env より優先して上書き（protected OS 環境変数は上書きしない）。

### Fixed
- 環境変数の解釈強化
  - .env パーサーがクォート内のバックスラッシュエスケープ、およびインラインコメントの処理を正しく扱うように改善。
- ポジションサイズの aggregated scaling の端数配分で再現性を確保（ソートの安定化と二次キーの使用）。

### Security
- OpenAI API キー取り扱いは明示的に引数または環境変数 OPENAI_API_KEY を要求。未設定時は失敗して明示的にエラーを返すことで鍵漏洩リスクの低減。

### Notes / Implementation details
- DuckDB を分析用途（prices_daily, raw_financials, ai_scores など）で多用。SQLite は監視・paper_trading の軽量永続化に使用。
- 実行時の許可や OS による差異（プロセス優先度設定や CPU affinity）については権限不足・未対応環境で安全にスキップする実装。
- 多くの関数は副作用を持たない純粋関数として実装されており、テストや研究用途での利用を想定。

---------------------------------------------------------------------

過去のリリースや変更履歴を追加したい場合、あるいは特定ファイル・機能に関するより詳細なリリースノート（例: API 仕様、設定項目一覧、CLI 使用例）を作成する場合は指示してください。