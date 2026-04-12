# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、日本語で記載します。  
バージョン番号はパッケージ定義（src/kabusys/__init__.py の __version__）に基づいています。

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-04-12
初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ全体
  - 初期リリースとして kabusys コードベースを追加。
  - モジュール構成: data, strategy, execution, monitoring, portfolio, research, ai, tools, utils, など。
  - パッケージバージョン: 0.1.0。

- 実行 / 監視エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててセッションを実行。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用し、本番 DB と分離（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - プロセス開始時にプロセス優先度を "high" に設定する処理を追加。
    - DuckDB をデータ処理用に接続。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きに対応（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視用テーブルの初期化（init_monitoring_db）を起動時に実行。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定 / 環境変数管理
  - config.py
    - .env 自動ロード機構を提供（プロジェクトルートを .git / pyproject.toml から発見して .env, .env.local を読み込み）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサーで以下をサポート/改善:
      - export KEY=... 形式の対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - クォートなしのインラインコメント処理（'#' の前が空白/タブのみコメントとして扱う）
    - Settings クラスを導入し、主要な環境変数をプロパティで一元管理（検証付き）。主要なプロパティ例:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABUSYS_ENV （development / paper_trading / live の検証）
      - PAPER_FILL_MODE の検証（instant / partial / never / reject）
      - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等のデフォルト値と Path 変換
      - 各種閾値（CPU/MEM/DISK）やフラグ（KILL_FLAG_CLEAR_ON_START）を環境変数から取得

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順 (同点は signal_rank でタイブレーク)。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を勘案してセクター集中を抑制するフィルタ。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）。

  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の複数配分方式を実装。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate 上限の計算、cost_buffer を用いた保守的推定、合計コスト超過時のスケールダウンと端数処理（残差配分ロジック）を実装。

- 研究（Research）
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照し、日付ウィンドウやウィンドウ長の不足に対する取り扱いを注釈で明記。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得できる設計。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）は None を返す。
    - rank, factor_summary: ランク変換（同順位は平均ランク）と基本統計量サマリを提供。
  - research/__init__.py
    - 主要関数群をエクスポート。zscore_normalize は data.stats から再利用。

- AI / ニュース NLP
  - ai/news_nlp.py
    - OpenAI（gpt-4o-mini）を使ったニュース記事センチメントスコアリングモジュールを追加。
    - 動作設計:
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window。
      - raw_news / news_symbols を集約し、1 銘柄あたり最大記事数・文字数でトリムしてバッチ送信（最大 20 銘柄/チャンク）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでリトライ（上限）。
      - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護する差分 DELETE/INSERT 戦略を採用。
    - score_news: API キー解決（引数または OPENAI_API_KEY 環境変数）とスコア書き込みを実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs などから稼働率・成功率・送信率・P95 レイテンシを算出し、Pass/Fail 判定（閾値はソース内定義）を行う。
    - 日付フィルタ (--from / --to)、DB パス (--db) オプション対応。
    - P95 計算、各種フォーマットユーティリティを実装。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定（Windows: 高/通常/低 の定数、POSIX: nice 値）。
    - CPU affinity を最初 N コアにピン留めする set_cpu_affinity。
    - アクセス権限や未サポートプラットフォームでの安全なフォールバック（ワーニング）処理を実装。

### Changed
- （初回リリースのため該当なし）  
  - 将来的なリリースで変更点をここに記載します。

### Fixed
- .env パーサーの堅牢化
  - クォート中のエスケープ処理や inline コメントの扱いを明確化し、.env ファイル読み込みの誤解釈を防止。
- DB 初期化の冪等化
  - init_monitoring_db を起動時に呼び出し、監視テーブルが存在しない場合に作成することで初期化の安全性を確保。

### Removed
- （初回リリースのため該当なし）

### Security
- 注意事項
  - J-Quants / kabu API 等の機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は必須環境変数として扱い、.env の取り扱いに注意するよう注記。
  - OpenAI API キーは環境変数（OPENAI_API_KEY）か明示的引数で提供する設計（コード中で直接キーを埋め込まないことを前提）。

---

## マイグレーション / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。未設定時は起動時にエラーになります。
- 重要な環境変数とデフォルト:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - SQLITE_PATH: data/monitoring.db（監視用、本番データ）
  - DUCKDB_PATH: data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用、paper_trading 時はこの DB を使用）
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: "instant"）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを無効化可能
- 実行例:
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

今後のリリースではテストカバレッジ、エラーハンドリング強化、ログの構造化、並列処理・性能改善等を予定しています。