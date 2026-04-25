Changelog
=========

すべての重要な変更履歴を記載します。本プロジェクトは Keep a Changelog の形式に準拠しています。

0.1.0 - 2026-04-25
------------------

Added
- 初回リリースを作成しました（バージョン: 0.1.0）。
- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。  
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行管理（スレッド起動／停止）、停止フラグ（data/stop_requested.flag）と PID ファイル管理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でループ間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化・参照する仕様。停止フラグでループを終了。
- 設定 / CLI
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成／更新を支援）。生成・更新した .env の書式・注意書きの出力をサポート。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・YAML パース検証（PyYAML 利用可時）などを実行。--strict オプションで警告を FAIL 扱いにできる。
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数を集計して PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定可能。
- 設定管理
  - config.py: 環境変数・設定管理モジュールを追加。  
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）、.env 自動読み込み（.env → .env.local の順、OS 環境変数は保護）を実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。  
    - Settings クラスで各種設定プロパティを提供（J-Quants / kabuAPI / DuckDB / SQLite / paper_trading 用パス / PID/KILL フラグ / リソース閾値など）。PAPER_FILL_MODE の値検証を実装。
- ログ / プロセスユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。  
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーへ設定。既存ハンドラはクリアして重複出力を防止。LOG_DIR/LOG_LEVEL の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。Windows / POSIX（Linux/Mac/FreeBSD）を吸収し、psutil を用いて優先度設定を行う。設定失敗時は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク）、等金額・スコア重みの計算を実装。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）を実装。lot_size（単元）丸め、max_position_pct、max_utilization、コストバッファ、aggregate cap によるスケールダウン、スケール後の端数配分ロジックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターの取り扱いやレジームフォールバックの挙動を明記。
  - portfolio/__init__.py で上記機能を公開。
- monitoring / DB 初期化
  - 監視 DB 初期化用の init_monitoring_db を各起動処理から呼び出し、監視テーブルの存在を保証（冪等）。
- research
  - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。momentum 計算の定義と定数が追加されている（実装は続きを想定）。
- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

Fixed / Improved
- .env パーサーの強化（config._parse_env_line）
  - export プレフィックス（export KEY=val）に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理と閉じクォート探索に対応。
  - 非クォート値におけるインラインコメント判定は「# の直前が空白またはタブの場合のみ」コメントとみなす仕様にして誤判定を低減。
- .env 自動読み込み
  - OS 環境変数を protected として扱い、override の場合でも保護する設計に変更（テスト・システム環境の上書きを防止）。
- ロギング設定
  - 既存ハンドラを一度 flush/close してから削除することで、複数回 setup_logging を呼んでもログが重複しないよう改善。
  - StreamHandler は stdout を利用（cron 等で stdout/stderr をリダイレクトする運用を想定）。
- run_* スクリプトの堅牢化
  - プロセス優先度設定（起動時に最初に high を試みる）を導入。権限不足などで失敗しても起動継続するよう警告で処理を継続。
  - 停止フラグのポーリング／検知ロジックと、例外発生時のログ出力（monitor.check_once の例外をキャッチして次回ポーリングまで待機）を実装。

Notes / Known issues / TODO
- research/factor_research.py は momentum 関連の実装が途中で切れており、完全実装は今後の課題。README/ドキュメントにある PortfolioConstruction.md / StrategyModel.md に準拠する設計方針は記載済み。
- position_sizing の価格フォールバック（price が欠損時の前日終値や取得原価使用）は TODO として残しています（現在は price が欠損だと当該銘柄はスキップされます）。
- run_monitoring は監視用 DB に本番 sqlite_path を直接使用するため、監視用途以外での誤った接続を避ける運用上の注意が必要です。
- logging_setup のファイルハンドラ作成失敗時はコンソール出力のみにフォールバックしますが、ログディレクトリ権限の確認を推奨します。

Deprecated
- なし

Removed
- なし

Security
- 現時点で特定のセキュリティ修正はありません。機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に保存することを前提としていますが、.env の Git 管理禁止（生成ファイルのヘッダ）を明記しています。運用時はシークレット管理ポリシーを検討してください。