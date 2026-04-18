CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」準拠です。
リリース日 YYYY-MM-DD はパッケージのリリース日に合わせて更新してください。

履歴
----

### [0.1.0] - 2026-04-18
初回リリース。KabuSys の基本機能群を実装しました（環境設定、起動スクリプト、監視、実行エンジンの起動補助、ポートフォリオ構築ユーティリティ、Paper Trading 検証ツール、ユーティリティ類など）。

Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 環境 / 設定関連
  - Settings クラス (src/kabusys/config.py)
    - 環境変数からの設定読み込みを提供。J-Quants / kabuステーション / DB / ログなどの設定をプロパティとして取得可能。
    - KABUSYS_ENV（development/paper_trading/live）の検証ロジック、LOG_LEVEL の検証、Paper Trading 用の DB パス・fill モードなどをサポート。
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env 読み書きユーティリティ・対話ウィザード (src/kabusys/config_setup.py)
    - 対話式に .env を生成・更新するウィザード。秘密項目はマスク表示。
    - デフォルト値、選択肢、説明を備えた項目定義を提供。書き込み時にテンプレートヘッダを付与。
  - 設定検証 CLI (src/kabusys/validate_config.py)
    - .env と config/*.yaml の存在や基本整合性を検証する CLI。--strict オプションで警告も失敗扱いにできる。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリチェック、YAML パース確認（PyYAML がインストールされている場合）などを実施。
- 起動スクリプト
  - Execution 起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine を起動する補助スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド起動と停止フラグ（data/execution.pid / data/stop_requested.flag）対応。
  - Monitoring 起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルで安全停止。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- 監視 / DB 初期化
  - init_monitoring_db を用いた監視テーブル初期化呼び出し（冪等）
- ログ・プロセス制御ユーティリティ
  - logging_setup (src/kabusys/utils/logging_setup.py)
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30日保持）を設定。
    - LOG_DIR の作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - process_priority (src/kabusys/utils/process_priority.py)
    - Windows/Linux/macOS を透過してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を提供（権限や環境により失敗時は警告してスキップ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder (src/kabusys/portfolio/portfolio_builder.py)
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0.0 の場合は等分配にフォールバック。
  - risk_adjustment (src/kabusys/portfolio/risk_adjustment.py)
    - セクター集中制限を適用する apply_sector_cap（既存保有を考慮して新規候補を除外）。
    - 市場レジームに応じて投下資金倍率を返す calc_regime_multiplier（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は 1.0 にフォールバック）。
  - position_sizing (src/kabusys/portfolio/position_sizing.py)
    - 各銘柄の発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap のスケーリングと残差処理（fractional remainder に基づき lot 単位で追加配分）を実装。
    - cost_buffer を反映した保守的なコスト見積りによりスケールダウンを実施。
- 研究 / ファクター計算
  - factor_research (src/kabusys/research/factor_research.py)
    - Momentum / Value / Volatility / Liquidity のファクター設計方針と計算ユーティリティの骨子を追加（DuckDB 経由で prices_daily / raw_financials を参照する方針）。
    - （ファイル末尾で実装途中の箇所あり。）
- ツール
  - Paper Trading 検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py)
    - ペーパートレード用の SQLite DB（デフォルト data/paper_trading.db）から複数指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ: avg/max/P95）を集計し、PASS/FAIL を判定してレポート出力。
    - P95 算出、期間フィルタ（--from/--to）および --db オプションをサポート。閾値はファイル内定数で定義。
- パッケージ公開用 __all__ の整理 (src/kabusys/portfolio/__init__.py)

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Deprecated
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / Known issues / TODO
- factor_research.py は一部実装が途中で終端している箇所があります（ファイル末尾で開始された calc_momentum の実装未完）。今後のリリースで完成予定。
- apply_sector_cap は price_map に欠損（価格が 0.0）ある場合にエクスポージャーを過小評価する可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討。
- position_sizing の将来的拡張として銘柄別の lot_size マスタ対応を想定した TODO コメントあり。
- process_priority / set_cpu_affinity は OS 権限や psutil の実装状況により失敗する可能性があり、その場合は警告を出して処理をスキップする設計。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラをスキップして stdout のみで動作する。CI/権限環境での運用時は LOG_DIR のパーミッションに注意。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。テストなどで自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB は明示的に分離していますが、設定ミスによる上書きを防ぐため .env の内容と validate_config の出力（特に --strict モード）で事前確認してください。
- run_execution/run_monitoring は停止フラグ（data/stop_requested.flag）や PID ファイルを利用して安全停止をサポートします。起動環境やデプロイ方法に合わせてファイルパスを調整してください（Settings で上書き可能）。

今後の予定
- factor_research の完成（ファクター計算の SQL/Python 実装完了）
- ExecutionEngine / Broker クライアント周りの統合テスト強化
- ポートフォリオ最適化（リバランス、コスト推定精度向上）
- config.yml のスキーマ検証やより厳密な設定チェックの追加

以上。