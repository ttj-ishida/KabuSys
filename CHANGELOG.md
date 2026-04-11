CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録しています。
このファイルはコードベース（src/ 以下）の内容から推測して作成しています。

v0.1.0 - 2026-04-11
-------------------

Added
- 初期リリース。以下の主要機能群を実装。
  - コア実行スクリプト
    - run_execution.py: ExecutionEngine セッション起動スクリプト（プロセス優先度設定、DB 接続、ブローカークライアント生成、Engine 起動）。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL でポーリング間隔上書き可能）。
  - 設定管理
    - kabusys.config.Settings: .env/.env.local の自動ロード（プロジェクトルート検出）および多くの環境変数のラッパー。必須値チェック、値の検証（KABUSYS_ENV, LOG_LEVEL 等）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - ポートフォリオ構築
    - portfolio.portfolio_builder: 候補選定(select_candidates)、等金額/スコア加重の重み計算(calc_equal_weights, calc_score_weights)。
    - portfolio.position_sizing: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap のスケールダウンアルゴリズム。
    - portfolio.risk_adjustment: セクター集中の上限適用(apply_sector_cap)、市場レジームに応じた乗数(calc_regime_multiplier)。
  - リサーチ（ファクター計算・特徴量解析）
    - research.factor_research: Momentum / Volatility / Value ファクターを DuckDB の prices_daily/raw_financials を参照して計算（ma200, ATR, PER/ROE 等）。
    - research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC（Spearman）計算(calc_ic)、統計サマリ(factor_summary)、ランク関数(rank)。
    - research パブリック API: zscore_normalize を含めたエクスポート（kabusys.research）。
  - AI（LLM）連携
    - ai.news_nlp: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメントを ai_scores テーブルへ書込む機能。バッチ処理、トークン肥大対策、リトライ（429/ネットワーク/5xx）、レスポンスバリデーション、スコアクリップを実装。
    - ai.regime_detector: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・永続化する機能。API キー未設定時のフェイルセーフ（macro_sentiment=0.0）。
  - ユーティリティ
    - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定と CPU affinity 設定を提供。権限不足や未対応 OS を考慮したフォールバック・警告を実装。
  - パッケージ情報
    - kabusys.__init__.py: パッケージバージョン __version__ = "0.1.0" を定義。

Changed
- （初回リリースにつき「変更」はありません）

Fixed / Robustness improvements
- 環境変数ファイル読み込みの堅牢化
  - .env の行パースで export プレフィックス、クォート、エスケープ、インラインコメントなどに対応。
  - 読み込み失敗時は warnings.warn による通知で処理継続。
  - OS 環境変数を保護する protected 機能を導入（.env.local の上書き制御）。
- run_monitoring のポーリング間隔取得で不正値を検出した場合にデフォルトへフォールバックし、警告を出すように実装（MONITOR_POLL_INTERVAL）。
- DB 書き込みの安全化
  - ai.news_nlp の ai_scores 書き込みでトランザクション（BEGIN/COMMIT/ROLLBACK）を使用。DuckDB executemany の空リスト制約に配慮して空チェックを行う。
- LLM 結果処理の堅牢化
  - レスポンス JSON のパース失敗時に文字列内の最外の { ... } を抽出して復元する試みを行う。
  - 返却形式検証（results リスト、各要素の code/score）と未知コードの無視、スコアの数値変換・有限性チェック、±1.0 にクリップ。
  - リトライ戦略（指数バックオフ、429/ネットワーク/タイムアウト/5xx の扱い）を実装。
- research / factor 計算でデータ不足のケースを明示的に扱う（windows 未満の観測点では None を返す等）。
- position_sizing のスケールダウンロジックで単元（lot_size）単位の再配分を実装し、残余キャッシュで fractional 残差順に追加配分するアルゴリズムを導入。
- process_priority: 権限不足や未対応 OS の例外をキャッチして警告に置き換え、プロセスが停止しないようにした。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供する必要がある旨を明記。未設定時は ValueError を発生させる実装。
- .env の自動ロードはオプトアウト可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

Configuration / Environment variables（主なもの）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development。無効値は ValueError。
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）。デフォルト: INFO。
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須（_require により未設定で例外）。
- SQLITE_PATH: デフォルト data/monitoring.db。run_monitoring は環境に依らず本番 sqlite_path を使用。
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）。
- DUCKDB_PATH: デフォルト data/kabusys.duckdb。
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視に関する設定。
- CPU / メモリ / ディスクしきい値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（デフォルト値を Settings で提供）。
- PAPER_FILL_MODE: paper トレード時の MockBroker 動作（instant / partial / never / reject）。不正値は例外。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。不正値・0 以下はデフォルト 60 秒にフォールバック。
- OPENAI_API_KEY: ai.news_nlp / ai.regime_detector で使用（必須または引数で提供）。

Notes / Implementation details
- DuckDB をクエリレイヤに使用し、prices_daily / raw_financials / raw_news 等のテーブルから純粋関数的に計算を行う設計。
- LLM 呼び出しは OpenAI の Chat Completions（gpt-4o-mini）を想定。テストしやすさのために内部呼び出し関数を差し替え可能（ユニットテストでの patch を想定）。
- レジーム判定は ETF 1321（日経225 連動）の ma200 乖離を主軸とし、マクロニュースセンチメントを補助するハイブリッド方式。
- 一部コメントに将来の拡張メモ（例: lot_size の銘柄別対応、price フォールバック）を残している。

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Authors
- この CHANGELOG はリポジトリ内ソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。