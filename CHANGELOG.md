# CHANGELOG

すべての変更は "Keep a Changelog" のフォーマットに従って記載されています。  
日付はコードベースから推測可能な最終更新日を使用しています。

## [0.1.0] - 2026-04-19

概要: 初期公開リリース相当。自動売買システム KabuSys の基盤機能（設定管理、起動スクリプト、ロギング、プロセス制御、ポートフォリオ構築ロジック、ポジションサイジング、リスク調整、ペーパートレード検証ツール、ファクター計算ユーティリティなど）を実装。

### Added
- 全体
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータ保存・分析基盤の導入（設定経由でパスを指定可能）。
  - 起動スクリプトおよびデーモン的なループ実行の仕組みを実装（停止フラグ / PID ファイル対応）。

- 設定・環境管理
  - Settings クラスにより環境変数をラップして公開（J-Quants / kabuステーション / LINE / DB / 監視閾値等）。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - .env 読み込みの堅牢化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いを実装。
    - override / protected オプションにより OS 環境変数の保護を実現。
  - paper trading 用設定:
    - PAPER_FILL_MODE（instant/partial/never/reject）を検証するプロパティを追加。
    - PAPER_TRADING_SQLITE_PATH を使ったペーパートレード専用 DB をサポート。

- 起動・管理用 CLI / スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時に専用 DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - エンジンを別スレッドで実行し、data/stop_requested.flag を検出して安全停止。
    - execution.pid を使用した PID ファイル管理のサポート。
    - リスク管理のデフォルト設定（max_position_pct 等）をコード内で定義。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0以下はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - data/stop_requested.flag によるループ停止検知、例外時ログ出力とポーリング継続（堅牢化）。
  - validate_config.py
    - 起動前の設定検証 CLI を実装（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py
    - 対話式 .env 設定ウィザードを実装（.env の読み込み・更新、シークレット項目マスク表示、保存前の確認）。

- ロギング・プロセスユーティリティ
  - utils.logging_setup
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定する共通ユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をフォールバックで無効化し、コンソール出力のみで継続。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。
  - utils.process_priority
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収するプロセス優先度設定機能を追加（psutil ベース）。アクセス権限エラー等は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（存在しない環境では警告を出してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - シグナルの候補選定（select_candidates）: スコア降順・タイブレークに signal_rank を使用。
    - 等配分 / スコア加重配分（calc_equal_weights, calc_score_weights）。スコア総和が0のとき等配分にフォールバック。
  - portfolio.risk_adjustment
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 フォールバック）。
  - portfolio.position_sizing
    - ポジションサイズ計算 calc_position_sizes を実装。
    - allocation_method による分岐（risk_based / equal / score）をサポート。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer を考慮した安全なスケーリングと残差分配ロジックを実装。
    - 価格欠損時のスキップやログ出力を実装。

- リサーチ・ファクター計算
  - research.factor_research（実装開始）
    - Momentum ファクター計算群のスケルトン実装（momentum 指標、MA200 乖離、ATR, ボラティリティ等に対応予定）。
    - DuckDB 接続を受け取り prices_daily テーブルを参照する設計（外部 API 無し、純粋な DB 参照処理）。

- ペーパートレード関連ツール
  - tools.paper_verification_report
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計してレポート出力する CLI を追加。
    - Pass/Fail 基準を定義（稼働率 >= 99% 等）、日付フィルタ（--from/--to）と DB パスオプション（--db）をサポート。
    - P95 計算、NULL（データなし）ハンドリング、SQL 実行時の OperationalError に対するフォールバックを実装。

### Changed
- （初期リリースのため無し） — 基本的に新規実装が中心。

### Fixed
- （初期リリースのため無し） — ただし各モジュールで入力検証や例外ハンドリングを強化。

### Notes / 実装上の注意
- 設計方針として、ポートフォリオ構築／ポジションサイジング／リスク調整の関数群は「純粋関数（副作用なし）」として実装されており、ユニットテストが容易な構成になっています。
- run_monitoring は説明のとおり「監視は環境にかかわらず本番 sqlite_path を使用する」実装です。環境による DB 分離が必要な場合は設定の見直しが必要です。
- process_priority / cpu_affinity の適用は実行環境の権限に依存し、失敗時は警告ログを出して継続する振る舞いです。
- research.factor_research はファイル末尾が途中で切れている可能性があるため、完全な指標群の実装・テストは別途必要です。

### Security
- .env は絶対に VCS にコミットしない旨を config_setup.py のヘッダに明記しています。
- 必須機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings._require により未設定時に起動時エラーを出す設計です。

---

将来的なリリースでは、以下の改善が想定されます:
- research モジュールの完全実装（各ファクターの SQL / 正規化パイプライン）。
- ExecutionEngine / SystemMonitor の詳細なログとメトリクス拡充、監視アラート送信（LINE 等）。
- 銘柄別単元 (lot_size) のマスタ導入とポジションサイジングの拡張。
- テストカバレッジ強化と CI ワークフローの整備。