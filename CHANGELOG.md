# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

全般的に、以下の内容はリポジトリ内のコードから推測して作成しています（実装の注釈や TODO も含みます）。

## [Unreleased]

### Added
- なし

---

## [0.1.0] - 2026-04-19
初回公開リリース（推測）。以下はコードベースから推測される主要機能と改善点。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じて本番 DB / ペーパートレード用 DB を切り替え、BrokerClientFactory からブローカークライアントを生成してエンジンをスレッドで実行。停止フラグ（data/stop_requested.flag）や実行用 PID ファイルに対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検出で安全に終了。

- 環境設定・検証・ウィザード
  - config.py: 環境変数・設定管理モジュール。プロジェクトルート自動検出（.git / pyproject.toml）、.env/.env.local の自動読み込み（無効化フラグあり）、多数の設定プロパティ（DB パス、API トークン、Paper Trading 関連、監視閾値など）を提供。PAPER_FILL_MODE 等のバリデーション実装。
  - config_setup.py: .env を対話式に作成・更新するウィザード。既存 .env の読み込み、シークレットマスク表示、保存前の確認などをサポート。
  - validate_config.py: 起動前の設定検証 CLI。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば）や本番環境向けのガードを実施。--strict モードあり。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティ。stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイルハンドラをスキップしてフォールバックする実装。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティ。Windows / POSIX(nice) を吸収し、許可されない場合は警告を出してスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコアでソートして候補抽出（タイブレークルールあり）。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重の重み計算（スコア全0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限に基づき新規候補を除外するロジック。既存保有・売却予定を考慮したセクター別エクスポージャ算出。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash を超える場合はスケールダウン）や cost_buffer（手数料・スリッページ想定）を考慮した分配ロジックを備える。端数配分は残差の大きい順に lot 単位で追加する調整を実装。

- 監視・DB 初期化
  - monitoring.monitoring_db:init_monitoring_db を利用して監視用テーブルの存在を保証（冪等）。
  - run_monitoring / run_execution で sqlite3（監視・履歴 DB）および DuckDB（分析）へ接続。

- Paper Trading 用ユーティリティ
  - tools/paper_verification_report.py: ペーパートレードログ（SQLite）から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計して検証レポートを生成。閾値に基づいて PASS/FAIL を判定する CLI を提供。P95 計算や期間フィルタ（ISO8601 UTC 変換）に対応。

- 研究用モジュール（骨組み）
  - research/factor_research.py（断片）: DuckDB の prices_daily / raw_financials テーブルを用いたモメンタム等のファクター計算（関数シグネチャや定数が定義されているが一部未完）。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。主要パッケージの __all__ 定義あり。

### Changed
- 新規初版のため変更履歴はなし（初期追加）。

### Fixed
- 新規初版のため修正履歴はなし（ただしいくつかの堅牢化処理を実装済み）
  - MONITOR_POLL_INTERVAL の不正値（0 や負値・非整数）に対するフォールバック処理を実装（警告ログ出力）。
  - .env パーサはクォート／エスケープや行内コメントの扱いに対応し、.env の読み込み失敗時は警告発行して継続。
  - ログディレクトリ作成失敗や権限エラー時にファイルハンドラをスキップするフォールバック実装。
  - set_process_priority や set_cpu_affinity は権限不足や未実装 API 時に警告を出してスキップ。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数読み込みは .env を自動で読み込むが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。機密情報は .env に保存するため .env の Git 管理禁止を README 等で徹底することを推奨（config_setup のヘッダにも注意書きあり）。

### Notes / Known limitations / TODO（コード内コメントより抜粋）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャが過少見積りされる可能性があるため将来的に前日終値や取得原価などのフォールバック価格を導入予定（TODO）。
- portfolio/position_sizing:
  - 単元株数（lot_size）は現状グローバルな共通値（例:100）で扱っている。将来的に銘柄別の lot_map を導入することが計画されている（TODO）。
- research/factor_research.py:
  - ファイル末尾で関数実装が途切れている断片があり、完全実装がまだの可能性あり（推測）。

---

参考: 主な CLI / 実行コマンド（コードから推測）
- python -m kabusys.run_execution
- python -m kabusys.run_monitoring
- python -m kabusys.config_setup
- python -m kabusys.validate_config [--strict]
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。必要であればリリースノートを利用者向けに平易な文章でまとめ直します。