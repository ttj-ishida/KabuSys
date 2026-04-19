# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在のパッケージバージョン: `0.1.0`

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初期リリース。KabuSys のコア CLI、ランタイム起動スクリプト、ポートフォリオ構築・リスク制御・ポジションサイジングロジック、ユーティリティ群、および Paper Trading 検証ツールを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境設定・管理
  - Settings クラスを実装し、環境変数経由で各種設定を取得（J-Quants / kabuAPI / DB パス / ログ / 監視閾値 等）。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - .env ファイルの堅牢なパーサ実装（コメント、export プレフィックス、引用符とバックスラッシュエスケープ対応）。
  - 環境変数の保護機能（既存 OS 環境変数を上書きしない / protected 指定）。

- 対話式設定ウィザード
  - `kabusys.config_setup` により `.env` を対話式で作成・更新する CLI を追加。
  - シークレット項目のマスク表示、選択肢表示、既存値の再利用、ファイル書き込みテンプレートを提供。

- 設定検証ツール
  - `kabusys.validate_config` CLI を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在と簡易パース（PyYAML 利用時）を検査。
  - `--strict` オプションで警告も失敗として扱う機能を提供。

- 起動スクリプト（ランタイム）
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用して paper_trading 用の専用 SQLite（`data/paper_trading.db` デフォルト）に記録し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と PID 管理をサポート。
    - スレッド起動・停止の安全な管理。
    - RiskManager, OrderManager, Reconciler の組み立てとデフォルトリスク設定値を用意（max_position_pct, max_utilization, circuit breaker 等）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境にかかわらず監視は本番用 sqlite_path を使用（監視 DB を環境依存に分離せず一貫して運用）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 停止フラグ検知によるループ終了、KeyboardInterrupt のハンドリング。

- Portfolio（ポートフォリオ構築）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選別ロジックを追加（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算を実装。全スコアが 0 の場合は等金額へフォールバック（警告出力）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を防ぐため既存保有を参照して新規候補を除外するロジックを追加（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知のレジームは警告後 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した株数決定ルーチンを実装。
    - lot_size（丸め）対応、per-stock 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）考慮、端数補正ロジック（fractional remainder に基づく追加配分）を実装。
    - allocation_method による分岐と現在保有との差分計算。

- 解析・研究関連
  - research.factor_research: DuckDB 接続を受けてモメンタム等のファクター計算を行うモジュールの骨組みを追加（prices_daily / raw_financials を参照する設計）。（一部実装は継続中）

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出してレポート出力。
    - P95 計算、閾値判定（デフォルト値: 稼働率99%、成功率90%、送信率95%、P95 ≤ 200ms）を実装。
    - DB が存在しない、またはテーブルが欠けている場合は耐障害性を持って N/A 等で出力。

- ユーティリティ
  - utils.logging_setup:
    - stdout StreamHandler と TimedRotatingFileHandler（ログ日次ローテーション、30日保持）をルートロガーに設定する統一ユーティリティを追加。
    - LOG_DIR/LOG_LEVEL の解決順を明確化。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続する。
  - utils.process_priority:
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加（Windows と POSIX を吸収）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
    - 許可エラーや未対応 OS 時は警告を出して安全にフォールバック。

- DB / クエリ関連
  - DuckDB 接続を利用する設計を導入（duckdb_path の設定）。
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を起動時に呼び出し、監視テーブルの存在を保証（冪等）。

### Changed
- （初回リリースにつき履歴なし）

### Fixed
- （初回リリースにつき履歴なし）

### Security
- シークレット値（トークン・パスワード）は config_setup の表示でマスクするなど漏洩に配慮した出力を採用。

### Notes / Known issues / TODO
- research.factor_research の一部（モメンタム計算等）は実装継続中。ファイル末尾が未完の状態のため追加実装が必要。
- position_sizing:
  - lot_size は現在グローバル共通（デフォルト 100）。将来的に銘柄ごとの単元サイズをサポートする予定（TODO コメントあり）。
  - open_prices に欠損（0.0）がある場合のフォールバック価格処理は未実装。将来の拡張で前日終値や取得原価などを使う検討。
- apply_sector_cap は "unknown" セクターを上限チェックの対象外としている（意図的）。データ整備状況により振る舞いが変わる点に注意。
- プロセス優先度・CPU affinity の設定は権限不足や OS によって失敗する可能性があるため、失敗時は警告が出て処理を継続する設計。

---

この CHANGELOG はコードベースから機能・挙動を推測して作成しています。実際のリリースノート作成時には、コミット履歴やリリース担当者の確認を推奨します。