# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。
この履歴は、ソースコードの内容から推測して作成しています。

## [Unreleased]

### 追加 (Added)
- 初期公開相当の機能群を追加。
  - CLI / 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（デフォルト 60 秒）を上書き可能。監視は環境設定にかかわらず本番 sqlite_path を使用する設計。停止はプロジェクト直下の data/stop_requested.flag で検出。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient（ペーパートレード）を使用し、ペーパートレード用 DB（デフォルト data/paper_trading.db）に記録。停止フラグと PID ファイルによる制御に対応。
  - 設定管理
    - config.py: Settings クラスを導入し、環境変数から各種設定を取得する API を提供。自動 .env ロード機能（プロジェクトルートの .env / .env.local、OS 環境変数を保護）を備える。以下の検証・規約を実装：
      - KABUSYS_ENV の許容値チェック（development / paper_trading / live）
      - LOG_LEVEL の検証
      - PAPER_FILL_MODE の検証（instant / partial / never / reject、デフォルト: instant）
      - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID/kill flag 等）のプロパティ提供
  - 設定ユーティリティ / CLI
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット入力・選択肢・デフォルト値サポート。
    - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と（PyYAML があれば）パース検証、本番ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の危険設定）などを報告。--strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築ライブラリ
    - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
    - portfolio.risk_adjustment: セクター集中制限を行う apply_sector_cap と、レジームに応じた投下資金乗数 calc_regime_multiplier を追加（"bull"/"neutral"/"bear" のマップ、未知レジームはフォールバック）。
    - portfolio.position_sizing: 各銘柄の発注株数を決定する calc_position_sizes を追加。allocation_method として "risk_based" / "equal" / "score" をサポートし、単元株（lot_size）丸め、per-stock 上限・aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積）を考慮するロジックを備える。
  - 実行ユーティリティ
    - utils.process_priority: プラットフォーム差を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX（Linux, macOS, FreeBSD）対応。権限不足などで設定できない場合は警告を出してスキップする。
  - 解析 / リサーチ
    - research.factor_research: DuckDB 接続を受け取り、prices_daily 等のテーブルからモメンタム（1M/3M/6M、MA200 乖離）やボラティリティ（ATR、平均売買代金、出来高比率）などのファクターを計算する関数を追加。設計は外部 API に依存せず DuckDB 上の SQL+Python 処理で実行。
  - ツール
    - tools.paper_verification_report: ペーパートレード用 SQLite を読み、システム稼働率、注文成功率、送信率、レイテンシ（P95 含む）、リスク却下数などを集計して PASS/FAIL レポートを生成するスクリプトを追加。閾値はソース内で定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）されている。日付フィルタおよび DB パス指定オプションをサポート。
  - DB / 分析バックエンド
    - sqlite3（監視・ペーパートレード DB）と duckdb（分析用 DB）の併用を標準に採用。監視テーブル初期化のための init_monitoring_db 呼び出しを組み込み（冪等）。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"（初期バージョン）

### 変更 (Changed)
- 起動スクリプト系でプロセス優先度を最初に "high" に設定する方針を採用（set_process_priority を呼び出す）。
- run_monitoring と run_execution において、停止フラグ（data/stop_requested.flag）と PID ファイルを使ったプロセス制御を統一的に扱うようにした。

### 修正 (Fixed)
- .env 読み込みの堅牢化:
  - _parse_env_line にて export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを実装。これにより多様な .env 形式を正しく扱えるように改善。
- position_sizing のスケーリングロジックで単元株（lot_size）丸めや残余配分の再現性（安定ソート）を導入し、資金配分の決定が安定するようにした。
- process_priority の実行時に、未サポート OS や権限不足の場合は警告を出して処理をスキップすることで起動失敗を防止。

### ドキュメント (Documentation)
- 各スクリプト（run_monitoring/run_execution/config_setup/validate_config/tools.paper_verification_report）に使用方法の docstring・ヘルプを追加。設定ウィザードで生成される .env のテンプレートコメントも含む。

## [0.1.0] - 2026-04-18

初回公開リリース。上記「追加」項目を含む初期安定版。

- 主要機能
  - 環境設定管理・ウィザード・起動前検証
  - 実行エンジンと監視ループの起動スクリプト
  - ポートフォリオ構築（候補選定、重み付け、リスク調整、ポジションサイズ計算）
  - リサーチ用ファクター計算（DuckDB ベース）
  - ペーパートレード結果検証レポート生成ツール
  - クロスプラットフォームのプロセス優先度設定ユーティリティ

注記:
- 設定ファイル（.env）には機密情報が含まれるため、リポジトリへコミットしないでください（config_setup のヘッダにも明記）。
- 本番運用時は KABUSYS_ENV=live の設定に注意してください。validate_config によるチェックと LINE 通知設定を推奨します。

---

今後の改善案（予定・提案）
- portfolio.position_sizing で銘柄ごとの lot_size をマスタから読み込めるように拡張。
- apply_sector_cap における価格欠損時のフォールバック（前日終値や取得原価）を実装。
- research モジュールのファクター計算に対するユニットテストとパフォーマンス最適化。
- validate_config による config/*.yaml のスキーマ検証強化（可能なら JSON Schema 等を採用）。

以上。