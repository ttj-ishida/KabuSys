# Keep a Changelog — CHANGELOG.md

すべての変更は「Keep a Changelog」仕様に準拠して記載します。  
このファイルはコードベースの内容から推測して作成したリリース履歴です。

全般注意
- 日付はリポジトリ上のファイル内容（スクリプト等に含まれる日付やバージョン）および現在日（2026-04-21）を参考にしています。
- 実装やコメントから推測した仕様、既知の制約や TODO、環境変数の挙動等を記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-21
初回公開リリース。以下の主要機能とユーティリティを含みます。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知してループを終了。
    - 監視用 DB は環境にかかわらず production の `sqlite_path` を使用する実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
    - 起動前に停止フラグ（data/stop_requested.flag）を確認し、既に立っている場合は起動しない。
    - 実行中は別スレッドでエンジンを動かし、停止フラグ検知で安全に停止。

- 設定・環境変数管理
  - config.py
    - .env 自動ロード機構（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能（テスト用）。
    - 必須環境変数チェック用 `_require()`、多くの設定プロパティ（DBパス、API トークン、PID/kill フラグパス、閾値など）を提供。
    - `PAPER_FILL_MODE` の検証（instant/partial/never/reject）。
    - `KABUSYS_ENV`（development/paper_trading/live）の検証。
  - config_setup.py
    - 対話式 .env ウィザードを追加（.env の初期作成・更新支援）。
    - シークレットのマスキング表示、選択肢サポート、保存確認を実装。
  - validate_config.py
    - 設定検証 CLI を追加（.env および config/*.yaml の存在・基本整合性検証）。
    - `--strict` オプションで警告をエラー扱いにできる。
    - PyYAML がない場合は YAML 検証をスキップして警告出力。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全アプリケーションで共通して使えるログ設定関数 `setup_logging()` を追加。
    - stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ（既定: logs/）作成処理と失敗時のフォールバックを実装。
  - utils/process_priority.py
    - プロセス優先度と CPU affinity 設定のユーティリティを追加。
    - Windows と POSIX 系（Linux/Mac/FreeBSD）を抽象化して `set_process_priority()` / `set_cpu_affinity()` を提供。
    - 権限不足など失敗時は警告を出して安全にスキップ。

- ポートフォリオ構築関連モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (`select_candidates`) と配分ウェイト計算（`calc_equal_weights`, `calc_score_weights`）。
    - スコアが全て 0 の場合は等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（`apply_sector_cap`）: 既存保有のセクター比率に応じて当日新規候補を除外するロジック。
    - レジーム乗数（`calc_regime_multiplier`）: bull/neutral/bear に基づく投下資金乗数と未定義レジームのフォールバック。
    - `apply_sector_cap` は "unknown" セクターを除外対象にしない方針。
  - portfolio/position_sizing.py
    - 株数決定アルゴリズム（`calc_position_sizes`）を追加。
    - risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap のスケーリング（scale-down）を実装。
    - コストバッファ（手数料・スリッページ見積り）を考慮した保守的な見積り。
    - aggregate scaling の残差配分（fractional remainder）を lot 単位で行うアルゴリズムを実装。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）等。
    - デフォルト閾値を設定（例: 稼働率 >= 99%、fill_rate >= 90% 等）し、PASS/FAIL 判定を出力。
    - コマンドライン引数 `--from` / `--to` / `--db` をサポート。

- 研究用モジュール（部分実装）
  - research/factor_research.py
    - ファクター計算のための構成と定数、モメンタム計算関数 calc_momentum の雛形を追加（DuckDB 経由で prices_daily を参照する設計）。
    - （ファイルは途中までの実装を含む）

- パッケージメタ
  - パッケージの初期バージョンを `__version__ = "0.1.0"` として定義。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正はなし）

### Known limitations / Notes
- monitoring は意図的に環境にかかわらず production の SQLite を使用する設計（監視データは本番 DB に集約）。
- execution は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB と完全に分離する。
- config の .env 自動読み込みはプロジェクトルート検出に依存する（.git / pyproject.toml）。ルートが特定できない場合は自動ロードをスキップする。
- position_sizing, risk_adjustment 内に価格データ欠損時の挙動に関する TODO が存在（将来的に前日終値や取得原価等をフォールバックすることが検討されている）。
- research/factor_research.py はファクター計算ロジックの雛形を含むが、完全実装が見られない（ファイル末尾が途中で終わっている可能性あり）。
- process_priority, set_cpu_affinity は OS 権限・psutil のサポート状況により失敗することがあり、その場合は警告を出して処理をスキップする。
- logging_setup はログディレクトリの作成に失敗した場合、ファイルログを無効化して stdout のみで継続する設計。

### TODO（コードコメントに基づく将来タスク）
- price の欠損時のフォールバック戦略（前日終値や取得原価など）を position_sizing/risk_adjustment に実装する。
- research/factor_research の各ファクター計算の完全実装を完了する（Momentum, Value, Volatility, Liquidity）。
- 戦略・リスク・実行設定の YAML を生成するスクリプト（scripts/generate_config.py）や CI での検証を整備する。
- 更なる単体テスト、エンドツーエンドテスト、及び CLI のユーザビリティ改善。

---

（この CHANGELOG はコード内容から推測して作成したため、実際の履歴や意図とは異なる可能性があります。必要に応じて実際のコミットログやプロジェクト管理ツールの履歴に基づいて調整してください。）