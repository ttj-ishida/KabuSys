CHANGELOG
=========

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」方式に準拠しています。

フォーマット:
- Unreleased（未リリース）セクションは将来の変更用に確保しています。
- 日付は YYYY-MM-DD 形式で記載します。

Unreleased
----------

- 特になし。

0.1.0 - 2026-04-18
------------------

Added
- 初回リリースを公開。
- 基本設定/起動用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで実行し、プロセス内の stop フラグ（data/stop_requested.flag）検知で安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定し、実行中は execution.pid を使用。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（監視データは本番 DB に集約）。

- 設定管理
  - config.py: 環境変数 / .env 読み込み・検証ロジックを追加。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env/.env.local を自動ロード。
    - export KEY=val 形式、クォートされた値（エスケープ対応）、行末コメントの扱い等の堅牢なパーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 各種設定プロパティ（DB パス、pid/kill flag、しきい値、PAPER_FILL_MODE 検証など）を提供。
    - settings = Settings() インスタンスをエクスポート。
- 設定支援 CLI
  - config_setup.py: .env の対話式ウィザードを追加。
    - 初期作成・更新を支援。シークレット項目は表示をマスク。
    - 保存テンプレート（.env の標準項目）を生成。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数やパス、config/*.yaml の存在・パース（PyYAML が利用可能な場合）をチェック。
    - KABUSYS_ENV の値チェックや本番環境向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実施。
    - --strict モードで警告も失敗扱いに可能。

- ユーティリティ
  - utils/logging_setup.py: 共通ログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。デフォルト logs/ ディレクトリ、30 日保持。
    - LOG_LEVEL / LOG_DIR / app_name で挙動をカスタマイズ可能。
    - ファイル出力に失敗した場合はコンソールのみへフォールバック。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応し、psutil ベースで優先度を設定。AccessDenied 等を捕捉してフォールバック。
    - set_cpu_affinity による CPU ピニング機能を提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター毎のエクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数（bull/neutral/bear）を返却。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer を考慮した安全な配分アルゴリズムを実装。

- 解析/レポート
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）からデータを集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出。
    - 基準値（稼働率 ≥ 99%、成立率 ≥ 90%、送信率 ≥ 95%、P95 ≤ 200ms）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）や --db オプションで対象 DB を指定可能。

- 研究（ファクター計算）
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（Momentum / Value / Volatility / Liquidity 設計方針を記載）。
    - モメンタム計算（1M/3M/6M、MA200 乖離 等）を想定した定数・関数設計を含む（実装の続きあり）。

- パッケージ情報
  - __init__.py にてバージョンを 0.1.0 に設定。

Changed
- 監視/実行のDB取り扱いに関する注意点を明確化。
  - 監視（run_monitoring）は常に本番 sqlite_path を参照（運用上の意図的な設計）。
  - 実行（run_execution）は paper_trading 環境では paper_sqlite_path を使用することで本番データと明確に分離。

Fixed
- なし（初回リリース）。

Security
- .env は絶対にリポジトリへコミットしない旨をドキュメント・config_setup のヘッダに明記。

Notes / Implementation details
- .env パーサは export キーワード、クォート内エスケープ、行末コメントの取り扱いなどを細かく扱うため、一般的な .env 形式の柔軟な読み込みに対応します。
- 各コンポーネント（ExecutionEngine 周辺、monitoring）で使用する DB テーブルは init_monitoring_db によって起動時に存在を保証（冪等）。
- process_priority / logging_setup は実行環境に依存する失敗を許容する（権限不足などで警告を出し処理を継続）。

開発者向け補足
- validate_config の YAML 検証は PyYAML がインストールされている場合にのみ実行されます。CI で厳密に検証する場合は PyYAML を要インストール。
- PAPER_FILL_MODE 等、環境変数値のバリデーションは Settings クラス側で行われるため、誤った値は起動時に例外となります。

今後の予定（参考）
- research/factor_research の完全実装（ファクター算出クエリの完成）。
- 銘柄毎の lot_size をサポートするための stocks マスタ導入と position_sizing の拡張。
- モニタリング／実行のさらに細かいメトリクス収集とアラート連携（LINE など）。

------------------------------------------------------------
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして公開する際は、実装者による確認・補足情報の追記を推奨します。