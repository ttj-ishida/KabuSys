Keep a Changelog
-----------------

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 基本ライブラリとバージョンを追加
  - パッケージバージョン: __version__ = 0.1.0（src/kabusys/__init__.py）
- 環境設定・管理
  - Settings クラスを実装（src/kabusys/config.py）。環境変数から各種設定（DBパス、APIトークン、監視閾値など）を取得するインターフェースを提供。
  - .env 自動読み込み機能を実装。プロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local をロード（OS 環境変数優先、.env.local は上書き）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パースの堅牢化（export プレフィックス、クォート文字・エスケープ、インラインコメント対応）。
- 対話式設定ウィザード CLI
  - config_setup（src/kabusys/config_setup.py）を追加。対話で .env を作成・更新し、必須/任意項目、デフォルト、マスク表示をサポート。
- 設定検証 CLI
  - validate_config（src/kabusys/validate_config.py）を追加。.env と config/*.yaml の存在・基本整合性を検査。--strict オプションで警告を失敗扱いに。
  - YAML が無ければパース検証をスキップし警告を出す（PyYAML インポートチェック）。
- 実行・監視プロセス起動スクリプト
  - run_execution（src/kabusys/run_execution.py）を追加。ExecutionEngine の起動フローを実装。paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring（src/kabusys/run_monitoring.py）を追加。SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）による終了制御をサポート。
- 実行支援・ユーティリティ
  - process_priority ユーティリティを追加（src/kabusys/utils/process_priority.py）。Windows/Linux/macOS でプロセス優先度（high/normal/low）を設定。CPU affinity を最初の N コアに固定する関数も提供。アクセス権限不足等の失敗は警告ログで安全にスキップ。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合のフォールバック挙動を定義。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター上限適用 apply_sector_cap（売却予定銘柄の除外、unknown セクターの扱い等）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とデフォルトフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - allocation_method（risk_based / equal / score）に基づいて発注株数を算出。lot_size（単元）丸め、per-stock 上限、aggregate cap（available_cash を超えた場合のスケーリング）を実装。コストバッファと残差配分ロジックあり。
  - 上記をまとめてパッケージとしてエクスポート（src/kabusys/portfolio/__init__.py）。
- 研究用ファクター計算
  - factor_research（src/kabusys/research/factor_research.py）を追加。DuckDB を用いた prices_daily / raw_financials ベースのファクター計算（Momentum：1/3/6M リターン、MA200乖離、Volatility：ATR20、流動性指標等）。データ不足時の None 返却など堅牢な SQL を組成。
- ペーパートレード検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加。paper_trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計しレポート出力。基準値（閾値）を定義して PASS/FAIL 判定を行う。
- モニタリング DB 初期化ユーティリティ呼び出しの組み込み
  - run_execution/run_monitoring で監視テーブルの初期化 init_monitoring_db を呼ぶ（冪等保証）。
- 実行フローの安全策
  - 起動時にプロセス優先度を高く設定する処理を最初に実行（run_execution/run_monitoring）。停止フラグ検出で安全に停止。

Changed
- 設定の既定値と優先度
  - 環境変数の優先度: OS 環境変数 > .env.local > .env（自動ロードの実装により明示化）。
- run_monitoring の DB 接続動作
  - Monitoring は KABUSYS_ENV に依存せず、本番 sqlite_path を使用する設計になっている旨をドキュメント化（コード内コメント）。
- paper_trading 動作分離
  - run_execution は paper_trading 環境のとき専用の paper_sqlite_path を使用して本番データと完全分離するように変更。
- 環境変数のバリデーション強化
  - Settings.paper_fill_mode の有効値チェック、および Settings.env / log_level の許容値検証を実装。無効値時に ValueError を発生させ明示的にエラーを知らせる。

Fixed
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応し、誤パースによる設定ミスを低減。
- ファイル・ディレクトリ存在チェックの警告
  - validate_config にて DB パスや設定ファイルの親ディレクトリが存在しない場合は警告を出し、起動時に自動作成される可能性があることを明示。

Security
- なし（このリリースでは特段のセキュリティ修正は含まれません）

Deprecated
- なし

Removed
- なし

注記 / マイグレーション
- .env 自動読み込みを利用する場合、既存の OS 環境変数は保護（上書きされない）されます。CI やテストで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading 環境ではデフォルトの SQLite が data/paper_trading.db に切り替わります。既存の本番 monitoring.db を上書きしないように注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL によりポーリング間隔を変更できます。不正な値（整数以外や <=0）は警告のうえデフォルト（60秒）にフォールバックします。

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0