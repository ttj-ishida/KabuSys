# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠しています。  
慣例に従い、重大なリリース・機能追加・運用改善を分類して記載します。

- リリース日はリポジトリ内のコード（参照日時）に基づいています。
- 記載内容はソースコードから推測してまとめたもので、実際のコミット履歴とは必ずしも完全に一致しません。

続きを読む: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-04-18

初回公開リリース。日本株自動売買システム「KabuSys」の基本機能群と運用ユーティリティを実装しています。主な追加点は以下のとおりです。

### Added
- コアランタイム・起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の管理。停止フラグ検知時に安全に停止処理を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は実行環境に関わらず本番用の sqlite_path を使用して監視データを記録。
    - stop フラグ検知でループを終了し、リソース（DB 接続など）をクリーンにクローズ。

- 設定・環境変数管理
  - kabusys.config.Settings
    - .env ファイルと環境変数から設定を読み込むラッパー。
    - 自動ロード順序: OS 環境変数 > .env.local > .env（プロジェクトルート自動検出、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 各種設定プロパティ（DB パス、ログレベル、Kill Switch 関連、閾値など）を提供。値検証（例: KABUSYS_ENV の有効値チェック、PAPER_FILL_MODE の検証）を行う。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI。
    - シークレット入力、選択肢、既存 .env の読み込み・再利用、確認プロンプト、書き込み機能を提供。

- 設定検証ツール
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス存在チェック（親ディレクトリの存在確認）を実施。
    - PyYAML がない場合は YAML 検証をスキップして警告出力。
    - `--strict` オプションで警告も失敗扱い（exit code 1）にできる。

- ロギング／運用ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定。StreamHandler（stdout） + TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することで cron/タスクスケジューラからの利用を想定。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティ。
    - Windows と POSIX 系（Linux/Mac/FreeBSD）での差分を吸収。権限や未対応環境では警告を出してスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソート（score 降順、タイブレークに signal_rank）と候補選定。
    - 等配分・スコア加重配分の重み計算（スコア全て 0 の場合は等分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）。既存保有のセクター別比率が閾値を超える場合に当該セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未知レジームは警告のうえフォールバック値を使用。
  - portfolio/position_sizing.py
    - 株数決定ロジック（risk_based / equal / score をサポート）。
    - 単元株丸め（lot_size）、per-stock 上限・aggregate cap、cost_buffer を加味したスケールダウン、端数処理を実装。

- リサーチ / ファクター計算（初期実装）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算方針と初期定数を追加。DuckDB を使って prices_daily / raw_financials を参照する設計。
    - （ファイル途中までの実装が含まれるため、今後計算ロジックを拡張予定）

- 運用ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成ツール。
    - PAPER_TRADING_SQLITE_PATH（または --db オプション）に接続し、稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を出力。
    - 既定の合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）を設定。
    - データ不足やテーブル未存在時に N/A/0 を扱うフォールバックを備える。

- DB / 分析基盤
  - DuckDB と SQLite の併用を想定した設計（Settings でパス指定、起動時に duckdb/ sqlite 接続を行う）。monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - paper_trading 環境では専用 SQLite を使用して分析・検証データを本番 DB から分離。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- run_monitoring / _get_poll_interval における不正な環境変数値のハンドリングを実装（不正値で ValueError にならないよう警告してデフォルトにフォールバック）。
- ロギング設定で既存ハンドラの二重登録を防ぐため、再設定時に既存ハンドラを flush/close して削除する挙動を導入。

### Security
- .env ファイルが初期化ウィザードで生成されることを明示し、.env を誤ってコミットしないよう注意喚起を出力。
- 必須の機密情報（J-Quants トークン、kabu API パスワード）は Settings で未設定時に明示的なエラーを出す（起動前に気付けるように設計）。

---

将来の改訂で記載する可能性のある事項:
- ExecutionEngine / SystemMonitor の詳細な監視項目やリスク管理ロジックの拡張
- research/factor_research の完全実装（各ファクター計算）
- 単体テスト、CI ワークフロー、ドキュメント（API・設定例）の追加

もし CHANGELOG に特定のコミットや実装者情報、より詳細な日付・リンクを含めたい場合は、該当情報を提供してください。コード差分から推測した内容なので、補足・修正をご希望であればお知らせください。