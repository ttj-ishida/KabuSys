# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
初回リリースとして、コードベースの内容から推測した機能追加・設計意図・既知の注意点をまとめています。

全般
- バージョン: 0.1.0
- 日付: 2026-04-18

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py: 実行エンジン (ExecutionEngine) を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いて実行時に適切なブローカークライアント（Mock を含む）を生成。
    - 実行エンジンはデーモンスレッドで run_session を実行し、data/stop_requested.flag を監視して安全に停止可能。
    - 実行 PID を data/execution.pid に記録するための pid_file のサポート。
  - run_monitoring.py: システム監視プロセス (SystemMonitor) のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - data/stop_requested.flag による外部停止フラグの監視。
    - プロセス優先度を起動直後に set_process_priority("high") で設定。

- 設定管理とユーティリティ
  - config.py: Settings クラスを導入し、環境変数／.env ファイルからの設定取得を一元化。
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 多数のプロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL、監視しきい値など）。
    - settings = Settings() として単一インスタンスを公開。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 複数キー（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL 等）を対話的に設定可能。
    - シークレット項目はマスク表示、既存の .env を読み込んで Enter で再利用可能。
    - 保存時にテンプレートヘッダ付きで .env を出力。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の有無チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML がインストールされている場合のみ）などを検証。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 本番環境 (KABUSYS_ENV=live) 向けの追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性など）を実装。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder.py: 銘柄候補選定と重み計算の純粋関数を追加
    - select_candidates: スコア降順、同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（スコア全て 0 の場合は等金額にフォールバック）。
  - risk_adjustment.py: セクター集中制限とレジーム乗数を追加
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数 (bull/neutral/bear) を返す。未知のレジームは警告して 1.0 をフォールバック。
  - position_sizing.py: 株数決定ロジックを追加
    - allocation_method("risk_based" / "equal" / "score") に応じた株数算出。
    - 1 銘柄上限、aggregate cap、単元 (lot_size) による丸め、スケールダウンと残差処理を実装。
    - cost_buffer により保守的なコスト見積りをサポート。

- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加
    - コンソール出力 (stdout) と TimedRotatingFileHandler（日次ローテーション、バックアップ 30 日）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する実装。
    - set_process_priority(level: "high"|"normal"|"low")
    - set_cpu_affinity(cpu_count: int | None)
    - 権限不足や未対応 OS では警告を出してスキップ。

- モニタリング DB 初期化ヘルパー（init_monitoring_db）と SystemMonitor（監視ロジック）は run_* スクリプトから利用されるように組み込み。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加
    - PAPER_TRADING_SQLITE_PATH（または --db）から DB を読み、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出してレポート出力。
    - 既定の合格閾値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）に基づき PASS/FAIL を判定。
    - 日付フィルタ (--from / --to) に対応。DB が存在しない場合のエラーメッセージを実装。

- 研究用モジュール
  - research/factor_research.py: ファクター計算の基盤を追加（Momentum、Value、Volatility、Liquidity の設計方針と計算定数を定義）。
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してファクターを計算する設計。
    - calc_momentum などの関数スケルトンと定数を導入（実装は継続中）。

- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を設定。
  - kabusys.portfolio パッケージの __all__ を公開し、上記関数群をトップレベルインポートで利用可能にした。

### Changed
- 初期リリースのため特別な変更履歴はなし（初版での機能追加が中心）。

### Fixed
- 初期リリースのため特別な修正履歴はなし。

### Removed
- 該当なし。

### Security
- シークレット系（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は .env に保存するよう設計。.env を絶対に Git にコミットしない旨を README／ウィザードで明記。

### Known issues / Notes（既知の注意点）
- sector_exposure の価格取得で price_map に 0.0（欠損）がある場合、エクスポージャーが過少見積りされる可能性がある点は TODO コメントで指摘済み。将来的に前日終値などをフォールバック価格として扱うことを検討。
- position_sizing の将来拡張として銘柄別 lot_size をサポートする旨の TODO がある（現在は全銘柄共通 lot_size を想定）。
- research/factor_research.py は設計と一部関数スケルトンを含むが、完全実装（すべての計算ロジックや SQL）は継続中である可能性が高い（コードが途中で切れているため）。
- run_monitoring.py は監視 DB に環境を問わず本番 sqlite_path を使用するため、開発環境で意図せず本番 DB を触らないよう注意が必要。
- validate_config の YAML パース検証は PyYAML インストールが前提。未インストール時は警告を出して検証をスキップする。
- ログディレクトリ作成に失敗した場合、ファイルハンドラは無効化されコンソールのみで運用される（失敗を検出しログへ警告を出す実装あり）。

---

今後の予定（推奨）
- research モジュールの計算ロジック完成とテスト追加。
- SystemMonitor / ExecutionEngine / BrokerClient の統合テストとエンドツーエンドのペーパートレード検証。
- 銘柄ごとの lot_size を stocks マスタに持たせ、position_sizing を拡張。
- モニタリングと実行のログ・メトリクス収集の自動化（Prometheus / grafana 等の統合）を検討。

以上。必要であれば各ファイルごとのより詳細な変更点や想定ユースケースに基づく「使い方」セクションを追記します。どの程度の詳細が必要か教えてください。