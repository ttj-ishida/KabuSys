# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
重大な変更のみコード内容から推測して要約しています。

## [Unreleased]

- なし（現時点のリポジトリはバージョン 0.1.0 としてまとめられています）

## [0.1.0] - 初期リリース
リリース日: 未指定

### Added
- 基本パッケージ構成を追加
  - パッケージ名: `kabusys`。__version__ を "0.1.0" に設定。
  - サブパッケージ: data, strategy, execution, monitoring（エクスポート定義あり）。

- 起動スクリプト / デーモン機能
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) による優雅な終了検知。
    - 監視用 SQLite は実行環境に関わらず本番用 sqlite_path を使用する実装。
    - duckdb 接続、監視 DB 初期化、例外時のログ出力と次ポーリング待ちの扱いを実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離する設計（コメントに MockBrokerClient の使用を明記）。
    - 停止フラグにより起動を抑止、別スレッドでエンジンを実行し停止フラグ検知で Engine.stop() 実行。
    - PID ファイルの扱い、duckdb 接続、監視テーブルの冪等な初期化を行う。

- 設定管理
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出して .env / .env.local を読み込む）。
    - .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースの堅牢化: export プレフィックス、クォート値（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント処理などに対応。
    - Settings クラスで各種設定（DB パス、LINE, kabu, J-Quants トークン、閾値、環境種別、ログレベルなど）をプロパティ経由で取得する仕組みを提供。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証など入力値チェックを実装。

- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - デフォルト値、選択肢、シークレット入力扱い、既存 .env のマージをサポート。
    - 最終的に .env を安全に書き出す機能を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス親ディレクトリ存在確認、config/*.yaml の存在と YAML パース（PyYAML がインストールされている場合）をチェック。
    - --strict オプションで警告を FAIL 扱いにできる。

- ログ設定ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーの初期化ユーティリティを提供。stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）を設定。
    - ログレベル解決順（関数引数 > LOG_LEVEL 環境変数 > デフォルト）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
    - 既存ハンドラのクリーンアップ処理を行う。

- プロセス制御ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice 値）を提供。
    - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を追加。
    - 権限不足や未対応 OS に対する安全なフォールバックとログ出力。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナルから候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコアがすべて 0 の場合は等分配にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）: 既存保有のセクター別時価を算出して閾値超過セクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py:
    - 発注株数算出ロジックを実装 (allocation_method: "risk_based" / "equal" / "score")。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer による保守的見積り、残差処理によるロット単位での追加配分などをサポート。

- リサーチ / ファクター計算（初期実装）
  - research/factor_research.py:
    - Momentum / Value / Volatility / Liquidity の計算方針と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計方針を明記。
    - モメンタム計算関数の枠組みを導入（calc_momentum 等、実装の続きあり）。

- Paper Trading 関連ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）から集計を行い、稼働率・注文成功率・送信率・レイテンシ等の指標を算出してレポート出力。
    - P95 計算、日付フィルタ、閾値判定（稼働率 99%、成立率 90% 等）を実装。FAIL 判定理由を列挙して出力。

- その他
  - monitoring.monitoring_db の初期化呼び出しを複数箇所で行い、監視テーブルの存在を保証（冪等）。
  - duckdb, sqlite の接続・クローズの堅牢化（finally ブロックでのクローズ）。

### Changed
- なし（初期リリースに相当する大規模追加が中心）

### Fixed
- なし（コード内に記載される小さな例外ハンドリング・フォールバックは実装として含む）

### Removed
- なし

### Security
- 環境情報 (.env) の取り扱いに注意を促すドキュメントヘッダー（config_setup にて .env を Git にコミットしない旨を明記）。

---

注意:
- 本 CHANGELOG は、提供されたコードベースの内容から機能追加点や設計上の重要事項を推測して作成したものです。実際のコミット履歴やリリースノートとは差異がある可能性があります。実際の変更履歴を反映するには git の履歴（commit メッセージ）を参照してください。