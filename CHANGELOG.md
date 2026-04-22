# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、リポジトリ内の現行コードベース（バージョン 0.1.0）から推測して作成しています。

## [0.1.0] - 2026-04-22

### Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 実行用スクリプト / デーモン類
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、MockBrokerClient を利用して本番 DB と完全分離して実行可能。
    - 停止制御: data/stop_requested.flag を監視。停止時にはエンジンの stop() を呼び安全に終了。
    - PID ファイル出力（data/execution.pid）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視部分は KABUSYS_ENV に関わらず本番用 sqlite_path を使用（監視データは本番の監視 DB に記録）。

- 設定関連ユーティリティ
  - config.py
    - .env 自動読み込み機能（.env, .env.local）。OS 環境変数を保護する仕組みあり。
    - .git / pyproject.toml を基準にプロジェクトルートを特定する実装（CWD に依存しない）。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / paper モード等）。値検証（有効値チェック）を実装。
    - PAPER_FILL_MODE（instant / partial / never / reject）や KABUSYS_ENV（development / paper_trading / live）等の検証を含む。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを実装。既存 .env の読み込み・編集、シークレット項目のマスク、保存機能あり。
  - validate_config.py
    - 起動前に .env や config/*.yaml の不備を検出する CLI を追加。
    - --strict オプションで警告も失敗扱いにできる。
    - 必須環境変数チェック、パス存在チェック、YAML パース確認（PyYAML の存在を確認）、本番環境向けガードを提供。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 単一の setup_logging(app_name, ...) で統一的にログ設定を行う実装を追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数連携、ハンドラの二重登録防止（既存ハンドラをクリア）を実装。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加（Windows の優先度クラスと POSIX の nice 値を吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。権限や未対応 OS の場合は安全にスキップし警告。

- ポートフォリオ構築 / リスク / ポジション管理
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター比率が上限を超えている場合に当該セクターの新規候補を除外）。unknown セクターは除外対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear → 1.0/0.7/0.3、未知レジームはフォールバック 1.0）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を算出する calc_position_sizes を実装。allocation_method として "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate キャップ（available_cash）に基づくスケールダウン、cost_buffer による保守的見積り、残差処理のための再配分ロジックを備える。

- Research / ファクター計算
  - research/factor_research.py（モメンタム等のファクター計算モジュール）
    - DuckDB 接続を受け prices_daily 等のテーブルを用いてモメンタム・移動平均乖離等を計算する設計を導入（モジュールコメント含む）。（モジュール途中まで実装あり）

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading の検証用レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出し PASS/FAIL 判定を行う。
    - CLI 引数で期間指定（--from, --to）および DB パス指定（--db）をサポート。閾値はスクリプト内の定数で定義。
  - package export
    - kabusys/portfolio/__init__.py で主要関数をエクスポート。

### Changed
- 初期リリースとして各モジュールを整理・命名規約に従って配置。ロギング・プロセス優先度設定を起動シーケンスの最初に行うことで実行中の挙動を安定化。

### Fixed
- 環境読み込みの堅牢化
  - .env パーサでクォート内のバックスラッシュエスケープ、行末コメントの扱いを正しく処理するように実装。export KEY=val 形式にも対応。
  - .env 読み込み失敗時に警告を出して処理を継続するフォールバックを実装。

### Security
- .env ファイルに関する注意喚起を config_setup の出力に明示（.env を Git にコミットしないこと）。

### Notes / Behavior
- 監視（run_monitoring）は MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（不正値はデフォルト 60 秒にフォールバック）。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データと分離する設計。
- config.validate では --strict を使うと警告を FAIL 扱いにでき、本番導入前チェックに使いやすい。
- ロギングは stdout を基軸にし、ログファイルが作成できない環境でもコンソール出力のみで継続するよう安全に設計。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に警告を出して安全にスキップする。

---

今後の更新案（非網羅）
- research/factor_research の完全実装（ファクター計算ロジックの続き）
- テストカバレッジの追加（ユニットテスト）
- 設定ファイル（config/*.yaml）の生成スクリプトやサンプルの充実
- 実行環境向けのデプロイ / systemd / supervisor 用の起動スクリプトサンプル

もし CHANGELOG に追加してほしい詳しい差分（例えばコミット単位や過去のバージョンとの比較情報）があれば、該当するコミットログや以前のバージョン情報を提供してください。そこからより正確な履歴を作成します。