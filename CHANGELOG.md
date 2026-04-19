# CHANGELOG

すべての重要な変更を記録します。本ドキュメントは Keep a Changelog の慣例に準拠します。

フォーマットの説明:
- 各リリースは日付付きの見出しで区切られます。
- セクション: Added / Changed / Fixed / Deprecated / Removed / Security

## [0.1.0] - 2026-04-19
初回公開リリース。

### Added
- 基本パッケージとバージョン管理
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
- 環境設定・管理
  - Settings クラスを実装。環境変数から各種設定（KABUSYS_ENV、データベースパス、ログレベル、各 API トークン／パスワードなど）を取得・バリデート。
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出。.env / .env.local の順で読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env のパースロジックを堅牢化（クォート・エスケープ・インラインコメント対応）。
  - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）。
  - 各種パス・閾値のプロパティ（duckdb/sqlite/paper_trading パス、CPU/メモリ/ディスク閾値、PID/kill flag パス等）。
- 環境セットアップ / 検証 CLI
  - config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加。デフォルト値・選択肢表示・シークレットマスク・保存確認をサポート。
  - validate_config: .env および config/*.yaml の妥当性検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML 未導入時は警告）などを実施。--strict オプションで警告を FAIL 扱いにできる。
- 実行・監視ランチャー
  - run_execution: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動処理を実装。
    - 停止フラグ（data/stop_requested.flag）と実行 PID 管理（data/execution.pid）を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照して初期化。
    - 停止フラグ検出によりループ終了。
- 監視 DB 初期化
  - init_monitoring_db を呼び出して、監視用テーブルが存在することを保証（冪等）。
- ロギング / プロセス制御ユーティリティ
  - setup_logging: ルートロガー設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を使ったファイル出力（logs/<app_name>.log）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - process_priority: プロセス優先度設定（Windows と POSIX を吸収）と CPU affinity 設定ユーティリティを追加。高優先度設定をトライし、権限不足時は警告してスキップ。
  - 起動スクリプトは最初にプロセス優先度を "high" に設定するよう統一。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の計算。スコア全てが 0 の場合は等金額にフォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存ポジション考慮、売却予定銘柄の除外、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じたレバレッジ乗数計算。未定義レジームは 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based/equal/score）に基づき発注株数を算出。単元株（lot_size）、max_position_pct、max_utilization、コストバッファ等を考慮したスケーリングロジックを実装。aggregate cap 超過時のスケールダウンと残差処理（lot 単位での追加配分）を実装。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）・リスク却下数を集計してレポート出力。基準値（稼働率 99% 等）を設定して PASS/FAIL 判定を行う。日付フィルタ（--from / --to）と --db オプションをサポート。
- リサーチ / ファクター計算（基盤）
  - research.factor_research: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計を追加（関数インターフェース、定数、仕様記載）。（ファイルは途中まで実装）
- DB 統合
  - sqlite3（監視 / paper_trading）と DuckDB（分析用）を併用する設計を追加。各起動スクリプトで接続を取得して適切にクローズする。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- 起動前に必須環境変数未設定を検出する validate_config を提供。特に本番環境でのトークン／パスワード管理に注意を促すチェックを追加。

---

注記 / 運用メモ
- デフォルトのデータパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
- 停止フラグ:
  - data/stop_requested.flag を用いて外部からプロセスの停止を指示可能。
- 本番環境（KABUSYS_ENV=live）では validate_config が追加の警告を出す（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険な設定など）。
- ログ出力先ディレクトリ作成に失敗した場合はファイルロギングを無効化して stdout のみで稼働します。

今後の予定（例）
- research.factor_research の完全実装（DuckDB クエリと計算ロジックを完成）。
- 銘柄ごとの lot_size 管理、銘柄マスタ参照による拡張。
- 監視・実行のユニットテスト充実化と CI 統合。