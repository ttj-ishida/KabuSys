# Changelog

すべての重要な変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。  
リリース日はコードから推測した日付（この CHANGELOG 作成日時）を使用しています。

全般的な注記:
- このリポジトリは日本株自動売買システム「KabuSys」の初期実装と見られる機能群を含みます。
- 環境変数・デフォルト値・CLI ツール・内部ユーティリティ・ポートフォリオ構成ロジック・モニタリング/実行エントリポイントなどが含まれます。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-23

### Added
- 基本バージョン情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 設定管理
  - 環境変数/`.env` の自動読み込み機能（プロジェクトルートに基づく）。
  - Settings クラスを提供し、主要設定（J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視しきい値等）をプロパティ経由で取得可能に。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

- .env 作成ウィザード
  - 対話式 CLI: `kabusys.config_setup`（python -m kabusys.config_setup）を追加。
  - 各種項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話的に作成/更新可能。
  - シークレット項目はマスク表示。`.env` 書き込みテンプレートを生成。

- 設定検証 CLI
  - `kabusys.validate_config`（python -m kabusys.validate_config）を追加。
  - 必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML があればパース検証を実行）などを実施。
  - --strict オプションで警告を FAIL 扱いにできる。

- 実行/監視エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプト。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。RiskManager / OrderManager / Reconciler 等のコンポーネントを組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）を検出したら安全に停止。
    - 実行時に execution.pid ファイルを扱う（pid_file のパス設定）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックして警告を出力。
    - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。

- 監視 DB 初期化
  - init_monitoring_db を実行して監視用テーブルの存在を保証（冪等）。

- ログ設定ユーティリティ
  - setup_logging() を追加。コンソール出力（stdout）と日次ローテーションファイル出力（logs/<app>.log、30日保持）をルートロガーに設定。
  - LOG_DIR / LOG_LEVEL の解決順とフォールバック動作、ファイルハンドラ作成失敗時のフォールバック（コンソールのみ）を実装。

- プロセス優先度 / CPU affinity ユーティリティ
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供（psutil ベース、Windows/Linux/macOS を吸収）。
  - 標準的な優先度レベル: "high", "normal", "low"。未対応 OS や権限不足時には警告を出力してスキップ。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio_builder
    - select_candidates(buy_signals, max_positions): score 降順、同点は signal_rank 昇順で上位 N を選定。
    - calc_equal_weights(candidates): 等金額配分を返す。
    - calc_score_weights(candidates): スコア加重配分を返す。全スコアが 0 の場合は等金額配分にフォールバック（警告）。
  - risk_adjustment
    - apply_sector_cap(...): セクター集中上限（max_sector_pct）を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier(regime): レジームに応じた資金乗数を返す（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 にフォールバック（警告）。
  - position_sizing
    - calc_position_sizes(...): allocation_method（"risk_based"/"equal"/"score"）に基づき発注株数を計算。単元株丸め（lot_size）、1銘柄上限（max_position_pct）、利用資金上限（max_utilization）、cost_buffer を考慮した aggregate cap のスケーリングロジックを実装。空価格や非正の価格をチェックしてスキップする挙動。

- Paper Trading 検証ツール
  - tools.paper_verification_report
    - SQLite（デフォルト: data/paper_trading.db）を参照して Paper Trading の検証レポートを生成（システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ指標（平均/最大/P95）等）。
    - 基準値（例: 稼働率 >= 99%、注文成功率 >= 90% など）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションに対応。

- research/factor_research の骨格
  - DuckDB 接続を受け取り prices_daily/raw_financials を参照してモメンタム/Value/Volatility/Liquidity 等のファクターを計算する設計（実装途中の箇所あり）。

- パッケージエクスポート
  - kabusys.portfolio モジュールに主要関数をエクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Notes / 実装上の注意
- Settings.paper_fill_mode の有効値は "instant" | "partial" | "never" | "reject"。不正値は ValueError を送出する。
- run_monitoring は監視用 DB に常に Settings.sqlite_path を使う点に注意（環境に依存しない）。
- run_execution は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH を使い本番 DB と完全分離する設計。
- process_priority / CPU affinity の設定は権限やプラットフォームに依存し、失敗時はログに警告を残して処理を続行する。
- logging_setup はログディレクトリ作成に失敗した場合、ファイルハンドラをスキップしてコンソール出力のみで継続する。
- portfolio/position_sizing のスケーリング・端数処理は単元株（lot_size）単位で行われる。将来的に銘柄別 lot_size を導入する余地あり（TODO コメントあり）。
- research/factor_research はファイル末尾で実装途中（切れている）箇所があるため、本格運用前の実装完了とテストが必要。

---

（この CHANGELOG は提供されたソースコードの内容から推測して作成しました。実際の変更履歴やリリース日・追加・修正内容はプロジェクトのコミット履歴やリリースノートを参照してください。）