# Changelog

すべての注目すべき変更点をこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- バージョン見出しは YYYY-MM-DD 形式の日付を含みます。
- 各見出しの下に Added / Changed / Fixed / Deprecated / Removed / Security 等のセクションを設けます。

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを設定: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知してループ終了。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用して起動する挙動を明示。
    - duckdb 接続、および監視用 DB 初期化（`init_monitoring_db`）を実行。
    - 例外発生時にログを出力して次のポーリングまで継続するフェールセーフを実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を利用し、paper_trading 用 SQLite DB（`data/paper_trading.db`）を使用して本番 DB と分離。
    - Engine は別スレッドで実行し、停止フラグを検知すると安全に停止させる仕組みを追加。
    - PID ファイル（data/execution.pid）管理をサポート。

- 設定管理 / CLI
  - config.py
    - 環境設定管理クラス `Settings` を追加。環境変数をプロパティ経由で取得し、必須チェック・値検証を行う。
    - .env 自動ロード: プロジェクトルート（.git または pyproject.toml）を検出して `.env` / `.env.local` を自動で読み込む機能を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env パースの堅牢化（export プレフィックス対応、クォート処理、インラインコメント対応など）。
    - Paper Trading 向け設定（`paper_fill_mode`、`paper_sqlite_path`）や監視閾値、PID / Kill flag 周りの設定プロパティを提供。
  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。テンプレート出力・既存値の再利用・シークレットマスク表示・最終確認の流れを実装。
    - 書き込み用 `_write_env` により安全な雛形を出力。
  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパースを検証。
    - `--strict` オプションで警告も失敗扱いにできる。
    - PyYAML の未インストール検出時には YAML 検証をスキップして警告を出す。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - アプリ共通のロギング初期化ユーティリティ `setup_logging` を追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30 日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続する安全性を実装。
  - utils/process_priority.py
    - プロセス優先度と CPU affinity を簡単に設定するユーティリティを追加。
    - Windows と POSIX (Linux, Darwin, FreeBSD) を抽象化し、`set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。
    - 権限不足や未対応環境では警告ログを出して安全にスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定 (`select_candidates`) と配分重み生成 (`calc_equal_weights`, `calc_score_weights`) を純粋関数として実装。スコア全 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (`apply_sector_cap`) を実装。既存保有のセクター別エクスポージャーを計算し、閾値超過セクターの候補を除外（"unknown" セクターは適用除外）。
    - レジームに応じた投下資金乗数 (`calc_regime_multiplier`) を実装（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 単元株丸め・リスクベース / 等配分 / スコアベースの発注株数算出関数 `calc_position_sizes` を実装。
    - per-position 上限、aggregate cap、lot_size 単位でのスケーリング、cost_buffer の取り扱い、残差配分ロジックを実装。

- ツール / レポート
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均 / 最大 / P95）を計算して PASS/FAIL を判定するレポートを出力。
    - P95 計算、日付フィルタ、DB パス解決（CLI `--db` / 環境変数）をサポート。複数の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。

- リサーチ（開始実装）
  - research/factor_research.py
    - ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity 設計方針をコメントで定義）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照して計算する設計。モメンタム計算関数（calc_momentum）の実装着手（ファイルの後半で実装継続予定）。

- パッケージエクスポート
  - portfolio パッケージの __init__ にて主要関数を公開。

### Changed
- （初期リリースのため該当なし）初版のため破壊的変更はなし。

### Fixed
- （初期リリースのため該当なし）既知のバグ修正は今後のリリースで記録予定。

### Notes / 実装上の重要ポイント
- run_monitoring は意図的に KABUSYS_ENV に関係なく本番用 `sqlite_path` を使う設計になっている点に注意（監視データは一元管理する想定）。
- .env 自動読み込みはプロジェクトルート検出に基づくため、配布後や CWD が変わる場合でも一貫して動作するよう工夫。
- process_priority / CPU affinity の設定は権限や OS によって失敗する可能性があり、その場合は警告を出して処理を継続する安全設計を採用。
- position_sizing の aggregate スケーリングは lot_size 単位で再配分を行うため、単元サイズ（例: 100 株）に依存した丸めが発生する。
- Paper Trading と本番の DB を明確に分離しているため、ペーパートレードの検証を本番データに影響させない設計。

---

今後の予定（例）
- factor_research の続き（モメンタム / ATR / Value ファクターの完成）
- ExecutionEngine / Broker インターフェースの詳細なユニットテスト追加
- ロギング・監視機能のメトリクス拡張（Prometheus など）
- config の型安全化（pydantic 等の導入検討）

以上。