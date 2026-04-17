# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [Unreleased]


## [0.1.0] - 2026-04-17

### Added
- 初回リリース (0.1.0) — KabuSys のコア機能群を追加。
- 実行・監視プロセス起動スクリプトを追加:
  - run_execution.py
    - ExecutionEngine の起動ロジック。KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler といった依存コンポーネントの組み立てを実装。
    - エンジンは別スレッドで起動し、data/stop_requested.flag を監視して安全に停止可能。
    - 実行 PID を data/execution.pid に保存する挙動をサポート（設定により変更可能）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時に data/stop_requested.flag を監視してループを終了。
- 設定管理・読み込み機能を追加:
  - config.py
    - .env 自動読み込み（プロジェクトルート検出基準: .git または pyproject.toml）。
    - 複数の環境変数プロパティを提供（J-Quants / kabu / DB パス / monitoring 関連閾値 など）。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。デフォルト値や説明付きの入力プロンプトを提供。
    - .env 出力テンプレートは .env を絶対にコミットしない旨の注意を含む。
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI。必須環境変数チェック、パスの親ディレクトリ有無、YAML パース検証（PyYAML が存在する場合）、本番用の追加ガード等を実装。--strict モードで警告を FAIL 扱いにできる。
- ユーティリティを追加:
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定。Windows と POSIX 系（Linux/Mac/FreeBSD）を扱う。CPU affinity 固定機能も実装（set_cpu_affinity）。
    - 実行スクリプトは起動時に優先度を "high" に設定するよう呼び出し。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）:
  - portfolio/portfolio_builder.py
    - select_candidates（スコア降順、同点は signal_rank を tie-break）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化、全スコアが 0 の場合は等分配にフォールバックし警告）
  - portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中上限チェック。unknown セクターは上限適用対象外。sell_codes により当日売却予定を除外可能）
    - calc_regime_multiplier（レジームに応じた投下資金乗数。未知のレジームは警告とともに 1.0 をフォールバック）
  - portfolio/position_sizing.py
    - calc_position_sizes（risk_based / equal / score の各 allocation_method をサポート）
    - ロット単位（lot_size）で丸め、per-stock 上限・aggregate cap（利用可能現金に対するスケーリング）、コストバッファを考慮したスケーリングと端数配分ロジックを実装
- リサーチ（ファクター計算）モジュールを追加:
  - research/factor_research.py
    - momentum（1M/3M/6M リターン、MA200 乖離）、volatility（ATR20、平均売買代金、出来高比）等の計算を DuckDB（prices_daily テーブル）で実装。
    - データ不足時は None を返す設計。
- 運用ツールを追加:
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポート生成 CLI。期間フィルタ、DB パス指定 (--db) に対応。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し、閾値比較で PASS/FAIL を判定。閾値はスクリプト内で定義（稼働率 99% など）。
- パッケージ初期化:
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。
- ドキュメント的な注記やログメッセージを多数追加して運用時の可観測性を向上。

### Changed / Improved
- .env パーサを強化:
  - export プレフィックス対応、シングル/ダブルクォートされた値のエスケープ処理、インラインコメントの扱い（クォートあり/なしでの違い）を実装。既存の OS 環境変数は protected として上書き回避の挙動を導入。
  - 読み込み順序: OS 環境 > .env.local > .env（.env.local は上書き許可）。
- 起動・停止の安全性強化:
  - data/stop_requested.flag による外部停止（監視・実行ともに対応）。
  - 起動時に PID ファイル保存や監視テーブルの初期化（init_monitoring_db）を行い idempotent に保証。
- ExecutionEngine の RiskManager デフォルト設定を明示:
  - max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker のパラメータや initial_portfolio_value を broker.get_available_cash() で初期化する挙動を採用。
- process_priority の失敗（権限不足など）を警告でスキップするよう堅牢化。
- position_sizing のスケーリングロジックは端数処理を安定化（再現性のため二次キーにコードを使用してソート）。

### Fixed
- 監視ループとエンジン起動での DB 初期化タイミングや接続クローズ処理を確実に行うよう調整（finally ブロックでの close）。
- Paper_verification_report の日付フィルタ/集計で DB が存在しない場合やテーブル欠損時に発生する例外を捕捉してメッセージを出すよう改善。

### Security
- .env を生成する config_setup.py のヘッダに「.env は絶対に Git にコミットしないこと」を明記。
- validate_config.py は本番環境（KABUSYS_ENV=live）の場合に LINE トークン未設定や KILL_FLAG_CLEAR_ON_START 設定に関する警告を出すことで安全運用を促進。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。未設定の場合は Settings プロパティアクセスで ValueError が発生するため、.env を用意してください。
- 自動 .env ロード:
  - デフォルトでプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local が自動読み込みされます。自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視プロセス:
  - run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path（settings.sqlite_path）を参照します。paper_trading 用 DB を監視したい場合は別途対応が必要です。
- 権限:
  - set_process_priority は OS により権限が必要になる場合があります（特に nice の負の値や Windows の高優先度）。権限不足時は警告を出してスキップします。
- CLI:
  - 設定チェック: python -m kabusys.validate_config [--strict]
  - .env ウィザード: python -m kabusys.config_setup
  - 監視開始: python -m kabusys.run_monitoring
  - 実行エンジン起動: python -m kabusys.run_execution
  - ペーパートレード検証: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

### Removed
- （なし）

### Deprecated
- （なし）

---

参考: 主要な環境変数・設定項目
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）

何か特定の変更点を強調したい、もしくは英語版の CHANGELOG も必要であれば教えてください。