# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」準拠です。

全般的な注意:
- このリリースはリポジトリの現行コードベースに基づき、実装内容から推測して記載しています。
- 日付はリリース時に適宜更新してください。

## [0.1.0] - 2026-04-19

### Added
- 起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視ループはプロジェクト直下の data/stop_requested.flag を検知して安全に終了する。
    - 監視は常に本番用の SQLite パス（Settings.sqlite_path）を使用する設計。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパー用 SQLite（data/paper_trading.db、環境変数で上書き可）と MockBrokerClient を使用し、本番 DB と分離する。
    - 実行中は data/stop_requested.flag により安全停止。実行用 pid ファイルパスをサポート。

- 設定・環境管理
  - config.py
    - Settings クラスを実装し、環境変数経由でアプリ設定を提供（J-Quants / kabu API / DB パス / モニタ閾値 等）。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH 等の設定を扱うプロパティを実装。
  - config_setup.py
    - 対話式の .env 作成ウィザードを追加。必須項目・任意項目・デフォルトを提示して .env を生成可能。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの存在チェック、config/*.yaml の存在/パース検証（PyYAML がある場合）等をチェック。
    - --strict オプションで警告を失敗として扱う機能。

- ロギング・ユーティリティ
  - utils/logging_setup.py
    - 一貫したログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続するフォールバックを実装。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。

- プロセス優先度ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) により Windows/Linux/macOS を透過して優先度を設定。権限不足や未対応 OS では安全にスキップして警告を出力。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定する機能を提供。制約やエラー時は警告でフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を提供。スコア合計が 0 の場合は警告を出して等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター上限適用 apply_sector_cap（当日売却予定の銘柄を除外可能、unknown セクターは制限適用除外）とレジーム乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" とフォールバック）を実装。
  - portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に基づく株数算出 calc_position_sizes を実装。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ）考慮、残差配分ロジックを実装。
    - 不足価格データ（価格未取得）の場合を安全に無視してログ出力。

- 解析・レポートツール
  - tools/paper_verification_report.py
    - ペーパートレーディング DB から稼働率・注文成功率・送信率・レイテンシなどを集計して検証レポートを生成する CLI を追加。
    - P95 計算、各種閾値（稼働率 99%、注文成功率 90% 等）に基づく PASS/FAIL 判定を実装。日付フィルタ、DB パス指定オプションをサポート。

- 研究用ファクター計算（骨子）
  - research/factor_research.py
    - DuckDB を用いたモメンタム等ファクター計算の骨子（モメンタム、MA200、ATR、出来高等）を追加（処理設計と定数定義を含む）。関数群は prices_daily/raw_financials を参照する設計。

### Changed
- ログの標準出力を stdout に統一
  - logging_setup にて StreamHandler を stdout に固定（cron/task からの起動時に stdout/stderr を一本化するため）。

- DB の取り扱い
  - run_monitoring は KABUSYS_ENV に依存せず本番用 sqlite_path を常に使用する明示的設計（監視 DB を本番で集約する想定）。
  - run_execution は paper_trading 環境時に paper 用 SQLite を使用して本番データと明示的に分離。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line にてクォート文字・エスケープ、インラインコメントの扱いを考慮したパーシングを実装。export キーワードにも対応。
  - MONITOR_POLL_INTERVAL の無効値（0 以下や非整数）を警告しデフォルトにフォールバックする処理を追加。

- 安全停止・リソースクリーンアップの改善
  - run_monitoring/run_execution で stop flag による安全停止処理を追加。例外発生時でも SQLite/DuckDB 接続を確実にクローズするよう finally を導入。

- 設定検証の情報改善
  - validate_config にて未設定の必須環境変数をエラー、プレースホルダ値を警告として分類するよう改善。PyYAML 未インストール時は YAML チェックをスキップして警告を出す。

### Deprecated
- なし（このリリースでは互換性破壊を意図した廃止は行っていません）

### Removed
- なし

### Security
- なし（直接的なセキュリティ修正は含まれていませんが、機密値の取り扱いでは .env 作成時にシークレット項目をマスク表示する等、取り扱いに配慮しています）

## 重要な注意（Breaking / 運用上の変更点）
- run_monitoring は環境にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視データを本番と分離したい場合は設定を見直してください。
- PAPER_TRADING 環境では run_execution が paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込むため、本番 DB とデータは明示的に分離されます。運用前に環境変数を確認してください。
- .env の自動ロード機能が追加されています。テストや特殊環境で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority の設定はプラットフォーム依存や権限により失敗することがあります（警告表示してスキップ）。運用環境での動作確認を推奨します。

---

（以降のリリース履歴は今後の変更に合わせて追記してください。）