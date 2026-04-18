# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。重要な変更点を日本語でまとめています。

全般的な注意:
- デフォルトの設定ファイルやデータベースパスはプロジェクト内の `data/` ディレクトリを想定しています（例: `data/monitoring.db`, `data/kabusys.duckdb`, `data/paper_trading.db`）。
- 環境変数の自動読み込み（.env / .env.local）や CLI ウィザードが提供され、ローカル開発やペーパートレード／本番切替を簡単に行えます。

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期実装
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 設定管理
  - Settings クラス (`kabusys.config.Settings`) を追加。環境変数から各種設定値を取得するプロパティを提供（J-Quants トークン、kabu API パスワード、DB パス、PID / kill flag パス、閾値など）。
  - 自動 .env 読み込み機能を追加:
    - プロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を読み込む。
    - OS 環境変数は保護され、`.env.local` は既存の環境変数を上書き可能（保護キーは上書きされない）。
    - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パースの細かな実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント対応（クォート無しでも先頭または直前にスペースがある `#` はコメント扱い）など。

- 環境ウィザード / 設定ツール
  - 対話式 `.env` 作成・更新ウィザード (`kabusys.config_setup`) を追加。
    - 各項目の説明付きプロンプト、シークレットマスク、デフォルト値、選択肢サポート。
    - 保存前に確認を行い `.env` を書き出す。
  - 設定検証 CLI (`kabusys.validate_config`) を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の値検査、DB パス（親ディレクトリ存在チェック）、`config/*.yaml` の存在チェックと（PyYAML があれば）パース検証、KABUSYS_ENV=live 時のガードチェックなど。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト (`kabusys.run_execution`) を追加。
    - `Settings` に基づく DB 接続。`KABUSYS_ENV=paper_trading` の場合はペーパートレード専用 SQLite（`paper_sqlite_path`）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成（paper/live に応じた実装を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。エンジンは別スレッドで実行し、`data/stop_requested.flag` による停止検知、PID ファイル管理を行う。
    - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を初期化し、初期の available_cash をブローカーから取得して使用する。
  - 監視ループ起動スクリプト (`kabusys.run_monitoring`) を追加。
    - `SystemMonitor` を初期化し、監視ループを実行。デフォルトポーリング間隔は 60 秒で、環境変数 `MONITOR_POLL_INTERVAL` で上書き可能。値のバリデーション（1 未満は無効）を行い、不正な値はデフォルトにフォールバックして警告出力。
    - 監視は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化（`init_monitoring_db`）。
    - 停止フラグ（`data/stop_requested.flag`）検知でループ終了。

- モニタリング DB 初期化
  - `init_monitoring_db`（監視テーブルが存在することを保証する冪等処理）を起動処理で呼び出す実装を採用（監視・実行の双方で呼び出し）。

- ユーティリティ
  - ロギングセットアップ (`kabusys.utils.logging_setup`) を追加:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（アプリ別ファイル、日次ローテーション）を設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - ログレベルは引数 -> 環境変数 `LOG_LEVEL` -> デフォルト "INFO" の順で解決。
    - ログディレクトリは引数 -> 環境変数 `LOG_DIR` -> デフォルト "logs/" の順で解決。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity ユーティリティ (`kabusys.utils.process_priority`) を追加:
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収する API を提供。`set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)`。
    - psutil を利用。権限不足や未対応環境では警告を出してフォールバック。

- ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定・重み付け (`kabusys.portfolio.portfolio_builder`):
    - select_candidates (score 降順 / signal_rank によるタイブレーク)、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等配分にフォールバックして WARNING）。
  - セクター集中制限・レジーム補正 (`kabusys.portfolio.risk_adjustment`):
    - apply_sector_cap：既存保有のセクター比率が上限を超える場合に同セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier：レジームラベル（"bull"/"neutral"/"bear"）に応じて資金乗数を返す（未知ラベルは 1.0 にフォールバックして警告）。
  - 株数決定・リスク制限 (`kabusys.portfolio.position_sizing`):
    - calc_position_sizes を実装。`allocation_method` に応じた計算（"risk_based", "equal", "score"）。単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer を使った保守的見積り、端数処理ロジックなどを備える。

- 研究（リサーチ）モジュール（初期）
  - `kabusys.research.factor_research` にモメンタム等のファクター計算の骨格を追加（DuckDB 接続を前提、momentum、MA200、ATR、出来高系などを計画）。（ファイル末尾は一部未掲載・実装継続中）

- ツール
  - Paper Trading 検証レポート生成スクリプト (`kabusys.tools.paper_verification_report`) を追加:
    - ペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH` または引数 `--db`）から指標を集計してレポート出力。
    - 集計指標: ポーリング稼働率（uptime）、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg / max / P95）。
    - P95 計算実装、日付フィルタ `--from` / `--to` サポート。
    - デフォルト基準値（合格/不合格判定）を設定:
      - 稼働率 >= 99.0%
      - 注文成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- run_monitoring と run_execution の停止制御はファイルベースのフラグ（`data/stop_requested.flag`）および PID ファイルで行う設計。kill スイッチ用のパスは Settings で取得可能。
- 設定検証 (`validate_config`) は PyYAML が無い場合でも実行可能で、YAML 検証はスキップされるが警告が出る。
- process_priority / cpu_affinity は権限やプラットフォームによっては無視される。失敗時はログに警告が出るのみでプロセスは継続する。
- .env の読み込みロジックは堅牢に設計されており、クォートのエスケープやコメント処理に注意している。

もしリリースノートで特に強調したい項目（例: paper_trading の分離動作、デフォルト閾値、監視ポーリングの上書き方法、ログ出力先の明示など）があれば追加して更新します。