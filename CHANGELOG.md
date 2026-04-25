# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、コードベース（src/ 以下）から推測される機能追加・改善点・修正点に基づいて作成されています。

※ バージョンや日付はコード内の __version__ や現在の推測に基づいています。

## [Unreleased]

### Added
- なし

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-25

初回リリース相当の機能セットを実装。日本株自動売買フレームワークのコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定周りの CLI、ペーパートレード検証ツール等を含む。

### Added
- 全体
  - パッケージ基底: kabusys メインパッケージを導入。__version__ = 0.1.0。
  - DuckDB / SQLite を併用する構成をサポート（設定経由でファイルパス指定）。
  - プロジェクトルート自動検出ロジックを実装し、.env 自動ロード（.env / .env.local）をサポート（KABUSYS_DISABLE_AUTO_ENV_LOAD により抑制可能）。
- 設定・環境管理
  - Settings クラスを実装し、環境変数から各種設定値（API トークン、DB パス、閾値、環境種別など）を取得できるようにした。
  - .env ファイルの対話式生成・更新ウィザード（kabusys.config_setup）を提供。必須項目やデフォルト値、シークレット入力等を案内。
  - 設定検証 CLI（kabusys.validate_config）を実装。必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）を実行。--strict オプションで警告を失敗扱いにできる。
- 起動スクリプト / ランタイム
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視側は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用して監視データを記録。
    - 停止フラグファイル (data/stop_requested.flag) の存在を監視して安全に終了。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trade SQLite DB（data/paper_trading.db をデフォルト）および MockBrokerClient を使用し、本番 DB と完全分離。
    - エンジン用 PID ファイル管理、停止フラグ検知で安全停止。
    - ExecutionEngine は別スレッドで run_session を実行し、メインループでフラグ監視・停止制御を行う。
- ロギング・プロセス管理
  - 統一ロギング初期化ユーティリティ (kabusys.utils.logging_setup.setup_logging) を実装。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続。
    - ログレベル・ログディレクトリは引数、環境変数、デフォルトの優先順で解決。
  - プロセス優先度 / CPU アフィニティユーティリティ (kabusys.utils.process_priority) を追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）に跨る優先度設定を抽象化。アクセス権限や未対応環境では警告を出してスキップ。
    - CPU affinity を最初 N コアにピン留めする set_cpu_affinity を提供（未指定なら全コア）。
  - run_* スクリプトは起動直後にプロセス優先度を "high" に設定するよう変更。
- 監視・監査
  - 監視 DB 初期化ユーティリティ init_monitoring_db を呼び出して、監視用テーブルの存在を保証（冪等）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順、signal_rank をタイブレークにして候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限の適用。既存保有を基にセクター比率が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告の上で 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を計算。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）、cost_buffer（手数料・スリッページ想定）を実装。
      - risk_based 方式ではリスク許容率、ストップロスを用いて個別ロットを計算。
- 研究（リサーチ）
  - research.factor_research の骨格を実装。DuckDB を用いて momentum / value / volatility / liquidity 等を計算する設計（関数 calc_momentum などの導入）。
- ツール
  - tools.paper_verification_report: ペーパートレード用の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH 環境変数（または --db オプション）で DB を指定可能。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）を集計。
    - PASS/FAIL 判定基準を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms 等）。
- 監査ログ / 取引ログ構造を前提としたクエリ関数を実装（system_status, trade_logs, risk_logs などを参照）。

### Changed
- 環境変数・設定読み込み
  - .env のパース実装を強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮。
    - クォートなし値のインラインコメント認識（'#' の前にスペース/タブがある場合のみコメントと判断）。
- ロギング
  - StreamHandler を stdout にして標準出力へ出すことで cron / scheduler 環境での取り扱いを考慮。
- run_monitoring のデフォルト挙動
  - モニタリングは KABUSYS_ENV に依存せず本番用 sqlite_path を使用する設計とした（監視データが常に一箇所に集約されることを重視）。
- run_execution の DB 分離
  - paper_trading モードでは paper_sqlite_path を使用し、本番監視 DB と分離して記録する（テスト/検証の安全性向上）。

### Fixed
- .env 読み込み時のファイルアクセスエラーを捕捉し警告を出すようにした（読み込み失敗時は自動ロードをスキップ）。
- init_monitoring_db を各起動時に呼ぶことで監視用テーブルが存在しない場合のクラッシュを回避（冪等に初期化）。
- MONITOR_POLL_INTERVAL の不正な値（0 以下や文字列）を検出してデフォルト値にフォールバックし、警告を出力するようにした（time.sleep への不正な値渡しを防止）。
- process_priority / cpu_affinity の設定で権限不足・未対応環境発生時に例外を殺して警告に置き換えるようにして堅牢化。

### Security
- .env を生成する config_setup は .env を絶対にコミットしない旨の注意を書き出す（README 相当のヘッダーを .env に付与）。

### Internal
- 各コンポーネント（ExecutionEngine, SystemMonitor, BrokerClientFactory, OrderManager, RiskManager, Reconciler 等）はモジュール分割されており、run_* スクリプトはそれらを組み立てて起動する責務のみを持つ設計。
- DuckDB/SQLite 接続は起動時に生成し、正常終了時に確実にクローズする実装。
- ロギング設定は重複ハンドラの登録を避けるため、既存ハンドラを flush/close してから再設定する。

---

## 今後の注記（推測）
- research.factor_research の実装は続きがあるように見える（calc_momentum の途中でファイルが切れている）。今後のリリースでファクター群の完全実装・正規化処理（Zスコア等）の追加が期待される。
- Strategy / Execution 関連のユニットテストやエンドツーエンドの検証ツール、さらなる監視アラートの強化（LINE 通知等の連携強化）が今後の課題として想定される。

---

参考: 本 CHANGELOG はソースコード（src/ 以下）の実装・コメント・命名規約から推測して作成しています。実際のコミット単位やリリースポリシーに合わせて適宜調整してください。