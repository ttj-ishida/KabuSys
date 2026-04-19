# CHANGELOG

すべての重要な変更をこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

※内容は提供されたコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション初期実装を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
- 起動用スクリプトを追加。
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 `data/stop_requested.flag` によるフラグ検知で行う。監視は環境にかかわらず本番用の sqlite_path を使用する仕様。
  - `run_execution.py`：ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合はペーパートレード用 MockBroker を使用し、専用の SQLite（`data/paper_trading.db`）に記録する。停止フラグ・PID 管理・スレッド制御を実装。
- 設定管理・ウィザード・検証 CLI を追加。
  - `config.py`：環境変数ラッパー `Settings` を提供。`.env` 自動読み込み機能（プロジェクトルート検出）を実装。複数のプロパティ（DB パス、PID / kill flag パス、閾値、env / log-level 判定、PAPER_FILL_MODE の検証など）を提供。
  - `config_setup.py`：対話式 .env 作成/更新ウィザードを実装（シークレット入力、選択肢、既存値の再利用、保存確認）。
  - `validate_config.py`：起動前チェックツールを実装。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML のパース（PyYAML があれば実行）や本番環境向けガードチェックを行う。`--strict` オプションあり。
- ロギング・プロセス制御ユーティリティを追加。
  - `utils/logging_setup.py`：統一ロギング設定。コンソール（stdout）ハンドラと日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして安全にフォールバック。
  - `utils/process_priority.py`：Windows / POSIX を吸収したプロセス優先度設定（`set_process_priority`）と CPU affinity 設定（`set_cpu_affinity`）を実装。権限不足時や未対応 OS では警告を出しスキップする。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）。
  - `portfolio/portfolio_builder.py`：候補選定（スコア/ランクでソート）、等分配・スコア加重配分を実装。スコア合計が 0 の場合は等分配にフォールバック。
  - `portfolio/risk_adjustment.py`：セクター集中制限（apply_sector_cap）および市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。未知レジームは警告して 1.0 にフォールバック。`apply_sector_cap` は既存保有のセクター別エクスポージャを計算し上限超過セクターの新規候補を除外する。
  - `portfolio/position_sizing.py`：複数の割当方式（risk_based / equal / score）に対応した株数決定ロジックを提供。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金でスケールダウン）、cost_buffer（手数料/スリッページ見積り）による保守的見積り、残差に基づく追加配分などを実装。
  - `portfolio/__init__.py` でモジュールを公開。
- ペーパートレード検証ツールを追加。
  - `tools/paper_verification_report.py`：ペーパートレード用 SQLite (`PAPER_TRADING_SQLITE_PATH` / default `data/paper_trading.db`) からデータを集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出してレポートを標準出力に出力。閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を用いた PASS/FAIL 判定を行う。日付範囲フィルタ `--from` / `--to`、`--db` オプション対応。
- 監視用 DB 初期化ユーティリティを導入（monitoring_db から初期化呼び出しをするコードを各スクリプトが利用）。
- 研究用ファクターモジュールの骨組みを追加。
  - `research/factor_research.py`：Momentum / Value / Volatility / Liquidity 等の計算方針と定数、`calc_momentum` の実装開始（prices_daily / raw_financials を参照する想定）。（注: 提供コードは途中まで）

### Changed
- 環境変数読み込みの挙動整理。
  - 読み込み優先順位を OS 環境変数 > .env.local > .env とし、OS の既存キーは保護して上書きされないように実装。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途など）。
  - .env パースの堅牢化：`export KEY=val`、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いなどに対応。
- ログ出力は stdout を用いるように明示（cron 等の運用で stdout/stderr を一本化しやすくするため）。
- run_monitoring / run_execution の起動フローを整備。
  - 起動時にまず `set_process_priority("high")` を呼び出してプロセス優先度を上げる処理を統一的に実行。
  - DB 接続の扱いを明確化：monitoring は環境にかかわらず本番用 sqlite_path を使用。実行（execution）は `KABUSYS_ENV=paper_trading` の場合に専用 paper_sqlite_path を使用して本番 DB と分離。
- logging_setup: 既存ハンドラがある場合は一旦 flush/close してから再設定し、二重設定を防止。
- process_priority: Windows / POSIX の定数差を吸収する実装に変更し、未対応 OS ではスキップして警告を出す。

### Fixed
- 例外処理の堅牢化。
  - monitoring のポーリングループ中に `monitor.check_once()` が例外を投げてもループを継続し、スタックトレースをログ出力するように変更（サービスの長期稼働性向上）。
  - logging_setup: ログディレクトリ作成に失敗した場合にファイルハンドラ作成をスキップし、プログラムを継続させるフォールバックを実装。
  - process_priority / set_cpu_affinity: 権限不足や機能非対応ケースで AccessDenied / NotImplementedError 等を捕捉して警告し処理をスキップ。
- 環境変数によるポーリング間隔指定 `_get_poll_interval()` で無効な値（0 以下や文字列）を受け取った場合にデフォルトへフォールバックし警告を出すように修正（time.sleep に不正な値が渡らないように保護）。
- config と validate の整合性チェックを追加（config/*.yaml の存在確認と PyYAML 不在時のスキップ警告など）。

### Notes / Known limitations
- research/factor_research.py は実装途中（`calc_momentum` の途中で提供コードが切れています）。完全実装と DuckDB クエリのチューニングが必要。
- 一部の TODO（例: position_sizing における銘柄別 lot_size 拡張、price 欠損時のフォールバック戦略など）がコード内に残っている。
- 本番環境では `KILL_FLAG_CLEAR_ON_START` を `0` にすることを推奨（validate_config が本番での誤設定を警告）。
- `.env` ファイルは機密情報を含むため Git 管理から除外するよう注意喚起がウィザードで表示される。

---

以上が、コードベースから推測してまとめた CHANGELOG です。補足・修正したい点があればお知らせください。