# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
次のバージョン方針に従います: Unreleased → リリース履歴（逆時系列）。

## [Unreleased]

### Added
- いくつかの TODO / 改善候補を記載：
  - position_sizing の将来的な拡張: 銘柄別の lot_size（単元）を導入する案がコメントに残っています。
  - risk_adjustment の価格欠損時のフォールバック（前日終値や取得原価）に関する改善提案。
  - research.factor_research の実装途中（ファイル末尾が未完）に関する継続実装。

### Changed
- なし（初期リリース以降の変更は今後ここに追加）

### Fixed
- なし（初期リリース以降の修正は今後ここに追加）

---

## [0.1.0] - 2026-04-25

初期リリース。以下の主要コンポーネントを含みます。

### Added
- 基本情報
  - パッケージバージョン: `0.1.0`
  - パッケージ説明: "KabuSys - 日本株自動売買システム"

- 設定管理
  - Settings クラス（`kabusys.config`）を導入。環境変数から各種設定を取得する統一インターフェースを提供。
  - .env 自動読み込み機能（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` の行パースはシングル/ダブルクォートやエスケープ、`export KEY=val` 形式、コメント処理などに対応。
  - 必須環境変数チェック `_require()` による起動時の明示的エラー。

- 設定支援ツール
  - 環境設定ウィザード CLI (`kabusys.config_setup`)：対話式で `.env` の初期作成・更新を支援。
  - 設定検証 CLI (`kabusys.validate_config`)：必須環境変数、KABUSYS_ENV、ログレベル、DB パス、`config/*.yaml` の存在と YAML パース（PyYAML の有無に応じてスキップ）を検査。`--strict` オプションで警告をエラー扱いに可能。

- 実行 / 監視ランナー
  - 実行エントリ `run_execution.py`：
    - プロセス優先度を最初に "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（環境に応じて MockBrokerClient を利用）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立て、別スレッドで `ExecutionEngine.run_session()` を起動。PID ファイルと停止フラグ（`data/stop_requested.flag`）により安全に停止可能。
    - RiskManager 初期設定値（`RiskConfig`）はデフォルトで設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 など）。

  - 監視エントリ `run_monitoring.py`：
    - SystemMonitor の初期化とポーリングループ実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - 監視は常に本番用の sqlite_path を使用（環境に関わらず監視 DB を共有）。
    - 停止フラグファイルを検知してループを終了。例外発生はログに記録して次のポーリングで継続。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で上位 N を選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額/スコア加重の重み計算（スコア合計が 0 の場合は等金額にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクターごとの既存保有比率が閾値（max_sector_pct）を超える場合に新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバックし警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数を算出（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based: 許容リスク率や損切り率を用いる。
    - equal/score: 重みを使った配分。lot_size（単元）で丸め、1 銘柄上限（max_position_pct）を考慮。
    - aggregate cap: 全銘柄合計が利用可能現金を超える場合にスケールダウンし、余剰現金で端数の lot 単位を残差順に再配分するアルゴリズムを実装。
    - cost_buffer による保守的コスト見積り（スリッページ・手数料想定）をサポート。
    - TODO コメントで将来的な銘柄別 lot_size 化や価格フォールバックの示唆あり。

- ユーティリティ
  - utils.logging_setup:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代保持）を設定するユーティリティ。
    - 既存ハンドラの重複設定を防ぐためクリアしてから再設定。
    - ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - ログレベルは引数 > 環境変数 `LOG_LEVEL` > デフォルト の順で解決。
    - 出力は stdout を使用（cron 等で stdout/stderr の一本化運用を想定）。
  - utils.process_priority:
    - psutil を用いて Windows（HIGH_PRIORITY_CLASS 等）および POSIX 系（nice 値）両対応でプロセス優先度を設定。
    - CPU affinity を最初 N コアに固定する機能（利用可能なコア数を超える指定は全コア使用で安全に処理）。
    - 権限不足や未対応 OS の場合は警告ログを出してフォールバック。

- 監視 / DB 初期化
  - monitoring.monitoring_db:init_monitoring_db により監視用テーブルの冪等な初期化を実行。

- Paper Trading / 検証ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite (`PAPER_TRADING_SQLITE_PATH` デフォルト `data/paper_trading.db`) からレポートを生成。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - P95 計算、閾値に基づく PASS/FAIL 判定を実装（デフォルト基準値をスクリプト内で定義）。
    - コマンドラインで期間指定（--from / --to）や DB パス指定（--db）が可能。

- research
  - research.factor_research: ファクター計算モジュールの骨子を実装（Momentum, Value, Volatility, Liquidity を想定）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計。実装は一部（ファイル末尾）未完。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Removed
- なし

### Security
- 重要な API トークン / パスワードは .env に格納する想定。`.env` を絶対に Git にコミットしないよう setup ウィザードのヘッダに注記。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD が必須です。未設定時は `validate_config` で検出できます。
- 実行環境切替:
  - `KABUSYS_ENV` が `paper_trading` の場合、Execution は paper_trading 専用 DB を使用して本番 DB と分離されます。
- Kill Switch / Stop フラグ:
  - `data/stop_requested.flag` を作成することで監視・実行プロセスに停止を通知できます。PID ファイル・停止フラグの利用により外部プロセスからの安全な停止が可能です。
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリ作成に失敗した場合はコンソールのみで動作します。

---

開発中の機能（未実装 / 改善予定）
- factor_research の完全実装（ファクター計算ロジックの続き）。
- price 欠損時のフォールバックロジック（risk_adjustment / position_sizing）。
- 銘柄ごとの単元（lot_size）を考慮した position_sizing の拡張。
- 追加のユニットテスト、E2E テストの整備。

---

参考:
- この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴・コミットログと差異がある可能性があります。