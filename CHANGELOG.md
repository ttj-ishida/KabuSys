# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
初回リリース (v0.1.0) はパッケージの基本機能（実行・監視・設定・ポートフォリオ構築・ユーティリティ類）を実装しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18

### Added
- 全体
  - パッケージ初期リリース。モジュール群を整理してアプリケーションの起動 / 設定 / レポート作成 / ポートフォリオ構築ロジックを提供。
  - バージョン: `kabusys.__version__ = "0.1.0"`

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下など）はデフォルトへフォールバックし、警告を出力。
    - 停止はプロジェクトの data/stop_requested.flag を検知して行う。
    - Monitoring 用 DB は実行環境にかかわらず本番用の sqlite_path を使用する挙動を明確化。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient（BrokerClientFactory 経由）を使用し、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全分離。
    - 実行中は PID ファイルを書き、停止フラグ（data/stop_requested.flag）で安全に停止できる仕組みを備える。
    - 起動時に監視テーブルが存在することを保証するため init_monitoring_db を呼ぶ（冪等）。

- 設定・検証
  - config.py
    - .env 自動ロード機能を追加（.env, .env.local）。ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパース実装は export 形式、クォート処理、インラインコメントなどを考慮した堅牢な実装。
    - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（J-Quants / kabu API / DB パス / 監視閾値 / 環境判定など）。値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。シークレット値はマスク表示し、既存 .env を読み込んで Enter で再利用可能。
    - デフォルトや選択肢を用意し、保存確認後に .env ファイルを出力する。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数の有無、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリの存在確認、config/*.yaml の存在および（PyYAML がある場合）パース検証、本番環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）を実施。
    - `--strict` オプションで警告も失敗として扱える。

- ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで統一して使えるロギング設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler、30 日分保持）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
    - ログレベル・ログディレクトリは引数または環境変数で解決。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows と POSIX 系（Linux/Mac 等）の差分を吸収。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。権限不足など発生した場合は安全にスキップし警告を出す。

- ポートフォリオ構成（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補抽出（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装。既存ポジションを考慮して特定セクターが上限に達している場合は新規候補を除外する。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear, 未知は 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。
    - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）でスケールダウンするロジックを実装。cost_buffer を考慮した保守的なコスト見積り、残余キャッシュを使った端数配分の実装を追加。
    - 価格欠損や 0 の場合はスキップしてログ出力。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を解析して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）などを計算。
    - P95 計算、期間フィルタ、データ欠損時の耐性、閾値（稼働率 99%、成功率 90% など）を備え、PASS/FAIL 判定を表示。

- リサーチ
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム等の定義、定数）。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。
    - （calc_momentum のドキュメントと定数群を実装。関数本体は継続実装を予定）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （なし）

---

注:
- 多くのモジュールで外部リソース（SQLite / DuckDB / kabu API / J-Quants 等）への依存があります。運用前に `python -m kabusys.config_setup` と `python -m kabusys.validate_config` による設定の作成・検証を推奨します。
- ファイル出力やプロセス優先度変更などは権限に依存するため、権限不足時には警告を出してフォールバックする設計です。