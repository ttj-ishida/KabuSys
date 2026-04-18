# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコード内容から推測して作成した変更履歴です（自動生成ではなく手作業での推測記述です）。

すべてのバージョンは semver 準拠の想定です。

## [Unreleased]

### Added
- なし

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-18

初回リリース想定。プロジェクトのコア機能（設定管理、起動スクリプト、ポートフォリオ構築、リスク調整、発注実行 / 監視ユーティリティ、開発用ツール群、ロギング・プロセス制御ユーティリティ）を実装。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として導入。
  - パッケージ構造と主要モジュールを実装（設定、実行エンジン、監視、ポートフォリオ構築、研究用ファクター計算、ユーティリティ、ツール）。

- 設定関連
  - .env ファイルおよび環境変数から設定を読み込む `kabusys.config.Settings` を実装。
    - 自動ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - 環境変数パースの強化: `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理などに対応。
    - 必須値チェック用 `_require()` を実装し、未設定時に明示的なエラーを投げる。
    - 各種設定プロパティ（`duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, 各種しきい値、`env`/`log_level` 検証等）を提供。
    - `paper_fill_mode` の検証（有効値: instant/partial/never/reject）。

  - 対話式設定ウィザード `kabusys.config_setup` を実装。
    - `.env` の初期作成・更新を対話式で支援（シークレット入力のマスク、デフォルト提示、保存確認）。
    - `--env-file` オプションで保存先を指定可能。

  - 設定検証 CLI `kabusys.validate_config` を実装。
    - 必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DB パスの親ディレクトリ存在チェック・config/*.yaml の存在／パース検証（PyYAML 利用）・本番時のガード（LINE 設定や kill flag の自動クリア）を行う。
    - `--strict` オプションで警告を失敗扱いにできる。

- 起動スクリプト / 実行系
  - 実行エンジン起動スクリプト `kabusys.run_execution` を実装。
    - 起動時にプロセス優先度を設定（`set_process_priority("high")`）。
    - 環境に応じて Paper Trading 用の独立した SQLite（`PAPER_TRADING_SQLITE_PATH` / `paper_sqlite_path`）を使用し、本番 DB と分離。
    - Broker クライアントは `BrokerClientFactory` によって生成され、`paper_trading` 環境では MockBrokerClient の使用を想定。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、`ExecutionEngine` を別スレッドで実行。停止フラグ検出時に Engine を停止してグレースフルに終了する。
    - 起動時に監視用テーブルが存在することを保証するため `init_monitoring_db` を呼び出す。

  - 監視プロセス起動スクリプト `kabusys.run_monitoring` を実装。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値ならフォールバックして警告）。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用する仕様（監視データは本番 DB に記録する想定）。
    - 停止フラグファイルによる終了判定。例外はログ出力して次回ポーリングまで待機。

- ロギング・プロセス制御
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / app_name に基づくログファイル出力、失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - `kabusys.utils.process_priority` を実装。
    - Windows / POSIX（Linux, macOS, FreeBSD）間の差分を吸収してプロセス優先度（nice / Windows priority）を設定。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供。
    - psutil の例外や権限不足に対して安全にフォールバックし警告ログを出す。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - シグナル候補の選択 `select_candidates`（スコア降順、同点時は signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコア 0 の場合に等金額へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap`（既存保有のセクターエクスポージャーに基づき当日新規候補を除外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear にマップ、未知レジームは 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数算出 `calc_position_sizes`（allocation_method: risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合のスケールダウンロジック）を実装。コストバッファ（手数料・スリッページ見積り）を考慮。
    - スケーリング後の fractional 残差に基づく再配分ロジックを実装。

- 研究（Research）
  - `kabusys.research.factor_research` の基礎を実装（モメンタム / MA200 / ATR / 出来高等を計算する方針、DuckDB 接続を受け取り prices_daily/raw_financials を参照）。
    - （ファイルは途中で切れているが、モメンタム計算のための定数と関数スケルトンが存在）

- ツール
  - `kabusys.tools.paper_verification_report` を実装。
    - Paper Trading 用 SQLite から稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計してレポート出力。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を提供。
    - 日付フィルタ（--from / --to）や --db オプションをサポート。

### Changed
- なし（初回リリース）

### Fixed / Robustness improvements
- .env パーサでのクォート、エスケープ、コメント処理を強化し、実運用でありがちな .env 記述のばらつきに耐性を追加。
- ログディレクトリ作成失敗時にファイルハンドラ作成をスキップするフォールバック処理を追加（起動失敗を防止）。
- プロセス優先度設定や CPU affinity の権限エラーを捕捉し、アプリケーションを継続可能にする。

### Removed
- なし

### Known issues / TODOs
- position_sizing.calc_position_sizes:
  - 価格が欠損（0.0）だった場合にエクスポージャーや投資額が過小見積りされる可能性があるため、前日終値や取得原価などでのフォールバック実装を検討中（TODO コメントあり）。
- risk_adjustment.calc_regime_multiplier:
  - 未知レジームは一旦 1.0 にフォールバックする実装。将来的にはレジーム検出ロジックと連携して挙動を見直す余地あり。
- research/factor_research はファイル途中で実装が切れているため、完全なファクター計算機能の追加実装が必要。

---

注: この CHANGELOG は提供されたソースコードを基に手作業で推測して作成したものです。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先してください。必要であれば、実際のコミットメッセージや変更差分に基づくより厳密な CHANGELOG を生成します。