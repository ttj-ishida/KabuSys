# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従い、セマンティックバージョニングを使用します。  

注: 以下は与えられたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。実際のコミット履歴ではありません。

## [Unreleased]

- ドキュメント化・コード注釈の追加（内部コメント・TODO の明示）
- research/factor_research.py の一部実装が途中（ファイル末尾で切れている箇所）であるため、計算ロジックの続き・テスト追加を予定
- 将来的な拡張:
  - 銘柄ごとの lot_size をサポートするためのマスタ導入
  - position_sizing の価格フォールバック（前日終値・取得原価など）
  - DuckDB/SQLite のマイグレーション・スキーマ管理ツール

---

## [0.1.0] - 2026-04-21

初回公開リリース。自動売買システム KabuSys のコアユーティリティ群、実行/監視スクリプト、ポートフォリオ構築ロジック、設定ツール、解析ツールを含む。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行・監視用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを提供。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db がデフォルト）を使用し、本番 DB と分離。
    - ブローカークライアントは BrokerClientFactory 経由で生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - RiskManager に既定の安全パラメータ (max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など) を設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境に依存せず production の sqlite_path を使用する設計。
    - 停止フラグの検知によりループを安全に終了。

- 設定管理と補助ツール
  - config.py
    - .env 自動読込（プロジェクトルート検出: .git / pyproject.toml ベース）。
    - .env/.env.local を OS 環境変数を保護した上で読み込む仕組み（自動読込は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env ファイルのパースは export 形式、単一/二重クォート、エスケープ、インラインコメント等に対応。
    - Settings クラス: 各種設定値（J-Quants / kabu API / DuckDB/SQLite パス / PID・kill flag パス /閾値設定 / KABUSYS_ENV, LOG_LEVEL 等）の取得・バリデーションを提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - config_setup.py
    - インタラクティブな .env ウィザードを提供。既存 .env の読み込み・更新、シークレット項目のマスク表示、保存時の確認をサポート。
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや YAML ファイルの存在・パースチェック、KABUSYS_ENV=live 時の追加警告を実装。
    - --strict オプションで警告をエラー扱いにして非ゼロ終了。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック。既存保有・売却予定を考慮して新規候補を除外。unknown セクターは適用除外。
    - calc_regime_multiplier: 市場レジームに基づく投下金額乗数（bull/neutral/bear）を提供。未知レジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数算出。単元株（lot_size）で丸め、max_position_pct・max_utilization・cost_buffer を考慮。
    - aggregate cap により available_cash を超える場合にはスケールダウンし、端数は lot_size 単位で残差分を再配分するロジックを実装。
    - リスクベース方式（risk_based）では stop_loss_pct と risk_pct に基づく算出を行う。
    - ログ出力と価格欠損時のスキップ処理を実装。

- 研究・解析ユーティリティ
  - research/factor_research.py（部分実装）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計。
    - モメンタム計算の定数（1M/3M/6M 等）、ATR や MA200 等のパラメータを定義。
    - 実装は途中（ファイル末尾が切れている）。将来的な完成を想定。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH）から期間指定で検証レポートを生成する CLI。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計して PASS/FAIL で判定。
    - デフォルト閾値を定義（例: uptime >= 99%、fill_rate >= 90%、P95 latency <= 200 ms）。
    - DB が存在しない場合の明示的メッセージを表示。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティ。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに登録。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
    - stdout を使用する点を明記（cron/Task Scheduler との相性考慮）。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（high/normal/low）と CPU affinity 設定機能を提供。
    - Windows と POSIX 系（Linux, Darwin, FreeBSD）に対応。権限不足等の例外は警告を出してスキップ。

### Changed
- （初回リリースのため履歴上の「変更」は無し。実装上の設計選定とデフォルト値を明文化）
  - 監視ループは監視 DB に対して常に本番 sqlite_path を使用する設計（run_monitoring）。
  - Execution は paper_trading 環境で専用 DB を使うことで本番 DB と分離（run_execution）。

### Fixed
- ロギングとファイル IO の堅牢化
  - logging_setup: ログディレクトリ作成に失敗した場合はファイルログを無効化して stdout のみで継続するようにし、例外でプロセスが落ちないように設計。
  - process_priority / set_cpu_affinity: psutil の例外（AccessDenied, AttributeError, NotImplementedError）をキャッチして警告に留め、安全にスキップ。
  - validate_config: PyYAML 未インストール時に YAML 検証をスキップして警告を出す仕様。

### Security
- .env の取り扱いに関する注意を明文化（config_setup.py で生成される .env を絶対に Git にコミットしない旨のヘッダを追加）。

### Notes / Known issues
- research/factor_research.py が途中で切れているため、ファクター計算の完全な実装と単体テストは未着手。
- position_sizing の価格フォールバックが未実装（TODO コメントあり）。価格が 0.0 の場合にエクスポージャーが過小見積りされる可能性があるため、将来的に前日終値等で補完することを検討。
- 一部 CLI は対話入力を伴うため、非対話環境での挙動（EOF/KeyboardInterrupt）に対する取り扱いを考慮済みだが、ヘッドレス運用向けのオプション追加は今後の課題。

---

履歴は今後のリリースごとに追記してください。