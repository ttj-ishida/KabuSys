# Changelog

すべての重要な変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠します。

全般的な注意
- このリリースはパッケージ内部の複数モジュール（実行/監視スクリプト、設定管理、ポートフォリオ構築、ユーティリティ、検証ツールなど）の初期実装を含むマイナーバージョンの初版です。
- 構成は環境変数およびプロジェクトルートの .env / .env.local を基に動作します。README や .env.example を参照してください。

## [0.1.0] - 2026-04-18

### Added
- 実行・監視起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - プロセス優先度を高に設定し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定管理とウィザード
  - kabusys.config
    - .env/.env.local の自動読み込み機能（プロジェクトルートを自動検出）。
    - クォートや export 形式、インラインコメント等に対応した堅牢な .env パーサー。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス / 監視閾値 / 環境種別 などをプロパティで取得可能。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH / PID ファイル等のプロパティを実装。
  - kabusys.config_setup
    - 対話式の .env 作成・更新ウィザード。既存値の読み込み、シークレット項目のマスク表示、保存機能を備える。

- 設定検証 CLI
  - kabusys.validate_config
    - .env と config/*.yaml の簡易検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース（PyYAML が存在する場合）を実施。
    - `--strict` オプションで警告を失敗扱いにするモードを提供。

- Paper Trading 検証ツール
  - kabusys.tools.paper_verification_report
    - ペーパートレード DB を解析して検証レポートを出力する CLI。
    - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、API レイテンシ（avg/max/P95）等を集計。
    - 閾値に基づく PASS/FAIL 判定を実装（デフォルト閾値がソース内に定義）。

- ポートフォリオ構築モジュール
  - kabusys.portfolio
    - portfolio_builder: 候補選定（スコア/ランク順）、等金額・スコア重みの計算。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - position_sizing: 発注株数計算（risk_based / equal / score）、単元（lot）丸め、aggregate cap によるスケーリングと端数配分ロジック。
    - いずれも副作用なしの純粋関数として設計（DB 参照なし）。

- ユーティリティ
  - kabusys.utils.logging_setup
    - 統一的なログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
    - LOG_LEVEL / LOG_DIR の環境変数または引数による上書き対応。
  - kabusys.utils.process_priority
    - プロセス優先度（Windows の優先度クラス、POSIX の nice 値）および CPU affinity 設定ユーティリティを追加。
    - 対応 OS 以外では安全にスキップし、失敗時は警告ロギングでフォールバック。

- パッケージメタ
  - kabusys.__init__ にバージョン文字列 __version__ = "0.1.0" を追加。

- 研究用ファクター計算（初期実装）
  - kabusys.research.factor_research
    - Momentum / Value / Volatility / Liquidity などのファクター計算方針とモメンタム計算関数の骨格を実装（DuckDB 接続を受け取り prices_daily 等を参照）。
    - 実装は段階的に拡張予定（本ファイルは基礎実装フェーズとして含まれる）。

### Changed
- アーキテクチャ／運用に関する設計上の注意点をドキュメント化
  - 監視プロセスは本番の監視 DB（SQLITE_PATH）を環境にかかわらず使用する旨を明記。
  - ExecutionEngine は環境に応じて paper_trading 用 DB を利用して本番 DB と分離。
  - run_* スクリプトは起動時にプロセス優先度を High に設定し、停止フラグを検出して安全にシャットダウンするフローを採用。

### Fixed
- 環境読み込みの堅牢性向上
  - .env パーサーでシングル/ダブルクォート内のバックスラッシュエスケープ、export プレフィックス、コメント処理などに対応し、誤った読み込みによる設定ミスを低減。
  - .env 自動読み込み時に OS 環境変数を保護するため protected セットで上書きを制限する実装を追加。

### Security
- .env の取り扱いに関する注意喚起を明示
  - config_setup が .env を生成する際に「.env は絶対に Git にコミットしないこと」を明記。
  - 実行時の必須シークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings 経由で必須チェックを行い、未設定時は ValueError を発生させる。

### Notes / Known limitations
- research.factor_research は基礎実装段階であり、全ファクター計算の完成・最適化は今後の作業予定。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別単位対応を想定した TODO コメントあり。
- apply_sector_cap は "unknown" セクターに対してセクター上限を適用しない仕様（意図的）。
- process_priority / set_cpu_affinity は権限やプラットフォームによって失敗する可能性があり、その場合は警告ログを出力してスキップする安全策を実装。

---

今後の予定（例）
- factor_research の完全実装とユニットテスト追加
- ExecutionEngine / SystemMonitor 周りの統合テスト、運用ドキュメント整備
- 各モジュールの単体テストと CI パイプライン追加

もし CHANGELOG に追記してほしい詳細（例: リリースノート用に特定の機能説明やスクリーンショット、コマンド例など）があれば教えてください。