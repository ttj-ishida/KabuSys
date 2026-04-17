# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

## [0.1.0] - 2026-04-17

### Added
- 初期リリース: KabuSys のコア機能群を追加しました。
  - 実行系 / 監視系
    - run_execution: ExecutionEngine を起動するエントリポイント。BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager 組立て、デーモンスレッドでのセッション実行・停止処理を実装。
      - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（デフォルト: data/paper_trading.db）と MockBrokerClient を使用し、本番 DB と分離。
      - 停止用フラグファイル (data/stop_requested.flag) を検知して安全に停止。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
    - 監視用 DB の初期化関数 init_monitoring_db を利用。
  - 設定 / 環境管理
    - config.Settings: .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で判定）。環境変数のパース（export 形式、クォート対応、コメント処理）を実装。
    - 各種設定プロパティを提供（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH など）とバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.select_candidates: BUY シグナルのスコア降順選抜。
    - portfolio.calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバックして警告ログを出力。
    - portfolio.apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮して候補除外）。
    - portfolio.calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear を実装、未知レジームはフォールバック）。
    - portfolio.calc_position_sizes: 発注株数計算（allocation_method: risk_based / equal / score）、lot_size（単元）丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate スケーリングと残差処理。
  - リサーチ / ファクター計算
    - research.calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を参照するファクター計算機能（MA200、ATR20、PER/ROE 等）。
    - research.calc_forward_returns / calc_ic / factor_summary / rank: 将来リターン算出、IC（Spearman）計算、統計サマリー等。外部ライブラリに依存せず実装。
    - research パッケージは zscore_normalize を再エクスポート。
  - ニュース NLP（AI スコアリング）
    - ai.news_nlp モジュール（部分実装）：ニュース収集ウィンドウ計算 (calc_news_window)、OpenAI API（gpt-4o-mini）を用いたバッチスコアリングの設計（バッチサイズ、トリム、リトライ、JSON モード検証、スコアの ±1.0 クリップ、部分置換による DB 更新の方針）を追加。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプト。稼働率・注文成功率・送信率・P95 レイテンシの算出、および閾値による Pass/Fail 判定（閾値はスクリプト内定義）。
  - ユーティリティ
    - utils.process_priority: set_process_priority（Windows / POSIX を吸収）、set_cpu_affinity（最初の N コアに固定）を実装。権限不足や未対応 OS の場合は警告してスキップ。

### Changed
- .env の読み込み方針
  - 自動ロード時の優先順位を OS 環境変数 > .env.local > .env とし、OS 環境変数は保護（上書き回避）するように実装。
  - export KEY=val、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを細かく改善。
- Settings の振る舞い
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の値チェックを厳格化。無効値では ValueError を投げるようにした。
  - paper_trading 用 DB パス・fill_mode 等のプロパティを導入し、paper_trading 環境の明確な分離をサポート。
- 実行時のプロセス制御
  - run_execution / run_monitoring の最初にプロセス優先度を "high" に設定する処理を追加（set_process_priority を利用）。失敗時はログで警告し続行。
- 報告系の堅牢化
  - paper_verification_report は DB ファイルが存在しない場合のメッセージ出力、テーブル欠如時の例外捕捉（sqlite3.OperationalError のハンドリング）を追加して、部分的に欠損した DB に対しても継続的にレポートを出力するようにした。
- ファクター / レポートの算出挙動
  - ファクター計算はデータ不足時に None を返すようにし、集計クエリでは NULL を考慮して結果を整形するよう改善。

### Fixed
- 環境変数パーサーの不具合修正
  - クォートされた値内のバックスラッシュエスケープを正しく処理するように改善。
  - export プレフィックスやコメントの扱いで無効行を誤ってパースするケースを修正。
- calc_score_weights のフォールバック
  - 全スコアが 0 の場合にゼロ除算や不正な重みを返す問題を修正し、等金額配分へフォールバックして警告を出すようにした。
- position_sizing のスケーリングと丸め
  - aggregate cap を超過した場合のスケールダウンロジックと lot_size 単位の残差配分処理を実装し、端数処理で不整合が生じる問題を解消。
- run_monitoring のポーリング設定
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非数）のときにデフォルトへフォールバックして time.sleep に渡すと ValueError になる問題を回避。
- ai.news_nlp の堅牢性
  - 設計上、OpenAI API 呼び出し時の 429 / タイムアウト / 5xx をリトライする方針を明確化。API キー未設定時に早期にエラーを返すようにした。

### Security
- OpenAI API キーの必須化
  - ai.news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY が未設定の場合 ValueError を送出。キーが外部に漏れないよう環境管理を推奨。

### Notes / Known issues / TODO
- portfolio.apply_sector_cap:
  - price_map に欠損（0.0）がある場合にエクスポージャーを過小評価してしまう可能性があるため、将来的に前日終値や取得原価でのフォールバックを検討（TODO コメントあり）。
- position_sizing:
  - 将来的な拡張で銘柄ごとの lot_size をサポートするための設計変更（stocks マスタからの lot_map）を想定している（TODO コメントあり）。
- ai.news_nlp:
  - ファイルは部分的に提示されているため、実運用には追加のエラーチェック・DB 書き込みロジックの完成が必要。
- run_execution / run_monitoring:
  - 実行中の PID ファイル管理・ログレベル設定など、運用環境向けの追加設定は今後拡張予定。

---

このリリースはコードベースの現状から推測してまとめた初期 CHANGELOG です。実際のリリース管理ポリシーに合わせてカテゴリや日付を調整してください。