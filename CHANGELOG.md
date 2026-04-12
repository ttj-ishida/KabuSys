# CHANGELOG

すべての重要な変更をこのファイルに記録します。形式は「Keep a Changelog」に準拠しています。

なお本リリースではパッケージバージョンが __version__ = "0.1.0" として初版相当の機能群を追加しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-12
### Added
- 基本アプリケーション設定管理 (kabusys.config)
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env 自動ロード機能を実装。
  - .env パーサーを実装: export プレフィックス、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - 必須環境変数未設定時に ValueError を送出するヘルパー _require を提供。
  - 各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値など）。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値のチェック）。

- 実行用・監視用起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度を高（"high"）に設定。
    - 環境に応じた SQLite パスの選択: KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - duckdb 接続の利用。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を実行。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非数）はデフォルトへフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する実装。
    - プロセス優先度を高に設定し、SQLite / DuckDB 接続を開いてポーリングループで monitor.check_once() を定期実行。KeyboardInterrupt により正常終了。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を呼び出すことで監視用テーブルの存在を保証する仕組みを利用（冪等操作）。

- Paper Trading 検証レポートツール (kabusys.tools.paper_verification_report)
  - paper_trading 用の SQLite（デフォルト: data/paper_trading.db）から集計を行い、稼働率、注文成功率、送信率、P95 レイテンシ等の指標を出力するコマンドラインツール。
  - --from / --to / --db オプションをサポート。データ不足に対する安全な取り扱いと例外処理を実装。
  - P95 計算、閾値による PASS/FAIL 判定を行う。閾値はソース内定数で管理（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder
    - シグナル選定、等金額配分、スコア加重配分（スコア総和が 0 の場合は等分配へフォールバック）を提供。
  - risk_adjustment
    - セクター集中制限 apply_sector_cap（売却予定銘柄の除外、"unknown" セクターは制限適用除外）を実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）を実装。
  - position_sizing
    - position_sizing.calc_position_sizes により等分/スコア加重/リスクベース配分の株数計算を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer による保守的コスト見積りを実装。
    - スケーリング時の残差処理（lot 単位での再配分）により残余キャッシュを有効活用。

- プロセス制御ユーティリティ (kabusys.utils.process_priority)
  - cross-platform にプロセス優先度設定 set_process_priority を提供（Windows の PRIORITY_CLASS / POSIX の nice を抽象化）。
  - CPU affinity を最初 N コアへ固定する set_cpu_affinity を提供。
  - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - モメンタム、ボラティリティ（ATR 等）、バリュー（PER・ROE）ファクターを DuckDB 上で計算する関数を追加。
    - 各関数は prices_daily / raw_financials テーブルを参照し、データ不足時の None 処理やカウントチェックを行う。
    - パフォーマンスを考慮したスキャン範囲（カレンダーバッファ）を使った実装。
  - feature_exploration
    - 将来リターン calc_forward_returns（horizons バリデーション、1..252 の制約）、IC（Spearman ランク相関） calc_ic、rank、統計サマリー factor_summary を追加。
    - pandas 等に依存せず標準ライブラリのみで実装。

- ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news を OpenAI (gpt-4o-mini) に送って銘柄別センチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む処理を実装。
  - バッチ処理（1 API 呼び出しで最大 20 銘柄）、チャンク処理、JSON Mode を想定した厳密なレスポンス検証、スコアを ±1.0 にクリップ。
  - 再試行ロジック（429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフ、最大リトライ回数）を実装。
  - タイムウィンドウ計算 calc_news_window（JST 基準、UTC に変換）を提供。
  - API キー未指定時は ValueError を送出。

- パッケージ初期化
  - __init__.py にてパッケージ名と __version__ を定義（"0.1.0"）。
  - research / portfolio / utils などのトップレベルエクスポートを用意。

### Changed
- 初期リリースのため該当なし（新規追加中心）。

### Fixed
- 初期リリースのため該当なし。

### Notes / Migration
- 環境変数のデフォルトパス:
  - DuckDB: DUCKDB_PATH = data/kabusys.duckdb
  - SQLite (監視): SQLITE_PATH = data/monitoring.db
  - Paper Trading SQLite: PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかを指定する必要があります。不正値は ValueError を発生させます。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使います。paper_trading 環境でも監視は本番 DB を参照する点に注意してください。
- run_execution は paper_trading 環境では paper_trading 用 DB を使用して本番 DB と完全分離します。
- .env 自動ロードにより OS 環境変数が既に設定されている場合は既定で上書きされません（.env.local は override=True で上書き可能だが OS 環境変数は保護されます）。

### Breaking Changes
- 初版リリースにつき互換性に関する既存 API からの破壊的変更はありません。

---

今後のリリースでは以下を予定しています（案）
- テストカバレッジの追加（ユニット/統合）
- エラーハンドリング・ログ改善の強化
- position_sizing の銘柄別 lot_size 対応
- news_nlp のレスポンスバリデーションの強化とメトリクス追加

以上。