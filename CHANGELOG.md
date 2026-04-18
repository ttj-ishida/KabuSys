# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-18

### Added
- 初期リリースとして以下の主要コンポーネントを追加しました。
  - コアパッケージ情報
    - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - 設定管理
    - Settings クラス（`kabusys.config`）を追加。環境変数から各種設定を読み取るプロパティを提供。
    - 自動 .env ロード機能（プロジェクトルートを .git / pyproject.toml で検出）。OS 環境変数は保護され、`.env.local` は `.env` 上書きが可能。
    - `.env` パーサーの追加（`export KEY=val`、引用符/エスケープ、インラインコメントの取り扱いに対応）。
    - 必須環境変数チェック用ユーティリティ（Settings 内の _require）。
  - 環境設定・検証 CLI
    - `kabusys.config_setup`：対話式ウィザードで `.env` を作成／更新する CLI。
    - `kabusys.validate_config`：`.env` と `config/*.yaml` の事前検証 CLI。`--strict` オプションで警告をエラー扱いにする機能を提供。
  - 実行・監視用起動スクリプト
    - `kabusys.run_execution`：ExecutionEngine 起動スクリプトを追加。
      - 起動時にプロセス優先度を "high" に設定。
      - `KABUSYS_ENV=paper_trading` の場合、ペーパートレード用の専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離。BrokerClientFactory を経由してブローカークライアントを生成。
      - OrderRepository、OrderManager、RiskManager（デフォルト RiskConfig 値あり）、Reconciler、ExecutionEngine の組立てと起動。バックグラウンドスレッドでセッションを実行し、停止フラグ（`data/stop_requested.flag`）で安全停止。
      - PID ファイル（デフォルト `data/execution.pid`）のサポート。
    - `kabusys.run_monitoring`：SystemMonitor ポーリングループ起動スクリプトを追加。
      - デフォルトポーリング間隔 60 秒、環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（不正値は警告してデフォルトにフォールバック）。
      - 監視は環境に関係なく本番の `sqlite_path` を使用して監視テーブルを初期化。
      - 停止フラグ（`data/stop_requested.flag`）の検知でループを終了。`check_once()` 内の例外は捕捉して次ポーリングへ継続。
  - データベース・分析
    - DuckDB 接続を使用する設計を導入（`duckdb` を利用）。
    - 監視テーブル初期化ユーティリティ `init_monitoring_db` を実行開始時に呼び出す（冪等）。
  - ユーティリティ
    - `kabusys.utils.process_priority`：クロスプラットフォームでのプロセス優先度設定（Windows / POSIX 対応）および CPU affinity 固定関数を提供。psutil の権限不足等を考慮した警告処理あり。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - `kabusys.portfolio.portfolio_builder`：候補選定（score 降順・同点時のタイブレーク）、等重・スコア重み計算（スコア合計が 0 の場合は等重にフォールバック）。
    - `kabusys.portfolio.risk_adjustment`：セクター上限適用（売却予定銘柄の除外や "unknown" セクターの扱い）とレジーム乗数（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）。
    - `kabusys.portfolio.position_sizing`：allocation_method（risk_based / equal / score）に基づく株数算出、単元株（lot_size）丸め、aggregate cap（利用可能現金を超えた場合のスケーリング）と残差分配ロジック、コストバッファ対応。
  - 研究用モジュール
    - `kabusys.research.factor_research`：DuckDB の prices_daily/raw_financials を参照してモメンタム（1M/3M/6M、MA200乖離）やボラティリティ（ATR、20日平均出来高等）を計算する関数群を追加。
  - ツール
    - `kabusys.tools.paper_verification_report`：Paper Trading 用の検証レポート生成スクリプトを追加。期間フィルタ（--from/--to）、DB パス指定（--db もしくは環境変数）に対応。稼働率・注文成功率・送信率・P95 レイテンシ等を計算し PASS/FAIL 判定を行う。
  - ドキュメント的コメント
    - 各モジュールに設計意図・使用方法・注意点を記載した docstring を多数追加（例: PortfolioConstruction.md/StrategyModel.md に基づく旨の注記）。

### Changed / Improved
- .env ロードの振る舞いを明確化
  - OS 環境変数は既定で保護され、`.env.local` は `.env` の上書き用として扱う。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
- 設定検証の利便性向上
  - `validate_config` で PyYAML が未インストールの場合は YAML 内容検証をスキップし、警告を出す。
  - ファイルパスの親ディレクトリ存在チェックを行い、存在しない場合は警告（自動作成される場合がある旨を注記）。
- 起動時の堅牢性向上
  - run_monitoring のポーリングループで check_once() の例外を捕捉してループを継続するようにし、監視プロセスが一度のエラーで終了しないように改善。
  - run_execution は停止フラグの存在を確認して即時起動中止するガードを追加。
- process_priority の互換性改善
  - Windows と POSIX の差を内部で吸収し、未対応 OS では警告してスキップする安全処理を実装。
  - CPU affinity 設定で指定コア数が利用可能コア数を超える場合の挙動をログメッセージで明示。
- position_sizing のアルゴリズム改善
  - aggregate cap 超過時のスケーリングと残差（fractional remainder）に基づく追加配分ロジックを実装。単元株（lot_size）を尊重して配分を調整。

### Fixed
- 各種算出関数での欠損データ（None / 空リスト）に対する安全処理を追加し、ゼロ除算や None 参照による例外を回避。
  - 例: P95 算出が空リストの場合は None を返す。
  - 例: calc_score_weights でスコア合計が 0 の場合は等金額配分にフォールバックして警告を出す。
- .env パーシングの不正行やコメント処理に起因する誤設定を回避するための解析ロジックを改善。

### Notes
- セキュリティ／運用上の注意
  - `.env` は絶対にリポジトリにコミットしないこと（`config_setup` のヘッダにも明記）。
  - 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨（自動クリアは危険）。
- ペーパートレード
  - PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject"。不正値は例外となる。
  - paper_trading 実行時は paper 用 SQLite を使用して本番 DB とデータを分離する設計。
- 依存
  - DuckDB と psutil がランタイム依存。PyYAML は config 検証時のみ（未インストールでも動作は継続し、YAML 検証はスキップされる）。
- 将来の改善メモ（コード内 TODO）
  - position_sizing の lot_size を銘柄別で扱えるように拡張する案がコメントとして残っています。
  - apply_sector_cap で価格欠損時のフォールバック（前日終値や取得原価）の採用検討。

---

（この CHANGELOG はソースコードの実装内容に基づいて作成しています。実際のリリースノートや運用ドキュメントと合わせてご利用ください。）