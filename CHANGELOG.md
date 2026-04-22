# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
リリース日はコード内の参照日や現在日付を元に推測しています。

## [0.1.0] - 2026-04-22

初回公開リリース。以下の主要機能・ユーティリティ類を導入しました。

### Added
- 全体
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - 複数の CLI / 起動スクリプトを追加（監視、実行、設定ウィザード、設定検証、各種ツール）。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env パーサーを強化:
    - export プレフィックス対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理（クォートなし時の仕様）
  - 自動ロード優先順位の実装: OS 環境 > .env.local > .env。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 各種設定プロパティを実装（DB パス、PID ファイル、Kill フラグ、モニタ閾値、PAPER_FILL_MODE の検証など）。
  - Settings インスタンス settings をモジュールレベルで提供。

- 設定ウィザード（src/kabusys/config_setup.py）
  - 対話式ウィザードで .env を作成・更新する CLI を追加。
  - 項目定義、既存 .env 読み込み、シークレットマスク表示、保存確認機能を実装。

- 設定検証ツール（src/kabusys/validate_config.py）
  - 起動前に .env および config/*.yaml の基本チェックを行う CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML がある場合）を実装。
  - --strict オプションで警告を FAIL 扱いにする機能を追加。

- ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
  - setup_logging() を追加し、標準化したログ設定を提供。
  - stdout へ StreamHandler（標準出力）出力、および日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日分保持）を設定。
  - LOG_LEVEL / LOG_DIR の解決順を実装し、ログディレクトリ作成失敗時はファイル出力を安全にスキップするフォールバックを実装。

- プロセス優先度 / CPU アフィニティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) を追加し、Windows/Linux/Mac の差分を吸収して優先度設定を行う（失敗時は警告でスキップ）。
  - set_cpu_affinity(cpu_count) を追加し、先頭 N コアにプロセスをピン留めする機能を提供（未対応環境では安全にスキップ）。
  - サポートレベル: "high" / "normal" / "low"。

- 監視ループ（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループ起動スクリプトを追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
  - 監視 DB は KABUSYS_ENV に依らず production sqlite_path を使用する仕様。
  - 起動時にプロセス優先度を high に設定、停止フラグ（data/stop_requested.flag）の検知でクリーンに停止。

- 実行エンジン起動（src/kabusys/run_execution.py）
  - ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（data/paper_trading.db）を使い、本番 DB と分離する動作を実装。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、ExecutionEngine をデーモンスレッドで実行。
  - 停止フラグや execution.pid の扱いを実装（停止時 engine.stop() を呼ぶ）。

- モニタリング DB 初期化フック
  - run_monitoring と run_execution 両方で監視テーブルの存在を保証する init_monitoring_db を呼び出す（冪等性の確保）。

- ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: buy シグナルのスコア降順選定（タイブレークに signal_rank を採用）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全銘柄スコア 0 の場合は等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限を考慮して候補を除外（unknown セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear、未知はフォールバック 1.0）。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の複数配分方式を実装。
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を用いた保守的見積り、aggregate cap によるスケーリング、端数処理（残差順で lot 単位を追加）を実装。
    - 価格欠損時のスキップやログ出力を実装。

- Paper Trading 検証ツール（src/kabusys/tools/paper_verification_report.py）
  - ペーパートレード用 SQLite から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポートを標準出力に生成するツールを追加。
  - P95 計算ユーティリティと各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
  - --from/--to/--db オプションをサポート。

- リサーチ（src/kabusys/research/factor_research.py）
  - DuckDB を用いたファクター計算モジュールの雛形を追加（Momentum / Value / Volatility / Liquidity を想定）。実装方針と定数を整備（計算範囲・ウィンドウ長など）。

### Changed
- なし（初回リリースのため既存変更ではなく新規追加が中心）。

### Fixed
- なし（初回リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- 環境変数にシークレットを扱う部分は .env の Git コミット禁止コメントを生成するなど、運用上の注意をドキュメント的に明示。

## その他（運用上の注意）
- 本番環境では KABUSYS_ENV を適切に設定し、KILL_FLAG_CLEAR_ON_START はデフォルト 0 を推奨（validate_config による警告あり）。
- .env に JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須項目を設定する必要がある（未設定時は Settings._require によって起動時例外）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続するため、ディスク容量や権限に注意。
- process_priority / cpu_affinity の設定は OS 権限に依存するため、権限不足時は警告が出てスキップされる。

---

今後のリリース候補（例）
- モジュール単位のテスト追加、CI 設定
- position_sizing の銘柄別 lot_size 対応（stocks マスタの導入）
- factor_research の完全実装とユニットテスト
- monitoring/execution のユニットテスト用フック（DI の強化）
- duckdb スキーマ初期化スクリプトの追加

（必要であれば、ファイル単位の更に詳細な変更点一覧を追加で生成します。）