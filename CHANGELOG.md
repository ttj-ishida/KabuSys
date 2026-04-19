# CHANGELOG

このファイルは Keep a Changelog のフォーマットに準拠しています。
https://keepachangelog.com/ja/

すべての変更はリリース単位で記載しています。以下の内容は、コードベース（src/ 配下）の実装内容から推測して作成した初回リリースの変更履歴です。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 実行エントリ/デーモン起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - KABUSYS_ENV により paper_trading モードを判別し、paper_trading 時は専用の SQLite（data/paper_trading.db 既定）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成（paper/live に応じた実装を切り替え）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を起動。デーモン化用スレッドで実行し、停止フラグ（data/stop_requested.flag）を監視して安全に停止。
    - PID ファイルを data/execution.pid に出力する運用を想定。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。

  - run_monitoring.py
    - SystemMonitor（監視ループ）を起動するエントリポイントを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する設計（監視用 DB の一貫性保持）。
    - 停止フラグ（data/stop_requested.flag）を検知してループ終了。KeyboardInterrupt のハンドリングと接続クローズ処理を実装。

- 設定・環境変数管理
  - config.py
    - Settings クラスでアプリケーション設定を集中管理（プロパティ経由で環境変数を取得）。
    - .env 自動読み込み機能を提供（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数を保護する仕組みあり。
    - 必須環境変数取得 (`_require`) とバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - SQLite/DuckDB の既定パス、paper_trading 用 DB パス、PID/kill flag のパス等を管理。

  - config_setup.py（対話式ウィザード）
    - .env の初期作成・更新を支援する CLI ウィザードを追加。
    - J-Quants / Kabu API 等の必須項目やログレベル、DB パス、Kill Switch 設定などを対話的に設定可能。
    - .env の既存値読み込み、シークレット値のマスク表示、保存確認を実装。

  - validate_config.py（検証 CLI）
    - .env と config/*.yaml の設定不備を起動前に検出する検証ツールを追加。
    - 必須環境変数の未設定/プレースホルダ警告、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML があれば）などをチェック。
    - `--strict` を指定すると警告も失敗として exit(1) を返すモードを提供。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等分配へフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装。既存保有のセクター比率が上限を超える場合に新規候補から除外するロジック（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは警告を出して 1.0 にフォールバック。

  - portfolio/position_sizing.py
    - position sizing（発注株数計算）を実装。allocation_method として "risk_based"、"equal"、"score" をサポート。
    - 損切り率・リスク許容率に基づくリスクベース計算、単元（lot_size）丸め、個別上限（max_position_pct）、総投下上限（available_cash による aggregate cap）を反映。
    - 投資合計が利用可能現金を超えた場合はスケールダウンし、残余で端数分を lot_size 単位で再配分するアルゴリズムを実装。
    - cost_buffer による手数料・スリッページの保守的見積もりに対応。
    - 価格欠損時はスキップしてログ出力する仕様。

  - portfolio/__init__.py で上記関数群をエクスポート。

- 監視・ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるロギング初期化ユーティリティを追加。
    - stdout へ出力する StreamHandler と、日次ローテーション（30 日保持）の TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップして stdout のみで動作。
    - ログレベル解決順やログディレクトリ決定ロジックを明確化。

  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac 等）に対応したプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - CPU affinity を最初 N コアにピン留めする set_cpu_affinity を提供。
    - 権限不足や未対応 OS では安全にスキップし、警告を出力する。

- 監視 / DB 初期化
  - monitoring/monitoring_db.py の init_monitoring_db（起動時に監視テーブルを冪等に初期化する呼び出し）が run_monitoring と run_execution の起動フローに組み込まれている（監視テーブルの存在保証）。

- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py
    - Paper Trading データ（SQLite）から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計して検証レポートを出力する CLI を追加。
    - デフォルトの DB パスは data/paper_trading.db。`--db` オプションおよび環境変数 PAPER_TRADING_SQLITE_PATH をサポート。
    - レポートの Pass/Fail 基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を実装。
    - 日付フィルタ（--from / --to）をサポートし、ISO8601 形式で内部フィルタリング。

- 研究用モジュール（骨格）
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum/Value/Volatility/Liquidity 等のファクターを算出する設計（calc_momentum 等）を開始。設計方針と定数が実装されており、prices_daily/raw_financials を前提に SQL+Python で計算することを想定。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Known limitations
- .env 自動読み込みはプロジェクトルートの検出に依存する (.git または pyproject.toml)。プロジェクトルートが見つからない場合は自動ロードをスキップする。
- Paper Trading と本番 DB は明示的に分離されているが、監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する仕様（監視データの一元化を意図）。
- position_sizing の一部ロジックは価格欠損時に単純にスキップし、コメントで将来的なフォールバック価格導入の TODO が残る（price が欠損するとエクスポージャーの過少見積りにつながる可能性あり）。
- calc_regime_multiplier は未知のレジームを 1.0（Bull 相当）でフォールバックする。Bear レジームでの BUY シグナル生成ポリシーはドキュメントに記載されている（戦略側実装と整合）。
- research/factor_research.py はファクター計算の骨格や定数を実装しているが、完全実装には DuckDB 上のテーブル定義／データ供給が必要（未完）。
- ロギング: ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソール出力のみで動作するため、運用環境でのパーミッション設定に注意。

---

この CHANGELOG はコードベースのソース（コメント・関数名・実装内容）から推測して作成したものであり、実際のコミット履歴や設計ノートに基づくものではありません。必要であれば、各モジュール・関数の詳細や既知の TODO を抽出して補足のリリースノートを作成します。