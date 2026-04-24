CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の慣例に準拠しています。

フォーマット:
- 各リリースは日付付きで記載
- セクション: Added, Changed, Fixed, Deprecated, Removed, Security

Unreleased
----------
（現在の開発中の変更はここに記載してください）

[0.1.0] - 2026-04-24
-------------------

Added
- 初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築、検証ツール群を追加。
- 起動スクリプト:
  - src/kabusys/run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視データベースは環境に依らず本番用 sqlite_path を使用。
  - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。停止フラグ/実行 PID ファイルを利用した安全な起動・停止制御を実装。
- 設定管理:
  - src/kabusys/config.py: Settings クラスを導入し、環境変数から各種設定（DB パス、API トークン、しきい値など）を取得。自動 .env ロード（.env → .env.local の順、OS 環境変数を保護）に対応。PAPER_FILL_MODE 等のバリデーションを実装。
  - src/kabusys/config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。secret 項目のマスク表示や選択肢サポートを備える。
  - src/kabusys/validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パースをチェック。--strict モードをサポート。
- ロギング・プロセス制御ユーティリティ:
  - src/kabusys/utils/logging_setup.py: 統一的なログ設定関数 setup_logging を追加。コンソール（stdout）と日次ローテーションファイルハンドラ（TimedRotatingFileHandler, 30日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - src/kabusys/utils/process_priority.py: プロセス優先度設定と CPU affinity 設定を提供。Windows/Linux/macOS の違いを吸収し、権限不足や未対応 OS の場合は警告を出してスキップする。
- ポートフォリオ構築ライブラリ:
  - src/kabusys/portfolio/portfolio_builder.py: シグナル候補の選定（select_candidates）、等配分・スコア加重の重み計算（calc_equal_weights、calc_score_weights）を実装。スコア全0 の場合は等配分へフォールバックし警告を出す。
  - src/kabusys/portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターは制限対象外。regime に対するデフォルトマッピングを提供（bull/neutral/bear）。
  - src/kabusys/portfolio/position_sizing.py: 発注株数算出ロジックを実装（risk_based / equal / score の allocation_method をサポート）。単元株（lot_size）で切り捨て、aggregate cap 超過時はスケーリングして残余を優先度に応じて割当てる。cost_buffer による保守的なコスト見積りに対応。
- ツール:
  - src/kabusys/tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 等）を算出し PASS/FAIL 判定を行う。デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- リサーチ:
  - src/kabusys/research/factor_research.py: ファクター計算モジュール（モメンタム、MA200 乖離等）の骨格を追加。DuckDB 接続を受け取り prices_daily/raw_financials を参照する設計。
- パッケージ情報:
  - src/kabusys/__init__.py: バージョン 0.1.0 を設定。

Changed
- （初回リリースのため変更履歴はなし。上記は追加機能の説明。）

Fixed
- （初回リリースのため修正履歴はなし。）

Deprecated
- なし

Removed
- なし

Security
- 機密情報（トークン・パスワード）は .env にて管理する方針を明示。.env は絶対にコミットしない旨のテンプレート（config_setup が生成）を追加。

注記・運用上の重要ポイント
- .env 自動ロード:
  - デフォルトでプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env/.env.local を自動ロード。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env.local は .env の上書き用で、既存 OS 環境変数は保護される。
  - .env のパースは export プレフィックス、シングル/ダブルクオート、エスケープ、インラインコメントなどに対応。
- 実行環境分離:
  - paper_trading モードでは paper_trading 用 SQLite を使用することで本番 DB を分離（run_execution）。
  - 監視（run_monitoring）は環境に関らず設定された sqlite_path を使用する設計になっている点に注意。
- プロセス制御:
  - 起動時にプロセス優先度を "high" に変更しようと試みる（権限がない場合は警告）。
  - 停止フラグ（data/stop_requested.flag 等）を用いた安全停止に対応。
- ロギング:
  - すべての起動スクリプトから setup_logging を呼び出すことでログが統一される。標準出力は stdout を使用（cron 等でのリダイレクトを想定）。
- ポジション/注文ロジックの挙動:
  - calc_score_weights は全銘柄スコアが 0 の場合、自動的に等金額配分にフォールバックし警告を出す。
  - calc_position_sizes は lot_size（デフォルト 100）単位で丸める。aggregate cap 超過時は縮小→残余で大きい fractional 割合を優先して lot 単位で追加配分する再現性のあるアルゴリズムを採用。
- Paper Trading 検証:
  - tools/paper_verification_report のデフォルト閾値はソース内の定数で定義。P95 はサンプルから算出（空データは N/A）。

今後の検討・ TODO
- portfolio.position_sizing の価格欠損時のフォールバック（前日終値や取得原価等）の導入。
- factor_research の実装完遂（ファイル末尾で途切れています）。
- monitoring/system_monitor や execution の内部実装詳細（monitor.check_once(), ExecutionEngine.run_session など）は別モジュールにあり、必要に応じてリリースノートで詳細を追記。

補足
- 上記はリポジトリ内のコードから推測して記載したものであり、実際の運用手順や既知のバグ、既存外部依存（例: psutil, duckdb, PyYAML 等）のインストール手順は別途 README や運用ドキュメントを参照してください。