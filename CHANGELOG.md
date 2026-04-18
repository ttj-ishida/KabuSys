# Changelog

すべての注目すべき変更はここに記載します。フォーマットは "Keep a Changelog" に準拠します。  

なお本文はリポジトリ内のソースコードから実装内容を推測して作成しています。

## [Unreleased]

（現在の開発途中の変更点・注意点などをここに記載してください）

- 開発中のファイルや未完成の実装が含まれる可能性があります（例: research/factor_research.py の一部は実装途中の痕跡が見られます）。  
- 追加・修正をリリースする際に、該当する項目をバージョンセクションに移してください。

---

## [0.1.0] - 2026-04-18

初期リリース。主要なモジュール群と起動スクリプト、ユーティリティ、ポートフォリオ構築ロジック、検証ツールなどを追加。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（data/paper_trading.db、環境変数で上書き可能）を使用する。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動ループを実装。  
    - プロセス優先度を高に設定し、停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。  
    - 監視用 DB 初期化（init_monitoring_db）、sqlite / duckdb 接続の確立、停止フラグ検知での安全終了処理を実装。

- 設定関連
  - config.py：.env 自動読み込み、堅牢な .env パース（クォート・エスケープ・export 形式対応）、Settings クラスによる環境変数のラップとバリデーションを追加。  
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のパス取得ユーティリティ、paper_fill_mode の検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェックなどを実装。  
  - config_setup.py：対話式 .env 作成ウィザードを追加。既存 .env 読み込み・編集、秘匿値のマスク表示、確認後 .env 保存機能を提供。
  - validate_config.py：起動前チェック CLI を追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリの存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向けの注意喚起を行う。`--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py：シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。  
    - スコアが全て 0 の場合は等分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py：セクター集中上限適用（apply_sector_cap）、市場レジームに基づく投下資金乗数計算（calc_regime_multiplier）を実装。  
    - セクター不明（"unknown"）は上限適用対象外、未知レジームはフォールバックして 1.0 を返す。
  - portfolio/position_sizing.py：株数決定ロジックを実装（allocation_method: risk_based / equal / score）。  
    - 単元株（lot_size）丸め、1 銘柄上限・全体利用上限、cost_buffer を考慮したスケーリング（aggregate cap）と残余の分配ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py：統一的なログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせて設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。ログレベル / ログディレクトリの解決順を定義。
  - utils/process_priority.py：プラットフォーム非依存のプロセス優先度設定ユーティリティを追加。  
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応、nice 値・Windows の優先度定数をラップ。CPU affinity 設定関数も提供。設定失敗時は警告を出す耐障害設計。

- モニタリング DB 初期化ユーティリティ
  - monitoring.monitoring_db モジュール（run_* から呼び出し）を経由して監視テーブル生成を保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py：ペーパートレード用 SQLite を対象に稼働率、注文成功率、送信率、P95 レイテンシなどを集計・判定してレポートを標準出力に出力する CLI を追加。  
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）で PASS/FAIL 判定を行う。日付フィルタは --from / --to で指定可能。

- リサーチ（ファクター算出）
  - research/factor_research.py：ファクター計算モジュール（モメンタム等）を追加。DuckDB の prices_daily / raw_financials を前提に、モメンタム（1M/3M/6M）、MA200乖離率、ATR、流動性等の計算設計を含む。

### 変更 (Changed)
- プロジェクトルート検出ロジックを導入（config._find_project_root）して .env 自動読み込みが CWD に依存しないように改善。
- ログ出力は stdout を優先し、ファイル出力はログディレクトリ作成成功時のみ有効化する設計に変更（外部環境での安全な起動を想定）。

### 修正 (Fixed)
- 環境変数/設定読み込みに関する堅牢性を向上：.env のパースがクォート・エスケープ・コメントを正しく扱うよう改善。  
- run_monitoring と run_execution の停止ハンドリングの強化（stop flag ファイルの検知、KeyboardInterrupt の捕捉、接続クローズを finally で保証）。

### 注意事項 / 既知の制約 (Notes)
- config.py の自動 .env 読み込みはプロジェクトルートが検出できない場合はスキップされます。CI / テストで自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。  
- research/factor_research.py は設計・計算方針を含む実装が含まれていますが、運用前に DuckDB スキーマと照合して十分なテストを行ってください。  
- 一部の機能（ブローカークライアント、ExecutionEngine 内部など）は外部依存（API / DB スキーマ）に依存するため、環境セットアップ（.env、config/*.yaml、DB 初期化）を事前に行ってください。

---

今後のリリースでは以下を想定しています（計画例）
- factor_research の完成とユニットテスト追加
- ExecutionEngine / BrokerClient のエンドツーエンドテストとモック整備
- ドキュメント（README / Setup / 運用手順）の充実

（必要であれば、この CHANGELOG を実際のコミット履歴に沿って細分化・調整します。どの程度の粒度で履歴を残すか指示ください。）