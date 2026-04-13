# CHANGELOG

すべての注記は Keep a Changelog 構成に準拠しています。  
リリース日は本リポジトリに含まれるコードから推測して付与しています。

## [Unreleased]

- 開発中 / 予定の改善点や未実装の拡張（ドキュメント中の TODO や将来の設計メモ参照）。

## [0.1.0] - 2026-04-13

初回公開リリース。以下の主要機能・モジュールを追加しました。

### Added
- 基本パッケージ定義
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書きに対応（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する（monitoring 用テーブルを本番 DB に作成する仕様）。
    - 起動時にプロセス優先度を "high" に設定する処理を呼び出す。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。MockBrokerClient を使用することを想定。
    - ExecutionEngine 起動前に OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立てる処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）を実装し、.env/.env.local 自動読込機能を追加。既存 OS 環境変数は保護される（.env.local は override）。
    - 自動ロードを無効にする環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - .env の堅牢なパーサーを実装（export 対応、クォート内バックスラッシュエスケープ、インラインコメント処理など）。
    - Settings クラスを提供し、以下の主要設定をプロパティとして取得可能にした:
      - API トークン系: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - LINE 関連: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
      - データベース: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）、PAPER_TRADING_SQLITE_PATH（paper 用 DB）
      - Paper trading 設定: PAPER_FILL_MODE（instant/partial/never/reject、検証あり）
      - 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値
      - システム: KABUSYS_ENV（development | paper_trading | live）、LOG_LEVEL
    - 環境変数が未設定の場合に明確なエラーを出す `_require()` を実装。

- ポートフォリオ構築ライブラリ（pure functions、DB 非依存）
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、タイブレークで signal_rank）、等配分・スコア加重配分の算出関数。
    - スコア全てが 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をサポート。未知レジームはフォールバック）。
    - セクター上限計算時の既存保有・売却予定除外ロジックを実装。
  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based / equal / score）に対応した株数計算を実装。
    - 単元株（lot_size）丸め、ポジション上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer による保守的なコスト見積もりをサポート。
  - portfolio パッケージの __all__ を整備。

- 監視 / ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（権限不足時は警告を出してスキップ）。

- 研究（Research）モジュール（DuckDB を用いた純粋な計算ロジック）
  - research/factor_research.py
    - Momentum / Volatility / Value の各ファクター算出関数を実装（prices_daily / raw_financials を参照）。
    - 各関数は日付を引数に取り、(date, code) をキーとする辞書リストを返す。
    - DuckDB 上でのウィンドウ関数を使った実装、データ不足時に None を返す設計。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン対応）、ランク相関 IC 計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP（OpenAI 連携）
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大銘柄数 20 / チャンク）、1 銘柄あたり記事数と文字数の上限、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク / 5xx 等に対する指数バックオフリトライを実装。
    - API キーの引数優先解決（api_key 引数 > OPENAI_API_KEY 環境変数）。未設定時は ValueError を投げる。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成コマンドを追加（コマンドライン引数 --from / --to / --db）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ、リスク却下数等を集計して PASS/FAIL を判定。
    - P95 の計算、日付フィルタ、DB 存在チェック、テーブルが無い場合のフォールバックを実装。

- DB 初期化ユーティリティ（monitoring_db）
  - monitoring_db.init_monitoring_db を起動時に呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- なし（初回リリースにつき過去バージョンからの変更は該当なし）。

### Fixed
- なし（初回リリース）。

### Removed
- なし。

### Security
- 環境変数の自動読み込みは OS 環境変数を保護する設計になっており、意図しない上書きを避けるように実装。

### Notes / Implementation details / 制約
- DuckDB をデータ解析用のローカル列指向 DB として使用。多くの研究・NLP 関数は DuckDB 接続を受け取り SQL と Python の組合せで計算する（pandas 等に依存しない設計）。
- 多くの関数は DB 参照を行わず純粋関数（副作用なし）として実装されているため、単体テストが容易。
- Paper Trading は本番 DB と完全分離される設計（paper 用 sqlite_path を使用）。
- 設計メモ / TODO:
  - apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格（前日終値等）の利用は未実装。現在は exposure が過少見積りされる可能性がある旨コメントあり。
  - position_sizing: 将来的に銘柄ごとの lot_size を導入する予定（現状は単一 lot_size）。
  - calc_value: PBR / 配当利回りは未実装。
- ログ・例外ハンドリング:
  - 監視ループ内で check_once() が例外を投げてもループは継続し、例外は logger.exception で報告される（フェイルセーフ）。
  - process_priority / cpu_affinity の設定は権限不足や未対応 OS の場合に警告を出してスキップするため、無停止での起動を重視。

### Environment variables (主要)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — Paper trading 専用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper の約定動作 (instant|partial|never|reject)、デフォルト "instant"
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）、デフォルト 60
- OPENAI_API_KEY — OpenAI API キー（ai/news_nlp で使用）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD — 各 API 用必須トークン/パスワード

---

今後のリリースでは以下のような改善を想定しています（優先度順、参考）:
- apply_sector_cap の価格フォールバック実装（前日終値、取得原価等）
- position_sizing の銘柄ごとの lot_size 対応
- calc_value に PBR / 配当利回り追加
- ai/news_nlp の部分失敗時の原子性向上（部分コミット保護の更なる強化）
- 追加のユニットテスト・CI ワークフロー整備

もし特定の変更（コミット差分ベースでの CHANGELOG 生成など）を希望される場合は、その差分（git log / パッチ）または対象ブランチを提供してください。