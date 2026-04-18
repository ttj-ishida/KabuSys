CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティに関する変更

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。ブローカークライアントの生成、OrderRepository/OrderManager/Reconciler/RiskManager の組み立て、ExecutionEngine のスレッド起動・終了制御（stop flag / pid ファイル）を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知で安全にループを終了。
- 環境設定・管理
  - config_setup.py: 対話式の .env 作成/更新ウィザードを追加。秘密値はマスク表示し、テンプレート形式で .env を出力。
  - config.py: 環境変数読み込み・管理モジュールを追加。プロジェクトルート自動検出（.git または pyproject.toml）、.env/.env.local の自動ロード（必要に応じて無効化可能）、.env 行の詳細なパース（クォート・エスケープ・インラインコメント対応）、Settings クラスによる型付き設定アクセス（各種パス、閾値、env 検証など）を提供。
  - validate_config.py: 起動前に .env および config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや YAML ファイルの存在・パース検証、--strict オプションによる警告の FAIL 扱いをサポート。
- 監視・検証ツール
  - monitoring DB 初期化ユーティリティを使用して起動時に監視テーブルの冪等初期化を行う。
  - tools/paper_verification_report.py: ペーパートレード用 DB から運用検証レポートを生成する CLI を追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し、閾値に基づく PASS/FAIL 判定を出力。
- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: 候補選定（select_candidates）と重み算出（calc_equal_weights, calc_score_weights）を追加（スコア 0 の場合はフォールバックで等配分）。
  - portfolio.risk_adjustment: セクター集中上限を適用する apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（未知レジーム時はフォールバック）。
  - portfolio.position_sizing: allocation_method（"risk_based", "equal", "score"）対応の株数決定ロジックを実装。単元株丸め、1銘柄上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer 考慮、残差の再配分ロジックを含む。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: cross-platform（Windows/Linux/macOS 等想定）でプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティを追加。psutil を利用し、権限不足や未対応 OS の場合は警告してスキップ。

Changed
- 実行環境分離の方針を明確化
  - run_execution.py は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離（MockBrokerClient を利用する想定）。監視（run_monitoring.py）は環境にかかわらず本番 sqlite_path を使用する旨を明記。
- ログ管理
  - setup_logging() により全起動スクリプトで一貫したログ出力を実現。LOG_DIR / LOG_LEVEL の優先解決ルールを定義。
- .env 自動読み込みの挙動
  - 自動ロードはデフォルトで有効。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。.env.local は .env の上書きとして扱う（OS 環境変数は保護）。

Fixed
- 環境ファイルパースの堅牢化
  - config._parse_env_line において、シングル/ダブルクォート内でのバックスラッシュエスケープやクローズクォート検出、クォートなし値のインラインコメント判定（直前が空白/タブの場合のみ）を正しく処理するよう実装。これにより複雑な .env 行の誤パースを防止。
- ポーリング間隔の検証
  - run_monitoring._get_poll_interval() が MONITOR_POLL_INTERVAL の不正値（0 以下・非整数）を検出してデフォルト（60 秒）にフォールバックし、警告ログを出すように改善。
- 安全なリソースクローズ
  - run_monitoring/run_execution の finally ブロックで DB 接続（sqlite, duckdb）を確実にクローズするように実装。

Security
- シークレットの取り扱い改善
  - config_setup の対話表示でシークレット項目（J-Quants トークン、kabu API パスワード、LINE トークン等）は表示をマスク。
  - Settings._require は必須環境変数未設定時に明示的な例外を投げて起動時の見落としを防止。

Notes / Implementation details
- DuckDB と SQLite の併用: 分析用に DuckDB、監視/注文履歴用に SQLite を利用する設計。起動シーケンスで両方の接続を確立。
- PID / Stop フラグ: 実行制御のため data/*.pid および data/stop_requested.flag の存在を利用。停止フラグを検知したら安全にシャットダウンする挙動を共通実装。
- リスク管理既定値: RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を Execution 起動時に注入。初期 portfolio value は broker.get_available_cash() を使用。
- tools.paper_verification_report の閾値: 稼働率、注文/送信成功率、P95 レイテンシ等の検証閾値（コード内定数）を設定して PASS/FAIL を判定。

Deprecated
- なし

Removed
- なし

Security
- 既知のセキュリティ脆弱性は報告されていません。

補足
- 以降のリリースでは research.factor_research の実装完了（ファクター群の計算）、テストカバレッジの追加、より詳細なエラー監視・アラート（LINE 通知統合）などが想定されます。