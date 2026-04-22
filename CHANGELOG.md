# Changelog

すべての重大な変更をここに記録します。フォーマットは Keep a Changelog に準拠します。  
現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-22

### Added
- 初回リリース。主要コンポーネントとユーティリティ群を追加。
- 起動スクリプト:
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。スレッドで ExecutionEngine を起動し、data/execution.pid に PID を記録。
    - 停止制御: プロジェクトルートの data/stop_requested.flag を検出するとエンジンを安全に停止。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。MockBrokerClient の使用を想定する設計（BrokerClientFactory を介して生成）。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - Monitoring 用 DB 接続は環境にかかわらず設定された sqlite_path（デフォルト: data/monitoring.db）を使用。
- 設定管理:
  - config.py
    - .env ファイルと環境変数の読み込み機能を実装。プロジェクトルート（.git または pyproject.toml）を基準に自動ロード。
    - .env のパースは export プレフィックス、クォート値、エスケープ、行内コメント等に対応。
    - Settings クラスを提供し、各種設定値（J-Quants トークン、kabu API、DB パス、監視しきい値、環境判定等）をプロパティで取得可能。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目はマスク表示、既存値の再利用、確認プロンプト後に .env を保存。
- 設定検証 CLI:
  - validate_config.py
    - .env および config/*.yaml の存在・基本整合性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が利用可能な場合）などを実施。
    - --strict オプションで警告も失敗として扱う。
- ロギング・プロセス制御ユーティリティ:
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを提供。stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 関数引数による解決をサポート。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定を提供。nice 値や Windows の priority class を使って優先度を変更。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（アクセス権限等で失敗した場合は警告を出力してスキップ）。
- ポートフォリオ構築関連（純粋関数、DB 非依存）:
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates) と配分重み（等金額: calc_equal_weights、スコア重み: calc_score_weights）を実装。
    - スコア合計が 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装。既存保有のセクター暴露に基づき新規候補を除外。
    - 不明セクター ("unknown") は上限チェック対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、全体利用率（max_utilization）を考慮。
    - cost_buffer を使った保守的なコスト見積もり、利用可能現金を超えた場合のスケールダウンと残差に基づく追加配分ロジックを実装。
- 研究・指標:
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールの実装方針と一部機能（モメンタム計算開始）の追加。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95））を集計してレポートを生成する CLI を追加。
    - デフォルトしきい値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 latency <= 200ms）し、Pass/Fail 判定を出力。
- DB インテグレーション:
  - SQLite（監視 / ペーパートレード）および DuckDB（分析用）の接続箇所を統合。監視用 DB の初期化を保証する init_monitoring_db 呼び出しを各所で実行（冪等）。
- パッケージ情報:
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / 注意事項
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値が設定されている場合や 0 以下の値に対してデフォルトへフォールバックします（time.sleep に渡すと例外になるための保護）。
- process_priority や CPU affinity の設定は権限不足で失敗する場合があり、その場合はログに警告を出して処理を継続します。
- .env の自動ロードはプロジェクトルートが特定できない場合および環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されている場合に無効化されます。
- Portfolio モジュールは純粋関数群として設計されており、データベースアクセスを行いません。テストしやすさと再利用性を重視しています。
- research/factor_research.py は一部実装が続きます（モメンタム等の詳細計算ロジックは継続実装予定）。

---

今後の予定:
- ExecutionEngine / BrokerClient 周りの統合テストおよびドキュメント整備
- research モジュールの追加ファクター実装完了
- モニタリング・アラート（LINE 等）連携の実装強化
- ユニットテスト・CI の整備

 (以上)