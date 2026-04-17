# Changelog

すべての重要な変更は Keep a Changelog に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。以下の主要機能と実装を含みます。

### Added
- 基本アプリケーションメタ情報
  - パッケージバージョンを定義（kabusys.__version__ = "0.1.0"）。

- 設定管理
  - Settings クラスによる環境変数取得ラッパーを実装（J-Quants / kabu API / LINE / DB /監視閾値など）。
  - .env 自動読み込み機能を追加（プロジェクトルートの .env / .env.local を順に読み込み、OS 環境変数を保護）。
  - .env パーサーは引用符・エスケープ・export形式・行末コメントなどの多様なケースに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - Settings による入力検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などの妥当性チェック）。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を作成 / 更新する CLI を追加（シークレットマスク表示、デフォルト値、保存確認）。
  - validate_config: .env と config/*.yaml の事前検証ツールを追加。--strict オプションで警告を失敗扱いにできる。
  - validate_config は PyYAML の有無に応じて YAML の構文チェックを行う（未インストール時はスキップして警告）。

- 実行（Execution）関連
  - run_execution スクリプトを追加:
    - プロセス優先度を上げる処理を最初に実行（set_process_priority("high")）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアントの抽象化。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと実行スレッド管理。
    - 停止フラグファイル（data/stop_requested.flag）を監視し、安全にエンジンを停止する仕組み。
    - PID ファイル出力（data/execution.pid）。

- 監視（Monitoring）関連
  - run_monitoring スクリプトを追加:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化。
    - SystemMonitor の check_once を定期実行するポーリングループ、停止フラグを検知して終了。
    - duckdb/SQLite のコネクション確立とクリーンなクローズ処理。

- モジュール・ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) により Windows/Linux/macOS の差を吸収して優先度設定。
    - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity を設定（失敗時は警告でスキップ）。
    - psutil を利用、権限不足や未対応環境では安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates、calc_equal_weights、calc_score_weights を実装（スコアによるソート、スコアが全て 0 の場合のフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap（セクター集中制限の除外ロジック）、calc_regime_multiplier（レジームに応じた乗数）を実装。
  - portfolio.position_sizing:
    - calc_position_sizes（risk_based / equal / score の配分方式、単元株丸め、集約上限スケーリング、cost_buffer を考慮したスケーリングと残余配分ロジック）を実装。

- リサーチ / ファクター計算
  - research.factor_research:
    - DuckDB を使ったファクター計算（モメンタム: 1M/3M/6M/MA200乖離、ボラティリティ: ATR20、流動性指標等）。
    - SQL ウィンドウ関数を使い、データ不足時に None を返す設計。

- ツール
  - tools.paper_verification_report:
    - ペーパートレード用 SQLite を読み、稼働率・注文成功率・送信率・P95 レイテンシなどの指標を集計してレポートを出力。
    - 判定基準（稼働率 >= 99%、成立率 >= 90% 等）を定義し、PASS/FAIL を報告。
    - 日付フィルタ、P95 計算、欠損データに対する安全なフォールバックを実装。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの作成を保証（冪等）。

### Changed
- （初回リリース）設計上の注意やデフォルトを明示的に設定:
  - run_monitoring と run_execution でプロセス優先度を起動直後に設定するように統一。
  - .env 書き込みテンプレートに注意書き（.env を絶対に Git にコミットしないこと）を追加。

### Fixed
- レジーム乗数や配分ロジックに関するフォールバックの明確化:
  - calc_score_weights が全スコア 0 の場合に等配分へフォールバックして警告を出す。
  - calc_regime_multiplier が未知レジームを受けた場合に警告を出して 1.0 でフォールバック。
- 環境変数の不正値（MONITOR_POLL_INTERVAL 等）に対する安全なフォールバック（ログ出力）を実装。

### Security
- シークレット項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / LINE_CHANNEL_ACCESS_TOKEN）を .env ウィザードでマスク表示。
- .env の生成テンプレートで「Git にコミットしない」旨を明示。

### Notes / Implementation details
- 外部依存:
  - psutil（プロセス優先度 / CPU affinity）。
  - duckdb（リサーチ / 分析）。
  - PyYAML は任意（validate_config で YAML 検証を行う場合に必要、未インストール時はスキップして警告）。
- ロギングは基本 INFO レベルで初期化され、各モジュールで適切にログ出力（debug/info/warning/exception）を行う。
- 停止制御はファイルフラグ（data/stop_requested.flag, data/kill.flag）を使う設計。KILL_FLAG_CLEAR_ON_START による挙動変更あり。
- paper_trading モードでは本番 DB とデータを分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。

---

今後のリリース案:
- エラーハンドリングとリトライロジックの強化（ブローカー API 呼び出し周り）。
- 単元株情報などのマスタデータを使った lot_size の銘柄別対応。
- モニタリング / レポートの自動化（定期ジョブ化）とアラート送信連携（LINE など）。