# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠し、バージョニングは SemVer を採用します。

## [0.1.0] - 2026-04-21

### Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper DB（`data/paper_trading.db`）と MockBrokerClient を使用し、本番 DB と完全に分離。
    - プロセス優先度を起動時に "high"へ設定する処理を追加 (utils.process_priority)。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）に対応。
    - ExecutionEngine を別スレッドで起動し、停止フラグ検知で安全に停止する制御を実装。
    - 依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、duckdb）を組み立てて起動。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックして警告を出す実装。
    - Monitoring は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用する挙動を明示。
    - 停止フラグファイル検知でループを終了し、例外発生時はログを残して次のポーリングへ継続。

- 設定管理・CLI
  - config.py
    - 環境変数と .env ファイルの読み込みロジックを提供。
    - プロジェクトルート自動検出（`.git` または `pyproject.toml` を起点）に基づいて `.env` / `.env.local` を自動ロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - `.env` のパースは `export KEY=val`、シングル/ダブルクオート、エスケープ、インラインコメント等に対応する堅牢な実装。
    - Settings クラスを提供し、各種環境設定（DB パス、PID/kill flag、閾値、paper_trading 周りの設定等）をプロパティとして取得可能。必須キー未設定時は明示的なエラーを投げる `_require()` を実装。

  - config_setup.py
    - 対話式の .env ウィザードを実装。
    - 主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 関連、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話的に作成・更新可能。
    - 既存 .env 読み込みと入力のスキップ（Enter で既存値・デフォルトを利用）に対応。
    - .env の書き出し機能を提供（重要: .env を Git にコミットしない旨の注意文付き）。

  - validate_config.py
    - 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在および（PyYAML があれば）パース検証を実施。
    - `KABUSYS_ENV=live` 時の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング・ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトから統一して呼べるログ設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（デフォルト `logs/<app_name>.log`、30 日分保持）をルートロガーに設定。
    - ログレベルは引数 > 環境変数 `LOG_LEVEL` > デフォルト `"INFO"` の順で解決。
    - ログディレクトリ作成失敗時は警告を出しファイル出力をスキップしてコンソール出力のみで継続。

- プロセス優先度・CPU 固定ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定（`set_process_priority("high"|"normal"|"low")`）を追加。psutil を利用。
    - CPU affinity 設定のための `set_cpu_affinity` を追加（core 数指定）。権限不足や未サポート環境では警告を出してスキップ。

- ポートフォリオ構築モジュール（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレークに signal_rank）`select_candidates`
    - 等重配分 `calc_equal_weights`
    - スコア加重 `calc_score_weights`（全銘柄スコアが 0 の場合は等重にフォールバックし警告）
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap`（既存保有のセクター比率が閾値を超える場合に新規候補を除外、`sell_codes` を露出計算から除外可能、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を算出する `calc_position_sizes`（`risk_based`、`equal`、`score` の allocation_method をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、ポートフォリオ全体の投下上限（max_utilization）を考慮。
    - cost_buffer を用いた保守的コスト見積・スケーリング、残余キャッシュを用いた lot 単位の端数配分ロジックを実装。
    - 価格欠損（<=0）に対するスキップとそのログ出力あり。

- リサーチ（骨組み）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加。DuckDB 接続を受け prices_daily / raw_financials を参照してモメンタム/バリュー/ボラティリティ/流動性等を計算する設計。
    - モメンタム計算（例: mom_1m/mom_3m/mom_6m、MA200乖離）を実装するための定数と関数（calc_momentum）の骨組みを追加（実装継続中）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（avg/max/P95）などを計算して期間レポートを標準出力に表示。
    - 判定基準（閾値）を定義し、PASS/FAIL の判定を行う（例: 稼働率 >= 99%、fill_rate >= 90%、P95 <= 200ms 等）。
    - DB ファイルパスは引数 `--db` / 環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db` で指定可能。

### Changed
- （初版のため履歴なし）

### Fixed
- （初版のため履歴なし）

### Notes / Important Behaviour
- .env 自動読み込みはデフォルトで有効。テストや特殊状況では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化可能。
- monitoring（run_monitoring.py）は KABUSYS_ENV に関係なく本番の `SQLITE_PATH` を参照します。環境による分離が必要な場合は運用上の注意が必要です。
- process_priority / cpu_affinity の設定は実行環境の権限によって失敗する可能性があります。失敗時は警告ログを出してスキップします。
- `validate_config` は PyYAML がない場合、YAML の内容検証をスキップして警告を出します（ただし存在チェックは行います）。
- Paper Trading と Live 環境の DB は分離されるよう設計されていますが、運用時は .env の設定を必ず確認してください。

---

（注）本 CHANGELOG は現行コードベースの内容から推定して作成しています。将来的な実装の追加・修正に応じて更新してください。