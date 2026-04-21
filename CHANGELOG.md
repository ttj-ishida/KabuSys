CHANGELOG
=========

フォーマット: Keep a Changelog 準拠  
本ファイルはリポジトリのコードベースから推測して自動生成されています。実際のリリースノートは開発者が調整してください。

Unreleased
----------

- なし

[0.1.0] - 2026-04-21
--------------------

Added
- 全体
  - 初期公開リリース。本リリースで基本的な自動売買・検証・運用ユーティリティ群を提供。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 環境設定 / 設定管理
  - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml から探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - 高機能な .env パーサーを実装。export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、無効行スキップなどに対応。
  - Settings クラスを追加し、環境変数経由で設定値を一元取得可能（DBパス、APIトークン、Paper Trading の挙動、監視閾値など）。
  - PAPER_FILL_MODE 等の値検証（有効値チェック）を実装。

- 設定支援 / 検証ツール
  - 対話式設定ウィザード CLI を追加（kabusys.config_setup）。.env の新規作成・更新を支援。
  - 設定検証 CLI を追加（kabusys.validate_config）。必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL の妥当性、DBパスや config/*.yaml の存在と YAML パースチェック（PyYAML があれば中身も検証）、本番環境向けガードチェック等を実施。--strict オプションで警告をエラー扱いにできる。

- 実行 / 起動スクリプト
  - ExecutionEngine 起動スクリプトを追加（run_execution.py）。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用しブローカークライアントを作成。OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動する仕組みを提供。
    - 停止フラグ（data/stop_requested.flag）検知で安全にシャットダウン。PID ファイル管理（data/execution.pid）をサポート。
  - SystemMonitor 起動スクリプトを追加（run_monitoring.py）。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告ログを出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データを本番 DB に記録）。
    - duckdb と sqlite3 両方の接続を初期化して SystemMonitor に渡す。
    - 停止フラグ検知や KeyboardInterrupt による正常終了処理を実装。

- ロギング / 運用ユーティリティ
  - 統一的なログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name による設定をサポート。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで動作。
  - プロセス優先度および CPU アフィニティ設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows/Linux/macOS 等で動作する抽象化を提供。優先度 "high"/"normal"/"low" を受け付け、psutil ベースで nice/priority を設定。アクセス権限エラー等は警告でスキップ。
    - set_cpu_affinity によりプロセスを先頭 N コアに固定可能（未指定なら変更しない）。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重を実装。全スコア 0 の場合は等分配にフォールバックして警告。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有のセクター別時価を計算し、1セクター上限（max_sector_pct）を超えるセクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: market レジーム (bull/neutral/bear) に応じた資金乗数を返す（未知レジームは 1.0 でフォールバック）。
    - セクター露出算出時の価格欠損に関する TODO コメントを追加（将来的なフォールバック価格の検討）。
  - 株数決定・リスク制限・単元丸め（kabusys.portfolio.position_sizing）
    - calc_position_sizes: risk_based / equal / score の allocation_method をサポート。lot_size（単元）で丸め、max_position_pct／max_utilization による per-position および aggregate の上限管理、available_cash に基づくスケーリング（端数処理で残差分を分配）を実装。
    - cost_buffer による保守的コスト見積りをサポート。
    - 将来的拡張のための TODO（銘柄別 lot_size 管理）を記載。

- 研究用モジュール
  - ファクター計算フレームワーク（kabusys.research.factor_research）を追加。
    - モメンタム、MA200、ATR、流動性等の計算方針と定数を定義。DuckDB を使った prices_daily / raw_financials 参照を前提とする設計。
    - （注意）一部実装が途中（ファイル末尾が切れているため未完）であり、今後の実装継続を予定。

- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - PAPER_TRADING_SQLITE_PATH（または --db オプション）から SQLite を読み、期間指定で各種指標（稼働率、注文成功率、送信率、リスク却下、レイテンシ(P95) 等）を算出してレポート出力。
    - Pass/Fail 判定基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）を備える。
    - DB テーブルが存在しない場合の例外（OperationalError）をハンドリングして適切に N/A を出力する。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Known issues / Notes
- research.factor_research はファイル末尾で実装が途切れているため、実用には追加実装が必要。
- position_sizing / risk_adjustment の一部で価格欠損時のフォールバック（前日終値や取得原価など）未実装（TODO）。短期的には価格が欠損すると銘柄がスキップされ、想定より保有数が少なくなる可能性あり。
- run_monitoring は監視 DB に本番 sqlite_path を常に使用する仕様。検証時は運用側で注意が必要。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗する可能性があり、その場合はログで警告され設定をスキップする。
- .env 自動ロードポリシーはプロジェクトルート検出に依存するため、パッケージ配布後や特殊な配置では自動ロードが行われない可能性あり（その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で制御可能）。

Breaking Changes
- なし（初期リリース）

セキュリティ
- なし（初期リリース）。環境変数やシークレット（API トークン等）は .env を利用する設計。.env の絶対に Git にコミットしない旨を config_setup に明記。

以上