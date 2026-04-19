# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般メモ:
- パッケージバージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 としています。
- コマンドライン／スクリプト群、設定管理、ポートフォリオ構築ロジック、ユーティリティ、簡易レポートツールなど、初期の主要機能を含むリリースです。

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初期公開リリース。自動売買システム KabuSys の基礎となる複数モジュールを追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) を監視し、安全に停止する処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイルパスをサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告出力。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用して初期化。
    - 停止フラグでループ終了、例外発生時はログ出力して次回ポーリングへフォールバック。
    - 起動時にプロセス優先度を "high" に設定。

- 設定関連
  - config.py
    - 環境変数読み込みとラッパー Settings クラスを追加。
    - .env ファイルの自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースは引用符、エスケープ、コメント（インライン）に対応。
    - 各種設定プロパティを定義（DB パス、API トークン、paper_trading 用設定、閾値、PID/KILL フラグなど）。環境値の妥当性チェックを行い、無効値では例外を発生させる。

  - config_setup.py
    - .env の対話式作成／更新ウィザードを追加。
    - デフォルト値や選択肢、シークレット項目の取り扱い、保存確認、ファイル書き込みを実装。
    - 生成された .env に関する注意（Git に含めない等）を出力。

  - validate_config.py
    - 起動前チェック用の CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の有無と YAML パースチェック（PyYAML があれば内容検証）。
    - KABUSYS_ENV=live 時の追加警告（LINE 設定未登録、KILL_FLAG_CLEAR_ON_START 設定等）。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコアが全てゼロの場合、等配分にフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中を抑える apply_sector_cap を追加。既存保有からのセクターエクスポージャーを計算し、閾値超過セクターの新規候補を除外。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を追加（"bull"/"neutral"/"bear" をサポート、未知レジームはフォールバックで 1.0 として警告出力）。
    - セクター未定義コードは "unknown" とみなし、上限制約を適用しない設計。

  - portfolio/position_sizing.py
    - 発注株数計算ロジックを追加（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限 (max_position_pct)、投下資金上限 (max_utilization) を考慮。
    - aggregate cap 超過時にはスケールダウン後、端数処理（lot_size 単位で残差の大きい順に追加配分）を行うアルゴリズムを実装。
    - price 欠損時の挙動や将来的な拡張（銘柄別単元情報など）の TODO コメントを追加。

  - portfolio/__init__.py
    - ポートフォリオ関連関数をパッケージエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力を使用）と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーへ設定。
    - 既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック処理、ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。

  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定を追加（Windows と POSIX(Linux/Mac/FreeBSD) を吸収）。
    - psutil を使用し、nice / priority を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
    - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を提供（エラー時は警告を出す）。

- モニタリング／DB 初期化
  - monitoring.monitoring_db の init_monitoring_db（参照のみ）を起動スクリプトから利用し、監視テーブルの存在を保証（冪等）。

- 実行検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime_pct)、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ (平均/最大/P95)、リスク却下数等。
    - 判定基準（しきい値）を定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）し PASS/FAIL を表示。
    - コマンドライン引数 --from / --to / --db をサポート。
    - P95 の計算、各種 SQL クエリ（system_status / trade_logs / risk_logs）から集計。

- 研究用モジュール（下地）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタムや MA200、ATR、出来高等の定義と定数）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを返す設計。
    - calc_momentum 等の関数スケルトンを含む（実装継続の必要あり）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

Notes / 備考:
- run_execution/run_monitoring はプロセス優先度設定、ログ設定を共通で用いるため、システムでの常時稼働を想定した設計です。
- Settings クラスは起動時に環境変数の妥当性チェックを行います。必須変数が未設定の場合は ValueError を送出します。validate_config CLI で事前検証することを推奨します。
- Paper Trading と本番 DB は分離されているため、ペーパートレード時の DB による検証・解析が可能です。
- research/factor_research.py はまだ実装途中の箇所が含まれており、必要に応じて完全実装を行ってください（コード末尾に未完の箇所あり）。

もし CHANGELOG に特定の追加情報（例えばリリースノートの粒度変更や追記したい動作確認手順など）が必要であればお知らせください。