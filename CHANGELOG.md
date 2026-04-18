# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
このプロジェクトの初回公開リリースは 0.1.0 です。

全般
- セマンティックバージョニングを採用しています（例: 0.1.0）。
- デフォルトバージョン: 0.1.0

## [Unreleased]
（作業中の変更をここに記載します）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション基盤を追加
  - パッケージのバージョン定義: kabusys.__version__ = "0.1.0"。
- 設定管理
  - 環境変数/`.env` 読み込みユーティリティを実装（kabusys.config）
    - プロジェクトルートを .git または pyproject.toml から自動検出して `.env` / `.env.local` を自動読み込み。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
    - `.env` のパースはコメント、`export KEY=val` 形式、シングル/ダブルクォート、エスケープ、行内コメント（スペース直前の `#` 扱い）に対応。
    - 必須環境変数チェック用の `_require()` を提供。
    - Settings クラスで主要設定（DB パス、API トークン、運用環境フラグ、監視しきい値等）をプロパティとして取得可能。
    - 環境値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）のバリデーションを組み込み。無効値は ValueError を送出。

- 設定ウィザード CLI（kabusys.config_setup）
  - 対話式で `.env` を作成・更新するウィザード実装（`python -m kabusys.config_setup`）。
  - シークレット入力サポート、既存値の再利用、デフォルト値表示、確認後のファイル書き出しを実装。
  - デフォルト `.env` フィールド群（API トークン、DB パス、ログレベル、KILL フラグ設定など）を定義して書き出し。

- 設定検証 CLI（kabusys.validate_config）
  - `.env` と config/*.yaml の起動前検証用 CLI を実装（`python -m kabusys.validate_config`）。
  - 必須環境変数の未設定検出、KABUSYS_ENV の妥当性チェック、LOG_LEVEL の確認、DB パスの親ディレクトリ存在チェックを実装。
  - PyYAML がインストールされている場合は YAML ファイルのパース検証を実施。未インストール時は警告を出し検証をスキップ。
  - `--strict` オプションで警告を FAIL 扱い（exit code 1）にできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - 実行開始時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV = "paper_trading" の場合、Paper Trading 専用 SQLite DB（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を行う。
    - 停止フラグ（data/stop_requested.flag）を検知して安全停止する仕組みを実装。PID ファイル出力パス指定あり。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - 監視用 SystemMonitor を初期化してポーリングループを実行（デフォルト 60 秒間隔）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能。無効値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV に依存せず常に本番用の sqlite_path を使用する旨の挙動。

- ロギングユーティリティ（kabusys.utils.logging_setup）
  - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定する共通ユーティリティを追加。
  - ログレベルは関数引数 > 環境変数 LOG_LEVEL > デフォルト INFO の優先度で解決。
  - ログディレクトリは引数 > LOG_DIR 環境変数 > `logs/` の優先度で解決。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - 日次ローテーション、30 日分のバックアップ保持。

- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度を設定する set_process_priority(level) を実装。
  - CPU affinity を先頭 N コアに固定する set_cpu_affinity(cpu_count) を実装。
  - 権限不足や未対応 OS 時は警告を出して安全にフォールバック。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 銘柄候補選定（select_candidates）：スコア降順、同点時 signal_rank のタイブレーク。
  - 重み計算
    - 等金額配分 calc_equal_weights
    - スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等配分へフォールバックし警告）
  - リスク調整
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）に基づく候補フィルタリング。既存保有のセクター別時価を考慮し、当日売却予定銘柄を除外可能。
    - calc_regime_multiplier: マーケットレジーム（bull/neutral/bear）に応じた資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告。
  - ポジションサイジング（calc_position_sizes）
    - allocation_method: "risk_based", "equal", "score" をサポート。
    - risk_based: 許容リスク率、損切り率などからポジションサイズを算出。
    - 単元株（lot_size）の丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）、および aggregate cap（available_cash 超過時のスケールダウン）を実装。
    - cost_buffer（スリッページ/手数料見積）を考慮して保守的に算出。スケーリング後の残差は lot 単位で再配分するロジックを実装。
    - 価格欠損時はスキップし、ログにデバッグメッセージを出力。

- Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用 SQLite DB（デフォルト `data/paper_trading.db`）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計・表示する CLI を実装。
  - デフォルトの合格基準（閾値）を定義:
    - 稼働率 >= 99.0%
    - 注文成功率（Filled/Created） >= 90.0%
    - 送信率（Sent/Created） >= 95.0%
    - P95 レイテンシ <= 200 ms
  - 日付フィルタ（--from / --to）と DB パスの上書き（--db）をサポート。標準出力でレポート出力。

- リサーチ（kabusys.research）
  - ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity を想定、DuckDB を使った計算方針を実装予定）。
  - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してファクターを計算する方針を明示。

- パッケージ構成
  - tools、portfolio、utils、monitoring、execution、research 等のモジュール群を追加。
  - 主要な CLI/スクリプトエントリポイント（run_execution, run_monitoring, config_setup, validate_config, tools.paper_verification_report）を提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 機密値（J-Quants トークン、kabu API パスワード等）は .env に保存し、config_setup にてシークレット入力をサポート。`.env` を Git にコミットしない旨を README/生成ファイルヘッダーで明示。

---

注記 / 運用上のポイント
- Monitoring は KABUSYS_ENV にかかわらず、Settings.sqlite_path の DB を使用します（監視データは本番 DB に集約する設計）。Execution は paper_trading 環境の場合専用 DB に分離します。
- プロセス優先度や CPU affinity の設定は権限や OS に依存します。設定に失敗した場合は警告のみで処理を続行します。
- `.env` 自動読み込みを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- YAML 検証には PyYAML が必要です。インストールされていない環境では YAML の内容チェックをスキップし、警告が出ます。

使用例
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

もしリリースノートに追加してほしい詳細や、特定ファイル単位の差分（例: どの関数を実装したか等）があれば教えてください。必要に応じて項目を展開して追記します。