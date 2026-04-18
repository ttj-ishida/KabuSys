# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
このファイルは、コードベースの内容から推測して作成しています（実装時点の機能一覧・挙動の要約）。

## [0.1.0] - 初回リリース（推定）
（初版リリース。主な機能を初めて実装）

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 実行/監視の起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - ExecutionEngine の起動フローを実装（ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler 組み立て、別スレッドで run_session 実行）。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading DB を使用して本番 DB と分離（`PAPER_TRADING_SQLITE_PATH` / `settings.paper_sqlite_path`）。
    - 停止制御用フラグファイル（data/stop_requested.flag）と pid ファイル（data/execution.pid）に対応。停止フラグ検知で安全停止。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - SystemMonitor の単発チェックを一定間隔で実行するポーリングループ（デフォルト 60 秒）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（不正値は警告してデフォルトにフォールバック）。
    - 監視用 DB は環境にかかわらず本番の sqlite_path を使用する設計（監視は本番データへ記録する前提）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。KeyboardInterrupt にも対応。

- 設定管理
  - `kabusys.config` モジュールを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み（優先度: OS env > .env.local > .env、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - .env のパース実装（export プレフィックス対応、クォート内のエスケープ、インラインコメントの扱いなどを考慮）。
    - Settings クラスで多数の設定プロパティを提供（J-Quants トークン、kabu API、LINE, DuckDB/SQLite パス、paper_trading 用設定、各種監視閾値、環境判定ユーティリティ等）。
    - `paper_fill_mode` の検証（有効値チェック）。
  - 設定ウィザード CLI (`config_setup.py`) を実装。
    - 対話式で .env を作成・更新するウィザード。入力中のシークレットはマスク表示。
    - 保存前の確認表示、キャンセル時の挙動を明記。
    - デフォルト値と説明文を備えた複数項目セット（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
  - 設定検証 CLI (`validate_config.py`) を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合は）パース検証、本番モード時のガードチェックを実装。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - `utils.logging_setup.setup_logging` を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）を設定。
    - LOG_DIR 作成失敗時はファイルロギングをスキップしてコンソールのみで継続。
    - ログレベル解決順や既存ハンドラの二重設定防止処理を実装。
  - `utils.process_priority` を追加。
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（psutil ベース）。`set_process_priority("high"|"normal"|"low")`。
    - CPU Affinity の設定ユーティリティ `set_cpu_affinity` を提供（権限不足時は警告でスキップ）。

- ポートフォリオ構築関連モジュール
  - `portfolio.portfolio_builder` を実装。
    - シグナル候補の選定（score 降順、signal_rank によるタイブレーク）、等配分・スコア加重配分関数を提供。
  - `portfolio.risk_adjustment` を実装。
    - セクター集中制限を適用する `apply_sector_cap`（既存保有のセクターエクスポージャーに基づく候補フィルタリング）。
    - 市場レジームに基づく投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - `portfolio.position_sizing` を実装。
    - 複数の配分方式（risk_based / equal / score）に応じた発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ想定）を考慮したスケールダウンと端数処理。

- 解析・検証ツール
  - Paper Trading 検証レポート生成ツール `tools/paper_verification_report.py` を追加。
    - SQLite の paper_trading DB（default: data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を集計。
    - P95 計算、期間フィルタ（--from / --to）、DB パス指定（--db / 環境変数）に対応。
    - 判定基準（しきい値）を定義して PASS/FAIL を出力。
  - research モジュールにファクター計算開始（`research.factor_research`）。
    - モメンタム等の計算方針を実装（DuckDB を用い prices_daily / raw_financials を参照）。（実装は部分的に含まれているが一部未完の可能性あり）

- DB 初期化ユーティリティ
  - 監視用 DB の初期化を行う `monitoring.monitoring_db.init_monitoring_db` を各起動スクリプトから呼び出して、監視テーブル存在を保証（冪等実行）。

### 変更 (Changed)
- ログ出力先の方針
  - StreamHandler は stdout に出力する設計に統一（cron 等で stdout/stderr をリダイレクトする運用を想定）。

### 修正 (Fixed)
- .env パーサの強化
  - export プレフィックス、クォート内バックスラッシュエスケープ、インラインコメント判定の改善を実装。既存 OS 環境変数を保護するため `protected` 引数で上書き制御。

### 注意点 / 実装上の補足
- run_monitoring の監視 DB は環境に依存せず常に `Settings.sqlite_path`（本番想定）を使用します。監視データを本番 DB に記録したくない場合は設定・設計上の考慮が必要です。
- run_execution は paper_trading 環境で DB を分離する実装がありますが、その他の資産管理・執行ロジックは外部コンポーネント（BrokerClientFactory、ExecutionEngine 等）に依存します。実行時の挙動はこれらコンポーネントの実装に依存します。
- `research.factor_research` はファクター計算の骨子が実装されていますが、ファイル末尾が途中で切れているため（ここに含まれるコードは途中まで）、完全な実装・テストが必要です。
- `utils.process_priority` / `set_cpu_affinity` は psutil を利用しており、権限不足や OS 非対応時には警告を出して安全にスキップします。
- `config_validate` は PyYAML 未導入時も警告を出して YAML 検証をスキップし、存在確認のみ行います。

---

今後の想定更新（例）
- factor_research の完全実装とテスト
- ExecutionEngine 周りの詳細実装（注文ライフサイクル、再試行戦略等）
- 監視アラート（LINE 通知）や監視ルールの拡張
- 単体テスト・CI 設定の追加

(以上)