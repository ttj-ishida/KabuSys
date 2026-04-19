# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

全般:
- このリポジトリは Semantic Versioning を採用します。
- バージョンはパッケージ定義 (kabusys.__version__) に合わせて記載しています。

## [0.1.0] - 2026-04-19

### Added
- パッケージ基本構成
  - パッケージ初期リリース。バージョンは `0.1.0` に設定。

- 実行／監視用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境に応じて本番用 SQLite（`SQLITE_PATH`）またはペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用して本番 DB と分離。
    - DuckDB 接続を作成し、監視用テーブルの初期化を行う。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動処理を実装。
    - 停止フラグファイル（data/stop_requested.flag）検出で安全に停止する制御を実装。
  - run_monitoring.py
    - SystemMonitor ポーリングループを起動するエントリポイントを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告を出しデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 `sqlite_path` を使用する（監視データは共有する設計）。
    - プロセス優先度設定、SQLite と DuckDB の接続、SystemMonitor の単回チェック `check_once()` をループで実行。例外はログ出力して次サイクルへ継続。

- 設定管理
  - config.py
    - 環境変数・Settings クラスを実装。プロパティベースで必要な設定を取得・検証する。
    - 自動 .env ロード機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。
    - .env 読み込みは OS 環境変数を保護しつつ `.env` → `.env.local` の順で適切に上書き処理を行う。
    - .env の行パーサを実装（export 句、クォート内エスケープ、インラインコメント処理などに対応）。
    - 設定値検証: `KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE`（有効値チェック）など。
    - 各種パス（DUCKDB, SQLITE, PAPER_TRADING_SQLITE_PATH, PID_FILE 等）を Path 型で提供。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 項目定義（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DB パス、LINE 通知設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を持ち、既存 .env の読み込みとマスク表示を行う。
    - 入力結果を .env に書き込み、保存前に確認プロンプトを提示。

  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在および PyYAML があればパース検証を行う。
    - `--strict` オプションで警告も失敗（exit 1）として扱うモードを提供。
    - 本番環境向け（KABUSYS_ENV=live）の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全アプリケーションで共通利用するログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリ解決順をサポートし、ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する堅牢設計。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。
    - `set_process_priority(level: "high" | "normal" | "low")` と `set_cpu_affinity(cpu_count)` を提供。
    - psutil ベースでアクセス権限エラーなどをハンドリングし、失敗時は警告ログを出力して続行。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全てが 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションと価格マップからセクターエクスポージャーを算出し、上限超過セクターの新規候補を除外する。
    - 市場レジームに基づく乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes を実装（allocation_method = "risk_based" / "equal" / "score" をサポート）。
    - 単元（lot_size）丸め、個別上限（max_position_pct）、aggregate cap（available_cash）に応じたスケールダウン、コストバッファ（cost_buffer）を考慮した安全弁ロジックを実装。
    - 価格欠損時のスキップ、残余キャッシュを用いたロット単位の再配分アルゴリズムを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から集計して検証レポートを生成するスクリプトを追加。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を計算し閾値で Pass/Fail 判定を行う。
    - P95 計算、日付フィルタ（--from / --to）対応、DB が存在しない場合のエラーメッセージを実装。
    - デフォルトの閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。

- Research / ファクター計算（骨組み）
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算モジュールの骨組みと定数を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを用いる設計（外部 API を呼ばない）。
    - calc_momentum の計算ロジックおよび期間定数（1M/3M/6M、MA200、ATR 等）の定義を含む初期実装（以降の完全実装へ拡張予定）。

- パッケージ初期エクスポート
  - kabusys.__init__.py に __version__ を追加（"0.1.0"）し、主要パッケージ名を __all__ で公開。

### Changed
- (初回リリースにつき該当なし)

### Fixed
- (初回リリースにつき該当なし)

### Security
- (初回リリースにつき該当なし)

### Notes / Implementation details
- .env 自動ロードはプロジェクトルートの検出に成功した場合のみ行われ、CWD に依存しない動作を目指している。
- 環境変数の読み込みでは OS 環境変数が保護され、必要に応じて .env.local で上書き可能。
- 各 CLI（config_setup、validate_config、paper_verification_report、run_execution、run_monitoring）はそれぞれ main ガードで直接実行可能な設計。
- Logging やプロセス優先度設定は起動スクリプトの冒頭で設定することを想定し、アプリケーション全体で一貫した動作を提供する。

---

今後の予定（例）
- factor_research のファクター計算ロジックを完成させる。
- テストカバレッジの追加（ユニットテスト、統合テスト）。
- 実行時メトリクス収集の拡張、アラート（LINE 等）送信の統合テスト。

（この CHANGELOG はソースコードから推測して作成しています。実運用向けには開発履歴やコミットメッセージに基づく追記を推奨します。）