# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 変更は意味のある粒度で記載しています（機能追加 / 変更 / 修正 等）。
- 日付はリリース日（想定）です。コードから推測して作成しています。

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初期リリース。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - Settings クラス（kabusys.config）を追加。環境変数を安全に読み込み、各種設定（J-Quants / kabuAPI / DBパス / Paper Trading 関連 / 監視閾値 / ログレベル / 実行環境フラグ等）をプロパティとして提供。
  - 自動 .env 読み込み機能を追加（プロジェクトルートの `.env` と `.env.local` を OS 環境変数を保護しつつ読み込む）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
  - .env ファイルのパーサーは引用符・エスケープ・コメント・`export KEY=val` 形式に対応。

- 設定ウィザード / 検証 CLI
  - 対話式 .env 作成ツール（kabusys.config_setup）を追加。
    - `python -m kabusys.config_setup` で実行可能。既存 .env を読み込み、秘密値はマスク表示して対話的に編集・保存できる。
    - デフォルト値・選択肢・説明を持つ項目群を提供（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
  - 設定検証ツール（kabusys.validate_config）を追加。
    - `python -m kabusys.validate_config` で必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml の存在・パース（PyYAML があればパース検証）等をチェック。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行・監視スクリプト
  - Execution 起動スクリプト（kabusys.run_execution）を追加。
    - 起動時にプロセス優先度を "high" に設定する（utils.process_priority を使用）。
    - 実行環境が `paper_trading` の場合は MockBrokerClient を利用し、Paper Trading 用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - duckdb 接続を確立して分析用 DB を利用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動（別スレッド）を実装。停止フラグ（data/stop_requested.flag）検知で安全に停止する。
    - RiskManager に対するデフォルト RiskConfig を提供（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期資金は broker.get_available_cash() を参照。
  - Monitoring 起動スクリプト（kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - Monitoring は KABUSYS_ENV にかかわらず常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視データを書き込む仕様。
    - 起動時にプロセス優先度を "high" に設定。停止フラグ（data/stop_requested.flag）でループを終了。

- ロギング・プロセスユーティリティ
  - 統一ロギング設定ユーティリティ（kabusys.utils.logging_setup）を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ログディレクトリ内、日次ローテーション、30日保持）を設定。
    - LOG_DIR / LOG_LEVEL 環境変数や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する安全性を実装。
  - プロセス優先度設定ユーティリティ（kabusys.utils.process_priority）を追加。
    - Windows / POSIX (Linux/macOS/FreeBSD) の差分を吸収して優先度（high/normal/low）を設定。psutil を利用し、アクセス拒否等は警告でスキップ。
    - CPU affinity を設定する set_cpu_affinity() を提供（指定コア数にプロセスを固定、未対応環境は警告）。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights。全スコア0のときは等配分にフォールバックして警告）。
  - risk_adjustment: セクター集中制限（apply_sector_cap。既存保有を考慮して同一セクターの新規候補を除外、"unknown" セクターは除外対象外）、市場レジームに応じた乗数（calc_regime_multiplier。未知レジームは1.0でフォールバックして警告）。
  - position_sizing: 発注株数算出（calc_position_sizes）。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）考慮、stop_loss_pct に基づくリスクベース算出、1銘柄上限・全体利用上限（max_utilization）・コストバッファ（cost_buffer）を考慮した aggregate cap スケーリングを実装。
    - スケーリング時は小数端数を lot 単位で切り捨て、残余資金で fractional 残差の大きい順に追加配分する再現性を確保。

- 分析 / ツール
  - Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）を追加。
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）等を集計し、閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）で PASS/FAIL を判定してレポートを出力。
    - P95 計算ロジック、日付フィルタ（--from / --to）、DB パス上書き（--db / 環境変数）に対応。

- 研究用モジュール（着手）
  - research.factor_research モジュールを追加（ファクター計算群の骨格）。
    - モメンタム（1M/3M/6M）や MA200 乖離、ATR、出来高関連等の設計方針と定数を記載。DuckDB 接続を受けて prices_daily/raw_financials を参照する計算方針を導入（実装は一部）。

### Changed
- 監視設計
  - run_monitoring が監視用 DB として常に Settings.sqlite_path（本番用パス）を使用することを明記（環境に依存しない監視データの一元化を意図）。

### Fixed
- ロバスト性向上
  - logging_setup: ログディレクトリ作成やファイルハンドラ生成に失敗した場合でも、コンソール出力のみで継続するよう例外処理と警告出力を追加。
  - config の .env 読み込み: ファイル読み込み失敗時に警告を出し、プロセスを継続するよう安全化。
  - process_priority: 対応 OS が不明な場合や権限不足で失敗した際に警告でスキップするようにして、挙動が硬直しないように実装。

### Notes
- 多くのモジュールは「DB 参照なしの純粋関数」設計（portfolio 等）でテスタビリティを重視している。
- 実行スクリプトは stop フラグ（data/stop_requested.flag）と pid ファイルを用いた簡易的なプロセス制御を想定している。
- Paper Trading は本番 DB から完全に分離される設計（別 SQLite ファイル）。これによりペーパートレードによるデータ汚染を防止。
- 一部モジュール（例: research.factor_research）は実装途中の箇所が見受けられる（コード末尾が途切れている）。今後の追加実装が想定される。

## 参考: 既知の環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔)
- PAPER_FILL_MODE (paper_trading の fill モード: instant|partial|never|reject)

---

（本 CHANGELOG はコードベースの内容から推測して作成しています。細部の動作や設計意図は実際の仕様や作者の意図に基づき変わる可能性があります。）