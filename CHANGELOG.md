# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新リリース
------------

### [0.1.0] - 2026-04-19

初回リリース。以下の主要機能・ユーティリティを含みます。

Added
- 基本アプリケーション情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。
- 環境設定・読み込み
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml 基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - 独自の .env パーサを実装（export 文対応、シングル/ダブルクォートとエスケープ、行内コメント処理）。
  - Settings クラスで環境変数をラップ（各種パス、API トークン、Paper Trading 用設定、監視閾値等をプロパティ化）。
- 設定支援 CLI
  - config_setup: 対話式ウィザードで .env を生成／更新（項目定義・既存値読み込み・シークレットマスク表示）。
  - validate_config: 起動前チェック CLI を実装（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パースなど）。--strict オプションで警告を失敗扱いにできる。
  - validate_config は PyYAML 非依存（未インストール時は YAML 検証をスキップし警告を出す）。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプト
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成フローを採用（本番/モックの切替想定）。
    - ExecutionEngine をデーモンスレッドで実行し、 data/stop_requested.flag による善後処理で停止可能。実行 PID 管理をサポート（data/execution.pid）。
    - init_monitoring_db を呼び出し監視テーブルの存在を保証（冪等）。
    - デフォルトの RiskManager 設定（例: max_position_pct=0.20, max_utilization=0.80 など）を採用。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト
    - 起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path（data/monitoring.db 等）を使用する設計。
    - stop フラグファイル検知でループを終了、KeyboardInterrupt による終了もハンドル。
- ロギング・プロセス制御ユーティリティ
  - logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。ログディレクトリは引数・環境変数で上書き可能。既存ハンドラをクリアして二重設定を防止。
  - process_priority: Windows/Linux（および一部 POSIX）でのプロセス優先度設定を抽象化。set_cpu_affinity による CPU affinity 設定を提供。権限不足や未対応環境では安全にスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順（同点は signal_rank でブレーク）で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限により新規候補を除外するロジック。既存保有のセクター別時価を計算し、max_sector_pct を超えるセクターの候補を排除（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却し、未知レジームは警告と共に 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づき発注株数（単元株丸め）を計算。max_position_pct, max_utilization, lot_size, cost_buffer 等を考慮した aggregate cap スケーリングを実装。
- Research / ファクター計算
  - research.factor_research: DuckDB 接続を用いたモメンタム・ボラティリティ等のファクター計算機能の基盤（関数シグネチャと定数を定義、モメンタム計算開始の骨子あり）。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。稼働率（uptime）、注文成立率（fill rate）、送信率、P95 レイテンシ等を集計・判定し PASS/FAIL を出力。日付フィルタ（--from / --to）、DB パスの上書き（--db / 環境変数）に対応。
- データベース周り
  - duckdb / sqlite の接続確立を各起動スクリプトで行う（パスは Settings または環境変数で設定可能）。
  - init_monitoring_db を用いて監視用テーブルが存在することを保証。

Changed
- ロギングの標準出力を stderr から stdout に変更（cron 等で stdout/stderr を一本化する運用に配慮）。
- .env 読み込み順序を明記（OS環境 > .env.local > .env）。既存 OS 環境は保護される（protected set）。

Fixed
- 環境変数パースの耐障害性向上
  - クォート内のバックスラッシュエスケープや行内コメント処理を改善して .env の柔軟な記述に対応。
- run_execution/run_monitoring におけるリソースクローズの確実化（finally ブロックで DB 接続をクローズ）。

Security
- 機密情報（J-Quants リフレッシュトークン、kabu API パスワード）は Settings で必須にし、config_setup ではシークレット入力をマスク表示する UI を提供。なお .env の扱いに関して README 等で Git へのコミット禁止を明示（config_setup のヘッダ内コメント）。

Notes / Known limitations
- research.factor_research の実装は一部（モメンタム計算の詳細実装など）で継続実装が必要（モジュールの冒頭に設計方針と定数はあるが、関数本体は未完）。
- apply_sector_cap は price_map に欠損（0.0）価格がある場合にエクスポージャーを過小評価する可能性がある旨を TODO として明記。将来的にフォールバック価格の導入が検討されている。
- process_priority / set_cpu_affinity は権限がない場合や未対応 OS ではスキップし、起動は継続する設計。
- validate_config の YAML 検証は PyYAML 未インストール時にスキップされる（警告）。

未分類の内部改善
- 各種モジュールは副作用を抑えた設計（多くが純粋関数または Settings を介した副作用管理）を心がけており、ユニットテスト容易性を考慮した実装になっています。

今後の予定（例）
- research.factor_research の完全実装
- strategy / execution 部分の単体テスト充実
- 銘柄別単元（lot_size）対応の拡張（stocks マスタからの読み込み）
- .env のより厳密なサニタイズ／検証機能の追加

------------------------------------------------------------
（注）本 CHANGELOG はソースコードの現在の実装内容から推測して作成しています。詳細な設計意図やドキュメントに基づく正式な変更履歴作成時には、コミット履歴やリリースノートの確認を推奨します。