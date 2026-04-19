CHANGELOG.md

すべての重要な変更点をこのファイルに記載します。フォーマットは「Keep a Changelog」準拠です。
リリース日: 2026-04-19

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、専用の SQLite（デフォルト: data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（監視データの一元化）。
    - 停止フラグ (data/stop_requested.flag) によりループを終了。

- 設定管理関連
  - config.py
    - .env / .env.local の自動読み込み機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD 非依存で動作。
    - .env の行パースロジック（クォート/エスケープ/コメント処理）を実装。
    - Settings クラスを導入し、各種環境設定（DB パス、API トークン、監視しきい値、PAPER_FILL_MODE の検証等）をプロパティで取得可能に。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 各設定項目の説明、既存値の再利用、シークレットマスク表示、最終確認と保存を提供。
    - .env 作成時にコミット禁止の注意喚起を出力。
  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース（PyYAML がある場合）を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合に等金額配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（sell_codes を除外、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）および残差処理を実装。
    - cost_buffer による保守的見積りに対応。

- ログ・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力（logs/<app_name>.log）を設定。既存ハンドラをクリアして重複設定を防止。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定（Windows の優先度クラス、POSIX の nice 値）を追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - アクセス権限不足や未対応 OS の場合は警告を出してスキップ。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から統計を集計し、検証レポートを生成するスクリプトを追加。
    - システム稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）などを算出。
    - デフォルトの判定基準（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）を定義し PASS/FAIL を出力。
    - 日付範囲指定 (--from / --to) と DB パス上書き (--db) サポート。
    - P95 の計算実装、欠損データのハンドリングを行う。

- 研究用モジュール（未完の計算ロジック含む）
  - research/factor_research.py
    - ファクター計算基盤（モメンタム／ボラティリティ等）用のモジュールを追加。DuckDB 接続を受け prices_daily / raw_financials を参照して計算を行う設計。
    - calc_momentum の雛形と定数を実装（関数は途中までの実装で続きが必要）。

- パッケージ情報
  - __init__.py にてパッケージバージョンを "0.1.0" に設定。

### 変更 (Changed)
- データベースの取り扱い方針
  - 監視（run_monitoring）は環境（development/paper_trading/live）に依存せず本番 sqlite_path を用いる方針とした（監視データの一元化）。
  - 実行エンジン（run_execution）は paper_trading 環境時に専用の paper_sqlite_path を使用して発注記録を本番 DB と分離。

- ログ出力の既定
  - ログのコンソール出力は stderr ではなく stdout を用いる（cron / Task Scheduler などで stdout/stderr を一本化してリダイレクトする運用を想定）。

- 設定自動ロードの優先度
  - 自動 .env 読み込み順を OS 環境変数 > .env.local > .env とし、既存 OS 環境変数を保護する仕組みを実装。

### 修正 (Fixed)
- 不正な MONITOR_POLL_INTERVAL の扱い
  - 非整数または 0 以下の値が設定された場合に警告してデフォルト (60 秒) にフォールバックするようにした（time.sleep に渡したときの ValueError を回避）。

### 注意事項 (Notes)
- research/factor_research.calc_momentum はファイル末尾で途中（実装未完）に終わっているため、完全なファクター計算には追加実装が必要です。
- config_setup によって生成される .env は機密情報を含むため、絶対に Git 等のバージョン管理にコミットしないでください（ファイル上部に注意文を出力）。
- 一部機能は外部パッケージ（psutil, duckdb, PyYAML 等）に依存します。これらが存在しない環境では該当機能が制限されます（validate_config は PyYAML が無ければ YAML 検証をスキップする等）。

### 既知の制限 (Known issues)
- position_sizing の将来的拡張として銘柄ごとの lot_size をサポートする TODO が残っています（現状は全銘柄共通の lot_size を仮定）。
- apply_sector_cap のエクスポージャー計算は price_map に 0.0 が含まれると過小評価になる可能性があり、フォールバック価格の導入を検討する必要があります。

---

今後のリリースでは research モジュールの完成、ExecutionEngine / BrokerClient の詳細実装、テストカバレッジ拡充、およびドキュメント整備を予定しています。