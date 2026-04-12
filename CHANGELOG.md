# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
詳細な設計や振る舞いは各モジュールの docstring / コメントを参照してください。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-12
初回リリース。日本株自動売買システム "KabuSys" のベース実装を追加。

### Added
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。
- 設定 / 環境変数管理（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を探索して自動的に .env / .env.local を読み込む機能を実装。
  - .env ファイルのパースは quote / escape / inline comment / export KEY=val 形式に対応。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
  - Settings クラスを追加し、J-Quants / kabuステーション / LINE / DB パス /監視設定 /システム設定等を環境変数から取得する API を提供（検証ロジック含む）。
  - 設定で有効値チェックやデフォルト値を持たせ、paper_trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）をサポート。
- 実行系エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper DB を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を起動するワークフローを実装。
    - RiskManager の初期設定値（max_position_pct 等）を定義。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
- 監視 DB 初期化ユーティリティ
  - monitoring_db.init_monitoring_db を使って監視用テーブルが存在することを保証する処理を導入（冪等）。
- ユーティリティ
  - process_priority（kabusys.utils.process_priority）:
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。
    - CPU affinity を最初の N コアにピンする set_cpu_affinity を追加（例外時は警告でスキップ）。
    - 権限エラーや未対応 OS に対するフォールバック / 警告を実装。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - BUY シグナルから候補選定（score 降順、tie-break: signal_rank）を実装。
    - 等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。全スコアが 0 の場合は等配分へフォールバック。
  - risk_adjustment:
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクターエクスポージャー計算に基づき候補を除外。
    - 市場レジームに応じた投下資金乗数(calc_regime_multiplier) を実装（bull/neutral/bear をマップ）。
  - position_sizing:
    - allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算を実装。
    - 単元株丸め、1銘柄上限、aggregate cap（available_cash を超えた場合のスケーリング）、cost_buffer を考慮した保守的評価、端数処理（lot 単位での再配分）を実装。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - momentum / volatility / value ファクター計算関数を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算）。
    - モメンタム (1M/3M/6M, MA200 差分)、ATR、平均売買代金等を計算。
  - feature_exploration:
    - 将来リターン計算(calc_forward_returns)、IC（スピアマンランク相関）計算(calc_ic)、ファクター統計サマリー(factor_summary)、rank ユーティリティを実装。外部ライブラリに依存しない純 Python 実装。
  - research パッケージは zscore_normalize を data.stats からエクスポート。
- AI / ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から銘柄ごとに記事を集約し OpenAI（gpt-4o-mini）にバッチで問い合わせてセンチメントスコアを ai_scores テーブルへ反映するスコアリング機能を実装。
  - ニュースタイムウィンドウの計算（JST 基準 → UTC 変換）を実装。
  - API バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数トリム）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に既存データを保護する DB 更新戦略を実装。
  - OpenAI API キーを引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを提供（コマンドライン引数 --from / --to / --db）。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率・送信率、P95 レイテンシ等を算出し、PASS/FAIL 判定を出力する。
    - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）を定義。
    - P95 計算、NULL 考慮、DB 存在チェック、OperationalError のフォールバック処理を実装。

### Changed
- なし（初回リリースのため既存コードからの変更はありませんが、実装上の注意点を以下に列挙します）
  - run_monitoring は意図的に本番 sqlite_path を使用（KABUSYS_ENV に依存せず監視は本番 DB を参照）。

### Fixed
- なし（初回リリース）

### Removed
- なし

### Security
- OpenAI API キー等の機密情報は Settings 経由で環境変数として扱う設計。自動 .env ロード機能は OS 環境変数を保護（.env の上書き時に protected set を使用）。

### 注意事項 / 既知の制限
- apply_sector_cap: price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格の導入を想定している（TODO コメントあり）。
- position_sizing の lot_size は現状全銘柄共通の想定（将来は銘柄別に拡張予定）。
- news_nlp モジュールは OpenAI API に依存。API 呼び出し失敗時は部分的にスキップして継続するフェイルセーフを実装しているが、外部 API の SLA に依存する点に注意。
- run_monitoring の MONITOR_POLL_INTERVAL に 0 や負値を設定するとデフォルトにフォールバックする（time.sleep の ValueError 回避のため）。
- calc_forward_returns の horizons は 1〜252 の整数である必要がある（検証あり）。
- research モジュールは DuckDB 上のテーブル構成（prices_daily / raw_financials 等）を前提とする。

### 環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper trading の fill_mode（instant | partial | never | reject）
- OPENAI_API_KEY: OpenAI API キー（news_nlp）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU/MEM/DISK 閾値等多数（Settings を参照）

---

今後の予定（例）
- 銘柄毎単元株数対応（lot_size の銘柄別化）
- 監視・実行プロセスのサービス化（systemd など）と改良された PID / フラグ管理
- news_nlp のロバスト化（モデル選択・分散リトライ）およびスキーマ検証強化

README や各モジュールの docstring に実行方法・設計方針の記載があります。ご利用前にそちらも参照してください。