Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[0.1.0] - 2026-04-25
--------------------

Added
- 実行スクリプト / 起動エントリを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) を検知して終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用の DB を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）および pid ファイル管理に対応。
    - BrokerClientFactory を利用して実際の/モックのブローカークライアントを生成。
    - ExecutionEngine をスレッドで実行し、停止フラグで安全に停止可能。

- 設定管理とセットアップ
  - config.py: 環境変数読み込み・解釈を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（無効化用 KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - env ファイルの行パースはクォート・エスケープ・インラインコメントに対応。
    - 各種プロパティを用意（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - KABUSYS_ENV、LOG_LEVEL 等のバリデーションを実施。
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 各設定項目の説明、デフォルト、シークレット入力対応、保存の確認までをサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在確認（PyYAML が未インストールなら警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分（スコア合計 0 の場合は自動で等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存保有・当日売却予定を考慮）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金倍率を返す（bull/neutral/bear）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 重み・候補・ポートフォリオ情報から発注株数を決定するアルゴリズムを実装。
      - allocation_method="risk_based"/"equal"/"score" をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケーリング）を実装。
      - cost_buffer を用いた保守的なコスト試算と残差処理ロジックを含む。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ初期化関数 setup_logging を提供。
    - stdout に StreamHandler をセット（cron などでのリダイレクトを想定）。
    - 日次ローテーションの TimedRotatingFileHandler を logs/<app_name>.log に設定（30 日保持）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで続行。
  - utils/process_priority.py:
    - set_process_priority: Windows / POSIX（Linux, macOS 等）での優先度設定を抽象化。
    - set_cpu_affinity: プロセスの CPU affinity を設定（指定なしなら何もしない）。
    - 例外時は警告を出してフェイルセーフ。

- ツール類
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite DB（デフォルト: data/paper_trading.db）から指標を抽出して検証レポートを出力。
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計し PASS/FAIL を判定可能。
    - コマンドライン引数で期間指定 (--from / --to) と DB パス (--db) を指定可能。

- 研究用（初期実装）
  - research/factor_research.py:
    - ファクター計算の設計と定数を定義（Momentum, Value, Volatility, Liquidity）。
    - calc_momentum の骨格を追加（prices_daily を参照する設計）。（実装の一部は未完）

Changed
- 初期リリースのため変更履歴はなし（初回導入）。

Fixed
- 初期リリースのため修正履歴はなし。

Removed
- 初期リリースのため削除履歴はなし。

Deprecated
- なし。

Security
- 環境変数を格納する .env は Git にコミットしないよう注意喚起を追加（config_setup のヘッダ）。

注記 / 既知の問題
- research/factor_research.calc_momentum の実装が途中で終端している（ファイル末尾が切れている）。ファクター計算は完成していないため、本番での使用前に実装完了とテストが必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0 または None）の場合はスキップする設計だが、price 欠損に対するフォールバック（前日終値や取得原価など）は TODO として記載されている。
- process_priority / set_cpu_affinity:
  - 権限不足や未対応プラットフォームでは設定に失敗する可能性があり、その場合は警告を出してスキップする動作にしてある。
- logging_setup:
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソールログのみで継続するが、ファイル出力が得られないことがある。
- validate_config:
  - PyYAML がない環境では config/*.yaml の内容検証をスキップして警告を出す。

参考（主な環境変数とデフォルト）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring デフォルト: 60）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB データベース（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（0/1、デフォルト: 0）

-----