# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
慣例: 重要な変更は大きな見出し、カテゴリは Added / Changed / Fixed / Removed / Security などに分けています。

全般的な注記:
- 本リリースはパッケージの最初の公開バージョンです。バージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に対応します。

## [0.1.0] - 2026-04-21

### Added
- 全体
  - 初期バージョンをリリース。
  - パッケージのエントリポイントと基本的なユーティリティ群を実装。

- 起動スクリプト / 実行関連
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離して動作。
    - ブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、ExecutionEngine の起動・停止監視（stop flag による停止）を実装。
    - エンジンは別スレッドで実行し、停止フラグ検知時に安全に停止処理を実行。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - PID ファイル指定対応。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値の場合はデフォルトにフォールバックし警告を出力する。
    - 監視モジュールは KABUSYS_ENV にかかわらず本番向けの sqlite_path を使用する（監視 DB は単一管理）。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定 / 環境変数管理
  - config.Settings クラスを実装。
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL、しきい値など）をラップして提供。入力値の妥当性チェックを行う（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV の検証など）。
    - settings = Settings() の単一インスタンスをエクスポート。

  - config_setup: 対話式の .env 生成ウィザードを追加。
    - 対話形式で主要な環境変数を設定、既存 .env の読み込み・再利用、シークレット項目はマスク表示。
    - 生成された .env のテンプレートと書き込みロジックを提供。

  - validate_config: 設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DuckDB/SQLite パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードチェック（LINE 設定など）を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: 統一されたログ設定ユーティリティを追加。
    - stdout 出力用の StreamHandler と、日次ローテーション（TimedRotatingFileHandler）によるファイル出力を設定。
    - LOG_DIR / LOG_LEVEL の環境変数、引数による上書きをサポート。ログディレクトリ作成に失敗した場合はファイル出力のみをスキップして stdout のみで継続。
    - root ロガーの既存ハンドラを安全にクローズして再設定する実装。

  - utils.process_priority: プロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収。psutil を利用して nice / priority class を設定。権限不足などで設定できない場合は警告を出してスキップ。
    - set_cpu_affinity() により最初の N コアにピン留め可能（未指定時は何もしない）。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補抽出。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。

  - portfolio.risk_adjustment
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合に当該セクターの新規候補を除外。'unknown' セクターは除外対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告を出して 1.0 にフォールバック。

  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算を実装。
      - lot_size（単元）で丸め、price の欠損・0 対応、per-stock 上限・aggregate 上限の両方を考慮。
      - cost_buffer（スリッページ・手数料の見積り）を考慮した保守的なコスト計算。
      - aggregate が available_cash を超える場合はスケーリング処理を行い、残余キャッシュを fractional remainder の大小で追加配分する安全弁ロジックを実装。

- ツール
  - tools.paper_verification_report: ペーパートレードの検証レポート生成スクリプトを追加。
    - SQLite（デフォルト: data/paper_trading.db）から system_status / trade_logs / risk_logs 等を集計し、稼働率（uptime）、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出。
    - デフォルトの合格基準（稼働率 >= 99% 等）を定義し、PASS/FAIL の判定を出力。
    - DB やテーブルが存在しない場合でも欠損値は N/A として堅牢に動作。

- リサーチ
  - research.factor_research: ファクター計算モジュールを追加（モメンタム等を想定した実装の開始）。
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照して各種ファクターを計算する設計（モメンタム計算の骨組みを含むが、ファイル末尾で未完の箇所あり）。

### Changed
- 環境変数の自動読み込み順序を明確化:
  - OS 環境変数 > .env.local > .env の優先順位で読み込み。OS 環境変数は保護され、.env/*.local による上書きから除外される。

- ログ出力挙動:
  - ログは stdout に出力するように統一（cron / Task Scheduler での扱いを考慮）。ファイル出力はログディレクトリが作成できない場合にフォールバック。

### Fixed
- MONITOR_POLL_INTERVAL の不正な値（ゼロや負数、文字列など）に起因する time.sleep の ValueError 発生を防ぐため、不正値はデフォルト（60秒）にフォールバックして警告を出力するように修正。

- run_execution:
  - paper_trading 環境では専用の SQLite を使用するように確実に分離（settings.is_paper による判定）。

### Notes / Known issues
- research.factor_research モジュールの末尾が未完（ファイルの最後で途中で切れている箇所が存在）。モメンタム計算の詳細実装を完了させる必要があります。
- position_sizing の _max_per_stock で price が欠損（0.0）の場合 0 を返す実装になっており、将来的に価格フォールバック（前日終値や取得原価など）を導入する余地あり（TODO コメントあり）。
- apply_sector_cap は "unknown" セクターを制限対象外としている点に注意（設計上の選択）。

---

今後のリリースでは以下を予定しています:
- research.factor_research の完成、Strategy/Signal 生成パイプラインとの統合。
- テストカバレッジの追加（特に資金配分・スケーリングロジック）。
- 起動スクリプトのユニット／統合テストとデプロイ手順の整備。