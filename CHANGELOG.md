# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。主な初期リリース履歴を日本語で記載しています。

## [0.1.0] - 初回リリース
リリース日: 未設定

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を設定可能（デフォルト 60 秒）。不正な値（1 未満）は警告してデフォルトにフォールバック。
    - 停止はプロジェクト内 `data/stop_requested.flag` を検出して行う。
    - Monitoring は実行環境にかかわらず本番用の `sqlite_path` を使用する設計。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority 呼び出し）。
    - SQLite（monitoring DB）と DuckDB を接続し、終了時にクローズ。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用の専用 SQLite（デフォルト: `data/paper_trading.db`）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）に対応。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知時に engine.stop() を呼び出して安全に終了。

- 設定管理 / ユーティリティ
  - config.py
    - 設定読み込み・検証用 `Settings` クラスを追加。
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - 多数の設定プロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、Paper Trading 関連、監視閾値、環境/ログレベル判定など）。
    - `paper_fill_mode` の検証（許容値: "instant"/"partial"/"never"/"reject"）。
    - `env` の検証（"development"/"paper_trading"/"live" のみ許可）。

  - config_setup.py
    - 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - multiple 設定項目のプロンプト（シークレット入力、選択肢、デフォルトのサポート）。
    - `.env` の読み書きロジックを実装（既存値の再利用、マスク表示など）。

  - validate_config.py
    - 起動前に環境変数と config/*.yaml の整合性をチェックする CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パース（PyYAML が存在する場合）等を実施。
    - `--strict` フラグで警告も失敗扱いにできる。

  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。
    - 期間指定 (`--from`, `--to`) と明示的 DB パス指定 (`--db`) に対応。
    - 検証指標: 稼働率 (uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシなど。
    - 基準値 (閾値) を定義（例: 稼働率 >= 99.0%、P95 レイテンシ <= 200 ms 等）と、Pass/Fail 判定ロジックを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights: 等金額配分を提供。
    - calc_score_weights: スコア正規化による重み計算。全スコアが 0 の場合は等分配にフォールバックし WARNING を出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限 (max_sector_pct) を超える場合に新規候補を除外。`unknown` セクターは除外対象外（セーフガード）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（"bull":1.0、"neutral":0.7、"bear":0.3、その他は 1.0 にフォールバックし警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した発注株数計算を実装。
    - リスクベースの計算、単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）超過時のスケーリングと端数処理（残差に基づく lot_size 単位の追加配分）を実装。
    - デフォルトパラメータ: risk_pct=0.005, stop_loss_pct=0.08, max_position_pct=0.10, max_utilization=0.70, lot_size=100, cost_buffer（手数料/スリッページ見積り）等。

- ログ & プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。
    - 標準出力（stdout）へ StreamHandler を設定し、TimedRotatingFileHandler による日次ローテーション（デフォルト logs/<app_name>.log、30 日保持）をサポート。
    - LOG_DIR / LOG_LEVEL / 引数からの上書きに対応。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。
    - psutil を利用。アクセス権限不足等の例外は警告してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を追加（任意）。

- 研究用モジュール（途中実装）
  - research/factor_research.py
    - DuckDB の prices_daily / raw_financials を用いたファクター計算の枠組みを追加（Momentum, Value, Volatility, Liquidity の想定）。
    - モメンタム計算（1M/3M/6M、MA200 乖離など）向けの定数と関数シグネチャを用意（実装は途中）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 廃止 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

## 既知の制限 / 注意事項
- .env 自動ロード:
  - プロジェクトルートを .git / pyproject.toml から検出して自動で `.env` / `.env.local` を読み込みます。テストなどで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - `.env.local` は OS 環境変数を保護しつつ上書き読み込みされます（既存 OS 環境変数は保護）。

- モニタリング DB:
  - run_monitoring は実行環境に依らず Settings.sqlite_path（本番監視 DB）を使用します。Paper Trading と完全に分離したいケースは注意してください。

- Paper Trading の分離:
  - run_execution は Paper Trading 時 `paper_sqlite_path` を使用するため、本番 DB と発注履歴が分離されます。

- 外部ライブラリ依存:
  - `psutil`, `duckdb` は必要。YAML 検証は PyYAML がある場合のみ実行され、ない場合は警告してスキップします。
  - ログディレクトリ作成やファイルハンドラの作成に失敗した場合、ログはコンソール出力にフォールバックします。

- 未実装 / TODO:
  - portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少推定される可能性あり。将来的に前日終値や取得原価をフォールバックとして使用する案を記載。
  - research/factor_research.py は一部実装が途中（スクリプト末尾が切れている / 未完）であり、完全なファクター計算ロジックは未完成。

- バックアップ / ローテーション:
  - logging_setup のファイルハンドラは日次ローテーション・30 日保持。ディスク容量やパーミッションに注意してください。

---

必要があれば、各変更点をさらに細かく分割（例えば run_execution の依存コンポーネントやリスク設定のデフォルト値を個別の項目に分ける）して追記できます。どの程度の粒度で履歴を残したいか指示してください。