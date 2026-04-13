# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
安定バージョンはセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-13
初回リリース — 基本機能の実装と運用／研究用ユーティリティ群を追加。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 常に本番用 sqlite_path を監視 DB として使用する仕様（KABUSYS_ENV に依存しない動作を明示）。
    - 起動時にプロセス優先度を "high" に設定。ループ内で例外を拾ってログ出力し継続するフェイルセーフ実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB から分離。
    - BrokerClientFactory により本番/モックブローカーを切り替え、ExecutionEngine を組み立ててセッション実行。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
    - .env のパースを堅牢化（export プレフィックス、クォート（エスケープ含む）、インラインコメント処理の実装）。
    - Settings クラスを導入し、環境変数経由で各種設定値（DBパス、PIDファイル、監視閾値、PAPER_FILL_MODE 等）を取得・検証するプロパティを提供。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。

- モニタリング DB 初期化ユーティリティ
  - monitoring/monitoring_db への init_monitoring_db 呼び出しを run_* スクリプトから実行（監視テーブルの存在を保証）。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア重み（calc_score_weights：全スコアが 0 の場合は等分配にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を実装。既存保有のセクター時価を計算し上限超過セクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）を実装（bull/neutral/bear 等のマップ、未知のレジームはフォールバック）。
    - 価格欠損時の注意点や将来的なフォールバックの TODO を明示。
  - portfolio/position_sizing.py
    - 発注株数計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、1銘柄上限・Aggregate cap（available_cash を超えた場合のスケールダウン）をサポート。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的な見積り、残差配分ロジックを実装。
    - 将来的な拡張（銘柄別 lot_size）を TODO コメントで記載。

- 研究・ファクター計算
  - research/factor_research.py
    - DuckDB を用いたモメンタム / ボラティリティ / バリュー指標の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 各関数は prices_daily / raw_financials 等のテーブルのみを参照する仕様。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ファクター統計サマリ（factor_summary）、ランク化ユーティリティ（rank）を実装。
    - 標準ライブラリのみでの実装とし、入力検証（horizons の上限等）を行う。

- AI ニューススコアリング
  - ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、トークン肥大化対策（記事数・文字数制限）、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップを実装。
    - OPENAI_API_KEY による API キー解決（引数で上書き可）。未設定時は ValueError を送出。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定ユーティリティを実装（Windows / POSIX(nice) を吸収）。
    - CPU affinity 設定ユーティリティ set_cpu_affinity を実装（権限不足時は警告してスキップ）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して PASS/FAIL 判定を出力。
    - P95 計算、期間フィルタ、DB 存在チェック、テーブル欠損時のフォールバックを実装。

### Changed
- DB 接続/初期化の取り扱い
  - run_execution.py と run_monitoring.py で監視用テーブルの初期化を冪等に行うよう保証（init_monitoring_db 呼び出し）。
  - run_execution.py は paper_trading 環境時に paper 用 SQLite を使用し、本番 DB と完全分離する仕様に明確化。

### Fixed / Hardened
- .env パースの堅牢化
  - export プレフィックス対応、クォート文字列のバックスラッシュエスケープ処理、インラインコメントの取り扱い等を改善し .env 解析での誤動作を低減。
- 実行中の例外処理を強化
  - 監視ループ内での monitor.check_once() の例外を catch してループ継続するようにし、予期しない例外で監視プロセスが停止しないようにした（ログ出力あり）。
- リソースクリーンアップ
  - スクリプト終了時に sqlite/duckdb 接続を確実にクローズするよう finally ブロックで保証。

### Notes / Known limitations
- apply_sector_cap は sector_map に存在しないコードを "unknown" と扱い、"unknown" セクターには上限を適用しない設計（意図的）。
- apply_sector_cap のエクスポージャー計算で price が 0.0 の場合に過少見積もられる旨の TODO コメントあり（将来的なフォールバック価格の検討）。
- position_sizing は現状グローバルな lot_size（既定 100）を想定。銘柄別単元対応は将来の拡張予定。
- ai/news_nlp.py における OpenAI へのリクエスト/書き込みは外部 API に依存するため、API 利用上限や料金に注意。
- run_monitoring.py はドキュメントどおり「監視は環境にかかわらず本番 sqlite_path を使用」する。意図的な設計なので運用時は留意。

---

以上がこのコードベースで確認できる主な追加・変更点です。必要であれば各ファイルごとのより詳細な変更点（関数定義の抜粋や注意点）を追加で出力します。どのレベルの詳細を追記しますか？