# Changelog

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

## [0.1.0] - 初回リリース
（初版リリース。以下はコードベースから推測してまとめた主な機能・実装内容と既知の注意点です。）

### 追加
- 全体
  - パッケージ初期公開: パッケージ名 `kabusys`、バージョン `0.1.0` を定義（src/kabusys/__init__.py）。
  - ログ、プロセス優先度、環境設定を含む複数のユーティリティと CLI を実装。

- 起動スクリプト
  - 実行エンジン用起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を最初に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用専用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory を利用してブローカークライアントを作成、ExecutionEngine をスレッドで起動・管理。停止フラグ（data/stop_requested.flag）を検知して安全に停止。
    - 実行用 PID ファイルをサポート（data/execution.pid）。
  - システム監視用起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒、無効値はデフォルトにフォールバック）。
    - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用して監視データを格納。

- 環境設定 / 検証
  - 環境設定読み込み・管理モジュールを追加（src/kabusys/config.py）。
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env のパース処理は export プレフィックス、クォート対応、インラインコメント処理などを考慮。
    - 各種設定プロパティ（DB パス、API トークン、環境フラグ、しきい値等）を提供。環境名のバリデーションあり（development / paper_trading / live）。
  - 対話式の .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - キー/説明/デフォルト/シークレット扱いを定義した項目群を対話的に入力して .env を生成・更新。
    - 生成された .env テンプレートのフォーマットを提供。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の確認、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検証（PyYAML が利用可能な場合）。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次・30世代保持）を設定。
    - ログディレクトリを自動作成。失敗時はファイルハンドラをスキップしてコンソールのみで継続。
    - ログレベル解決順、ログディレクトリ解決順を実装。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS を吸収。nice 値や Windows 優先度を設定。
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。権限不足等は警告してスキップ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算モジュールを追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順 + タイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全スコアが 0 の場合はフォールバックで等配分）。
  - セクター制限・レジーム乗数を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有のセクター比率が max_sector_pct を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）。
    - TODO コメント: 価格欠損時のフォールバックロジックの改善予定（前日終値等）。
  - ポジションサイズ算出モジュールを追加（src/kabusys/portfolio/position_sizing.py）。
    - 複数の allocation_method（risk_based / equal / score）をサポート。
    - 単元株（lot_size）丸め、per-position 上限・aggregate 上限、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングロジックを実装。
    - aggregate cap 超過時はスケールダウンし、残余キャッシュで端数（lot 単位）を再配分するアルゴリズムを実装。

- Execution / Monitoring 周辺（データベース）
  - monitoring 初期化ヘルパー呼び出し（init_monitoring_db）を起動スクリプトから実行して監視用テーブルの存在を保証（冪等）。
  - DuckDB 接続を利用する箇所が存在（分析用 duckdb は設定 DUCKDB_PATH）。ExecutionEngine 等で duckdb_conn を受け渡す設計。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 検証指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - CLI オプション: --from / --to（日付フィルタ）、--db（DB パス上書き）。
    - 既定の閾値（例: 稼働率 >= 99.0%、fill_rate >= 90%、P95 <= 200 ms）に基づき PASS/FAIL を判定。
    - DB 内のテーブルが存在しない場合でも sqlite3.OperationalError を捕捉して耐障害性を持たせて出力を継続。

### 変更
- なし（初回リリースにつき "追加" が中心）

### 修正
- なし（初回リリース）

### 既知の注意点 / 制限事項（推測含む）
- run_monitoring は Monitoring 用 DB として Settings.sqlite_path（デフォルト data/monitoring.db）を使用し、KABUSYS_ENV に関わらず「本番の sqlite_path を使用する」と明示されているため、開発環境での運用時は注意が必要（監視データが本番 DB に混在する可能性）。
- .env の自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後や特殊な配置では検出できず自動ロードがスキップされることがある。
- process_priority の設定は権限不足や OS 非対応時にスキップされる（警告ログで通知）。
- risk_adjustment.apply_sector_cap には price が欠損 (0.0) の場合にエクスポージャーが過少見積りされる懸念がある旨の TODO コメントあり。将来的に前日終値等でのフォールバックを検討する必要あり。
- research/factor_research.py はファイル末尾が途中で切れている（本 changelog 作成時点のソースが不完全である可能性）。ファクター計算のさらなる実装が必要。
- Paper Trading レポートは DB のスキーマ依存であり、対象テーブルが欠けている場合は一部指標が "N/A" になるか、OperationalError を捕捉して既定値にフォールバックする仕様。

### 将来の改善候補（コード内コメント等から推測）
- 個別銘柄の lot_size を銘柄マスタに持たせ、銘柄別の lot_map をサポートする（現状は全銘柄共通 lot_size を想定）。
- price 欠損時のフォールバック戦略（前日終値、取得原価など）を実装してエクスポージャー計算の精度を向上させる。
- research モジュールの完成（ファクター計算の SQL / 正規化ユーティリティ統合）。
- 実運用向けの詳細な監視・アラート（LINE 通知等）の強化。validate_config による本番ガードはあるが、運用時のオペレーション手順を整備する。

---

この CHANGELOG はコードベースの内容から推測してまとめたものです。実際のリリースノート作成時は、コミット履歴・差分と運用上の決定を参照して適宜更新してください。