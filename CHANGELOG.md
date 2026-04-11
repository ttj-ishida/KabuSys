Changelog
=========
すべての重要な変更はこのファイルに記載します。
このプロジェクトは「Keep a Changelog」規約に準拠します。
リリース日はコミット内容・リリース時に想定した日付を記載しています。

フォーマット
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

Unreleased
----------
（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-04-11
-------------------

Added
- 基本パッケージ構成を追加
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用する設計。
    - BrokerClientFactory を利用して本番 / モックブローカーを切り替え（paper_trading 用の MockBrokerClient を想定）。
    - 各種実行コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み上げてセッション実行。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値はデフォルトにフォールバックして警告ログを出力。
    - 監視用 DB は環境に依らず本番 sqlite_path を使用（監視は常に本番データを参照する想定）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で判定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 環境変数のパースを robust に実装（export 句、シングル/ダブルクォート、エスケープ、コメント処理など）。
  - Settings クラスを提供し、各種設定（DBパス、APIトークン、PID/kill flag パス、閾値、環境判定など）をプロパティで取得可能にした。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH 対応。
  - ログレベル・環境（development/paper_trading/live）のバリデーション。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等金額にフォールバックして警告）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限チェック。既存ポジションのセクター別時価を算出し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マップ、未知レジームはログを出して 1.0 にフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
      - risk_based: 許容リスク率・stop_loss から基本株数を算出し単元株（lot_size=100）で丸める。
      - equal/score: 重み・max_utilization を用いた per-position 上限と aggregate cap を実装。cost_buffer を考慮した保守的見積り、利用可能現金を超える場合のスケールダウン（端数処理は lot 単位で残差に基づき再配分）。
    - 単元丸め・価格欠損時のスキップ・portfolio_value による _max_per_stock 上限を考慮。

- 研究（research）モジュール
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を DuckDB の SQL ウィンドウ関数で計算。データ不足時は None。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を明示的に扱う。
    - calc_value: raw_financials と prices_daily を組み合わせ PER / ROE を計算（target_date 以前の最新財務データを採用）。
  - feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト: [1,5,21]）の将来リターンを LEAD を使って一括取得。horizons のバリデーションを実装。
    - calc_ic / rank: スピアマンランク相関（IC）計算とランク関数（同値は平均ランク）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - DuckDB を前提に SQL+Python で高速に計算する設計。

- AI 関連（kabusys.ai）
  - news_nlp
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを取得して ai_scores に書き込む機能を実装。
    - 処理の主要事項:
      - ニュースウィンドウは JST ベースで定義し、UTC に変換（target_date の前日 15:00 JST 〜 当日 08:30 JST を対象）。
      - 1チャンク最大 20 銘柄（_BATCH_SIZE）、1銘柄あたり最大記事数と最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - OpenAI API 呼び出しは JSON Mode を想定。429・接続断・タイムアウト・5xx は指数バックオフでリトライ（最大回数制御）。
      - レスポンスの厳密なバリデーション（JSON 抽出、"results" 配列、code と score の検証）、未知コードは無視、スコアは ±1.0 にクリップ。
      - 部分失敗時のデータ保護のため、書き込みは対象コードに絞って DELETE → INSERT を実施（DuckDB executemany の注意点に対処）。
      - API キーは引数または環境変数 OPENAI_API_KEY から解決。未指定時は ValueError。
  - regime_detector
    - ETF 1321 の MA200 乖離とマクロニュース LLM センチメントを加重合成して日次レジーム（bull/neutral/bear）を判定する実装。
    - マクロニュースは事前定義キーワードでフィルタしたタイトルを使用し、OpenAI にて macro_sentiment を算出。API 失敗時は macro_sentiment=0.0 のフォールバック。
    - 合成式: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)（重み: MA70% / Macro30%）。
    - 判定ロジックに閾値を設け、結果を market_regime テーブルへ冪等に書き込む。

- utils
  - process_priority
    - set_process_priority(level): Windows と POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。無効な level は ValueError。
    - set_cpu_affinity(cpu_count): 指定コア数に固定する機能（None で未設定）。psutil の権限エラー等を捕捉して警告ログでフォールバック。
    - 権限不足や未対応 OS ではエラーを投げず警告してスキップ。

Changed
- DuckDB 統合
  - 研究・AI・実行系で DuckDB 接続を受け渡す設計に統一（性能と分析用 SQL 利便性向上）。
- DB 初期化
  - run_execution/run_monitoring の起動部分で監視用テーブルの初期化を idempotent に行う init_monitoring_db 呼び出しを追加（テーブルが存在することを保証）。

Fixed
- 環境変数パース周り
  - .env のクォートやエスケープ、インラインコメントの扱いを改善し、より実運用向けに堅牢化。
- ニュースウィンドウ
  - JST→UTC の変換ロジックを明確化し、ルックアヘッドバイアスを防止（関数 calc_news_window を追加）。

Security
- OpenAI API キー取得時に未設定を明示的に検出して ValueError を送出（API キー漏洩防止のため挙動を明確化）。

Notes / Implementation details
- ロギングは各モジュールで logger を利用。致命的でない失敗（API 呼び出し失敗、権限不足等）は基本的に警告ログに留め処理継続するフェイルセーフ設計。
- datetime.today()/date.today() を直接参照しない実装方針（ルックアヘッドバイアス回避）。ただし ExecutionEngine のデフォルト target_date は date.today() を使う箇所あり（エンジン起動時の意図的挙動）。
- DuckDB への executemany は空リストを渡せない制約に配慮して空チェックを行う実装。

今後の予定（草案）
- stocks マスタで銘柄別 lot_size をサポートし、position_sizing の lot_size を拡張する。
- news_nlp / regime_detector のテスト用モック化・CI 統合と OpenAI 呼び出しの抽象化による切替容易化。
- モニタリング・Execution の監視・PID / kill flag 周りの運用スクリプト強化。

--- 
この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴・リリースノートに合わせて適宜修正してください。