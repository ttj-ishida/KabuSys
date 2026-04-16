# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: 主要な変更点をカテゴリ別（Added / Changed / Fixed / Security）で列挙しています。

## [Unreleased]
（無し）

## [0.1.0] - 2026-04-16
初回リリース。自動売買システム KabuSys のコア機能群を追加しました。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を併用するアーキテクチャを採用。分析・リサーチ用途に DuckDB、稼働監視や取引ログに SQLite を使用。

- 起動スクリプト / 実行基盤
  - run_monitoring.py を追加
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視テーブルは init_monitoring_db を呼んで冪等に初期化。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する仕様。

  - run_execution.py を追加
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）へ完全分離して記録。
    - 起動前に停止フラグをチェックし、既に立っていれば起動しない安全措置。
    - 実行中は別スレッドで engine.run_session を実行し、停止フラグ検知で engine.stop() を呼ぶ制御。
    - 実行 PID ファイルを data/execution.pid に保存する仕組み（設定から上書き可）。

- 設定・環境
  - config.Settings を追加
    - プロジェクトルート（.git または pyproject.toml）を自動検出して .env / .env.local を読み込む自動ロード機能。
    - .env パーサは export 前置、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応した堅牢な実装。
    - OS 環境変数を保護するための protected キーセットを導入（.env.local は上書き可能だが OS 環境は保持）。
    - 各種プロパティ（J-Quants / kabu / LINE / DB / 監視閾値 / システム設定）を提供し、妥当性チェックを行う（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証）。
    - settings = Settings() をエクスポート。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順＋同点タイブレーク実装。
    - calc_equal_weights / calc_score_weights: 等分配・スコア比率配分（全スコアが 0 の場合は等分配にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。単元株（lot_size）丸め、per-position と aggregate cap、cost_buffer を用いた保守的見積り、利用可能現金に応じたスケールダウンを実装。

- リサーチ / 特徴量
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value を追加。DuckDB の SQL とウィンドウ関数でファクターを算出（MA200、ATR20、volume 等）。
  - research.feature_exploration
    - calc_forward_returns / calc_ic / factor_summary / rank を追加。外部ライブラリに依存せず純 Python 実装でランク相関（Spearman）や統計サマリを計算。
  - research.__init__ により主要 API をエクスポート（zscore_normalize は data.stats から取り込み）。

- AI（ニュース NLP）
  - ai.news_nlp を追加
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）に対してバッチでセンチメント解析を行う機能。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を厳密に計算してルックアヘッドバイアスを排除。
    - 1 銘柄あたりの最大記事数 / 文字数制限、バッチサイズ上限（20）、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライを実装。失敗時は部分的にスキップして継続するフェイルセーフ設計。
    - レスポンス検証と、ai_scores テーブルへの置換型書き込み（部分失敗時に既存他銘柄のスコアを保護する設計）。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI（--from/--to/--db）。稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）などを算出し、PASS/FAIL 判定を表示。
    - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - P95 計算、欠損データのハンドリング、SQLite のテーブル欠落時のフォールバックを実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。Windows と POSIX（Linux / macOS / FreeBSD）を跨いだ抽象化を提供し、権限不足や未対応 OS の場合は警告を出してスキップする堅牢な実装。
  - utils パッケージ追加（プレースホルダ __init__）。

### Changed
- 設計決定
  - 監視（run_monitoring.py）は KABUSYS_ENV に依存せず「本番 sqlite_path」を参照する仕様に明確化（運用上の監視一元化のため）。
  - paper trading 実行は本番データと完全に分離された SQLite（data/paper_trading.db）に記録されるよう明確化（run_execution.py）。

### Fixed
- 環境変数パーサの強化（config._parse_env_line）
  - export 形式やクォート内のバックスラッシュエスケープ、インラインコメント処理の不整合を解消。
- MONITOR_POLL_INTERVAL の不正値取り扱いを改善
  - 0 や負の値、整数以外が渡された場合は警告を出してデフォルト（60 秒）にフォールバックし、time.sleep での例外回避を行う。

### Security
- ai.news_nlp: OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出して誤った公開アクセスを防止。

### Notes / Limitations / TODO
- position_sizing.calc_position_sizes
  - 価格が欠損（0.0）だとエクスポージャーの過小見積りになる可能性がある旨の注記あり。将来的に前日終値や取得原価でのフォールバックを検討。
- ai.news_nlp の処理途中でコードの末尾が切れている箇所（score_news 内の続き実装を要する箇所）が存在するため、実運用前に完全実装・単体テストが必要。
- DuckDB に対する executemany の挙動（params が空の場合エラーになる点）を考慮した呼び出し側の実装に注意。
- 監視・実行エンジン周りは本リリースで基本的な安全・停止フローを実装済みだが、運用に合わせたログ/監視・稼働試験（SIT/ステージング）が推奨されます。

---

（注）本 CHANGELOG は提示されたコードベースから推測して作成したものであり、実際のドキュメントや設計仕様に基づくものではありません。コードの未完了箇所や未実装の機能は将来のリリースで補完される可能性があります。