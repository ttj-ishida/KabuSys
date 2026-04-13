# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
このファイルはコードベース（src/ 以下）から推測して作成した初版の変更履歴です。

注: 日付は本コードスナップショットの作成日（2026-04-13）を使用しています。

## [Unreleased]
- 内部改善:
  - 環境変数の自動読み込み周りを堅牢化（プロジェクトルート自動検出、.env/.env.local 読み込み、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env パーサを強化: export 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応。
  - プロセス優先度／CPU affinity 設定ユーティリティを改善（Windows / POSIX の差分吸収、許可エラー時は警告でスキップ）。
  - DuckDB / SQLite 接続の初期化とクリーンアップを一貫して行う処理を強化。

---

## [0.1.0] - 2026-04-13
初期リリース

### Added
- コア:
  - kabusys パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - 設定管理モジュール (kabusys.config.Settings) を追加。.env 自動読み込み、必須環境変数検査、各種デフォルトパス／閾値を提供。
    - 環境変数例: KABUSYS_ENV, SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT など。
    - KABUSYS_ENV の許容値検証 (development / paper_trading / live) を実装。
    - PAPER_FILL_MODE の入力検証（instant / partial / never / reject）を実装。
- 実行／監視用スクリプト:
  - run_execution.py を追加。ExecutionEngine 起動エントリポイントを提供。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用専用 SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てとセッション実行。
    - プロセス優先度を起動時に "high" に設定。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0/負の値は警告のうえデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を "high" に設定してから起動。
- ツール:
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポートを生成。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシなどを算出して PASS/FAIL 判定を行う。
    - CLI オプションで期間指定 (--from, --to) および DB パス指定 (--db) が可能。
    - デフォルト DB パス: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH により変更可）。
    - 既定の判定基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- ポートフォリオ構築:
  - portfolio モジュールを追加（portfolio_builder, position_sizing, risk_adjustment）。
    - 候補選定 (select_candidates)、等金額 / スコア加重の重み計算 (calc_equal_weights / calc_score_weights)。
    - セクター集中制限の適用 (apply_sector_cap)、レジームに応じた投下資金乗数 (calc_regime_multiplier)。
    - 株数決定ロジック (calc_position_sizes): risk_based / equal / score 方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer 考慮。
    - 各関数は純粋関数（副作用なし）でメモリ内計算に限定。
- リサーチ／ファクター計算:
  - research モジュールを追加（factor_research, feature_exploration）。
    - calc_momentum, calc_volatility, calc_value：prices_daily / raw_financials を用いたファクター計算（モメンタム、ATR、流動性、PER/ROE 等）。
    - calc_forward_returns、calc_ic、factor_summary、rank：将来リターン計算、IC（Spearman）計算、統計サマリー、ランク付けユーティリティ。
    - DuckDB を用いた SQL ベース実装でパフォーマンスと再現性を重視。
- AI ニュース NLP:
  - ai/news_nlp.py を追加。raw_news を OpenAI API（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込む処理を実装。
    - 1 銘柄あたりの記事数／文字数上限、バッチ処理（最大 20 銘柄／API 呼び出し）、429/5xx/ネットワーク断に対する指数バックオフのリトライ、応答バリデーション、スコアの ±1.0 クリップなどを実装。
    - タイムウィンドウは JST で前日 15:00 ～ 当日 08:30（UTC に変換して DB 検索）。
    - API キーは引数または OPENAI_API_KEY 環境変数から取得（未設定時は ValueError）。
- ユーティリティ:
  - utils/process_priority.py を追加: set_process_priority(level), set_cpu_affinity(cpu_count) を実装。アクセス権限がない場合は警告してスキップ。

### Changed
- DB 戦略:
  - run_execution は paper_trading 環境では paper_trading 専用の SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離するように設計。
  - run_monitoring は常に本番 sqlite_path を使用して監視データを記録。
- ロギング／エラーハンドリング:
  - run_monitoring の監視ループで check_once() 実行時に例外発生してもループを継続するように例外捕捉を導入（次のポーリングまで待機して継続）。
  - run_monitoring／run_execution の起動時にプロセス優先度設定と起動環境ログを追加。

### Fixed / Robustness
- .env パーサの安定化:
  - クォートあり／なしの値取り扱いとコメント処理の改善により、複雑な .env 行も安全に読み込めるようになった。
- ポジションサイズ計算:
  - 単元株（lot_size）での丸め処理、最大ポジション上限、aggregate cap によるスケールダウン、残余キャッシュを用いた再配分ロジックを実装し、総投下資金が available_cash を超えないよう調整するようにした。
- スコア重み付け:
  - calc_score_weights は全銘柄のスコア合計が 0 の場合に等金額配分へ自動フォールバックし、警告を出すようにした。
- ファクター／リサーチ:
  - ファクター計算はデータ不足時に None を返す設計にして安定化（窓不足等）。
  - calc_forward_returns は horizons の妥当性チェックを追加。
- ニュース NLP:
  - OpenAI 呼び出しのエラー耐性（リトライ）とレスポンスの厳密なバリデーション、部分成功時に既存スコアを保護するための部分置換ロジックを実装。

### Documentation / Comments
- 多くのモジュールに実装方針・注釈・使用上の注意をコメントとして記載。特に PortfolioConstruction.md / StrategyModel.md 参照を明記してアルゴリズムの根拠を示した。

### Security
- OpenAI API キーやその他機密情報は明示的に必須／環境変数にて取り扱い、.env の自動読み込みにおいて OS 環境変数を保護する設計とした。

---

備考:
- 本 CHANGELOG はコードの静的解析と実装コメントからの推測に基づいて作成したため、実際の変更履歴（コミット履歴）と完全に一致しない可能性があります。必要であればコミットログやリリースノートと照合して調整してください。