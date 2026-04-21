# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

- リリースノートは意図的にコードベースから推測して作成しています。実際の変更履歴や日付はプロジェクト管理の記録に合わせて適宜調整してください。

## [0.1.0] - 2026-04-21

Added
- 初回リリース相当の機能群を追加。
- 起動スクリプト / CLI:
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視データは環境にかかわらず本番の sqlite_path を使用する仕様。
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用して data/paper_trading.db に記録し、本番 DB と分離する挙動を提供。エンジンは別スレッドで実行し、停止フラグ検知で安全に停止可能。
  - validate_config: .env および config/*.yaml の設定を起動前に検証する CLI を追加。--strict モードで警告をエラー扱いにするオプションあり。
  - config_setup: インタラクティブな .env 作成/更新ウィザードを追加。よく使う設定項目とデフォルト、マスク入力等をサポート。
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。期間指定や DB パス指定が可能で、稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出して PASS/FAIL 判定を出力する。

- 設定管理:
  - Settings クラスを導入し、環境変数経由でアプリケーション設定を一元化（J-Quants、kabu API、DB パス、監視閾値、KABUSYS_ENV など）。
  - プロジェクトルート自動検出ロジックを導入（.git または pyproject.toml を基準）。これにより .env の自動ロードが CWD に依存せず動作。
  - .env 自動ロード: OS 環境変数 > .env.local > .env の優先順位で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理など）。

- ロギング・プロセス管理ユーティリティ:
  - logging_setup: ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（デイリーローテーション、30 日保持）を統一的に設定するユーティリティを追加。既存ハンドラの二重設定を防止するために既存ハンドラをクリアする実装。ログレベル・ログディレクトリの解決ロジックを提供（引数 > 環境変数 > デフォルト）。
  - process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS の際は安全にスキップして警告を出力。

- ポートフォリオ構築関連（純粋関数群）:
  - portfolio_builder: シグナル選定（スコア降順、タイブレーク）と重み計算（等配分、スコア加重）を実装。スコア合計が 0 の場合は等配分へフォールバック。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。セクター不明は "unknown" 扱いで上限適用除外。未知レジームは警告のうえフォールバック。
  - position_sizing: allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出を実装。単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）や aggregate cap によるスケールダウンと残差処理（lot 単位で再配分）をサポート。

- リサーチ:
  - research/factor_research モジュール（骨格）を追加。DuckDB 接続を受け取り、Momentum/Value/Volatility/Liquidity 等のファクター計算を行う設計（prices_daily / raw_financials テーブル参照）。（注：ファイルは途中まで含まれているが、設計方針と定数・開始部分を実装済み）

Changed
- 監視（monitoring）と実行（execution）で DB 初期化を冪等に保証するため init_monitoring_db を起動時に実行するように統一。
- run_monitoring の動作: 環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を参照して監視データを記録する明示的な仕様とした（意図的な分離）。
- run_execution: paper_trading モード時は paper_sqlite_path を使用して発注ログを本番 DB と分離。BrokerClientFactory により paper/live を自動で切り替え。
- logging_setup: ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続する堅牢化を実施。
- process_priority: 未対応 OS や権限制約時に失敗を例外ではなく警告で扱うように変更（起動継続確保）。

Fixed / Improved
- 環境変数パーサの強化により次のケースに対応:
  - export PREF=val 形式
  - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
  - クォートなし値についたコメント（#）を適切に扱う（先行スペース有無で判定）
- MONITOR_POLL_INTERVAL の取り扱いを堅牢化:
  - 非数値や 0 以下の値を入力した場合、ログ出力のうえデフォルト値（60 秒）にフォールバックして ValueError を回避。
- Position sizing の aggregate スケールダウン時の再配分ロジックを実装し、残余キャッシュで lot_size 単位の追加配分を行うことでより確定的な配分を実現。
- paper_verification_report:
  - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出するレポート機能を実装。データ欠如時の N/A ハンドリングと PASS/FAIL 判定ロジックを追加。
  - 日付フィルタは ISO8601 UTC 文字列に変換してクエリに適用。

Security
- .env 作成ウィザードが .env ファイルを生成する旨の注意（.env を Git にコミットしない）を明記。

Notes / Misc
- パッケージバージョンを __version__ = "0.1.0" に設定。
- DuckDB と SQLite の両方をデータ層として利用する構成を採用（分析用: DuckDB、監視/トレードログ: SQLite）。
- 一部モジュール（broker_factory 等）はファクトリ/インタフェース設計で実装されており、環境（paper/live）に応じて振る舞いを切替可能。
- まだ実装途中の箇所（例: research/factor_research の続き）は存在するため、将来的な拡張や微調整が見込まれる。

---

今後のリリースで想定される項目（例）
- factor_research の完全実装（各ファクターの SQL/計算ロジック完結）
- strategy / execution のテスト補完、BrokerClient のモックと統合テスト
- ドキュメント（API 仕様・デプロイ手順・運用ガイド）の整備
- CI による自動検証（lint / unit tests / type checks / packaging）

もし CHANGELOG の内容や表現（リリース日、カテゴリの分配、詳細レベル）をプロジェクト方針に合わせて調整したい場合は、対象箇所を指定していただければ修正します。