# Changelog

すべての注記は「Keep a Changelog」フォーマットに準拠しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションとツール群を初回リリース。
  - パッケージ名: KabuSys — 日本株自動売買システム（src/kabusys）。
  - バージョン: 0.1.0

- 起動スクリプト / ランナー
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV による paper_trading モード対応:
      - paper_trading 時は MockBrokerClient を使用（BrokerClientFactory により生成）。
      - SQLite は paper_trading 用 DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 起動前に stop flag（data/stop_requested.flag）を確認し、既に立っている場合は起動しない。
    - 実行時は別スレッドで engine.run_session を実行し、停止フラグを検知すると engine.stop() で終了を指示。
    - PID ファイル管理（data/execution.pid）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト: 60 秒）。
    - 停止フラグ(data/stop_requested.flag) による安全停止。
    - 監視は設定にかかわらず本番の sqlite_path を使用する挙動（設計上の挙動として明記）。

- 設定・起動補助
  - config.py
    - .env 自動ロード機能（プロジェクトルートの .env / .env.local を読み込む。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 環境変数の取得ユーティリティ（必須チェック _require 等）。
    - 各種設定プロパティ（DB パス、PID ファイル、閾値、env 判定、paper_trading 設定等）を提供。
    - PAPER_FILL_MODE の検証（有効値: instant / partial / never / reject）。
  - config_setup.py
    - 対話式 .env 作成ウィザードを提供（既存 .env の読み込み・更新に対応）。
    - 出力時に .env を上書き保存するユーティリティを実装。
  - validate_config.py
    - 起動前設定検証 CLI（必須環境変数の有無、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース（PyYAML が存在する場合）など）。
    - --strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N を選択（タイブレークに signal_rank を使用）。
    - calc_equal_weights: 等金額ウェイトを計算。
    - calc_score_weights: スコア比率で正規化。全スコアが 0 の場合は等金額にフォールバックし警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を考慮して候補を除外するフィルタリング。
      - sell_codes を渡して当日売却予定銘柄を除外しつつ算出可能。
      - "unknown" セクターは上限適用を行わない。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear -> 1.0/0.7/0.3、未知レジームは 1.0 にフォールバックし警告）。
  - portfolio.position_sizing
    - calc_position_sizes: 各種配分方式（risk_based / equal / score）に基づいた株数計算。
      - 単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）によるスケーリング、cost_buffer を使った保守的見積もり。
      - 利用可能現金不足時のスケーリングと残余キャッシュの再配分ロジックを実装。

- ユーティリティ
  - utils.logging_setup
    - 共通ロギング初期化ユーティリティを提供（StreamHandler -> stdout、TimedRotatingFileHandler 日次ローテート、30 日保持）。
    - ログディレクトリの自動作成と、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数(LOG_LEVEL) > デフォルト(INFO)。
  - utils.process_priority
    - プロセス優先度設定（Windows と POSIX を吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップ。

- 監視・DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して監視用テーブルの冪等初期化を行う（run_monitoring / run_execution で呼び出し）。

- Paper Trading 検証ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite のログを集計してレポートを標準出力生成。
    - 指標: 稼働率（uptime）、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ等。
    - 判定用閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - コマンドライン引数 --from / --to / --db に対応。
    - DB が欠けるテーブル（OperationalError）の場合は該当指標を N/A 扱いで耐障害性を確保。

- 研究用ファクター計算（research）
  - research.factor_research（骨格実装）
    - モメンタム等のファクター計算を行う意図で設計（DuckDB 経由で prices_daily / raw_financials を参照）。
    - 定数と関数シグネチャが用意され、モメンタム計算の実装が開始されている（calc_momentum 等）。
    - 設計方針として外部 API に依存せず、DuckDB + SQL/Python による完結計算を想定。

### Changed
- なし（初回リリースのため）

### Fixed
- なし（初回リリースのため）

### Removed
- なし（初回リリースのため）

### Security
- なし特記。ただし .env は絶対に Git にコミットしないよう README と .env 作成ロジックで注意喚起。

### Notes / Known limitations
- research.factor_research.calc_momentum はファイル終端で実装が途中に見える（スナップショットの都合か部分実装）。完全なファクター計算の実装は今後の作業項目。
- run_monitoring はドキュメントに「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明記されているため、誤って本番 DB に対して監視処理を行わないようデプロイ時の注意が必要。
- process_priority や CPU affinity 設定はプラットフォーム依存や権限により失敗する可能性があり、その場合は警告ログを出してスキップする設計。
- position_sizing の単元丸めや価格欠損時の処理（price が 0.0 の場合のフォールバック等）については TODO コメントが残っており、将来的な改善余地あり。

---

上記はリポジトリに含まれるソースコードの構成とドキュメント文字列から推測した変更履歴です。必要であれば各機能ごとにさらに詳細な変更点（関数仕様、例、利用方法）を追記できます。