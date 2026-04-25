# CHANGELOG

すべての重要な変更点を Keep a Changelog の形式で記載します。  
日付はリリース日を示します。コードベースから推測して記載しているため、実際のコミット履歴とは一部異なる可能性があります。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 現時点で未リリースの変更はありません（初期リリースを 0.1.0 として記載）。

---

## [0.1.0] - 2026-04-25
初期リリース。日本株自動売買システム KabuSys の基本機能を実装しました。以下はコードベースから推測される主な追加点・振る舞いです。

### Added
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading 時はペーパートレード用の MockBrokerClient を使用し、paper_trading 用 DB を別途使用する（データ分離）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。停止フラグファイル（data/stop_requested.flag）で安全にループを終了可能。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 設定管理
  - config.Settings: 環境変数／.env ファイルからの設定読み込みを行う Settings クラスを実装。各種プロパティ（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading の挙動設定など）を提供。
  - 自動 .env ロード機能: プロジェクトルートを .git または pyproject.toml から探索し、.env/.env.local を自動読み込み（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パースの堅牢化: export プレフィックス、クォート付き値、エスケープ、インラインコメントなどに対応するパーサを実装。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の入力検証機能を実装（不正値は例外）。
- 設定補助 CLI
  - config_setup: 対話式ウィザードで .env の初期作成／更新を支援する CLI を追加。必須・任意項目のプロンプト、シークレットマスク、保存確認を実装。
  - validate_config: .env と config/*.yaml（存在する場合）を起動前に検証する CLI を追加。必須環境変数のチェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、PyYAML がない場合は YAML 検証をスキップする旨の警告を実装。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を実装。スコア合計が 0 の場合は等金額にフォールバックし警告を出す。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別集中リスクをチェックして候補を除外する機能。既存保有からセクター別エクスポージャを計算し、上限を超えるセクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは警告して 1.0 をフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に従って発注株数を計算。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に応じたスケールダウン）を実装。cost_buffer を考慮した保守的見積りと、スケールダウン後の分配ロジック（端数処理）を実装。
- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ファイル日次ローテート、30 日保持）を設定する共通ユーティリティ。ログディレクトリ作成に失敗してもコンソール出力のみで継続する。
  - utils.process_priority: Windows / POSIX（Linux/Mac/FreeBSD）両対応でプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity を最初の N コアにピン留めする set_cpu_affinity も実装。権限不足や未対応 OS の場合は警告してスキップ。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して検証レポートを出力するスクリプトを追加。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）と Pass/Fail 判定ロジックを備える。
- データアクセス
  - run_monitoring/run_execution などで DuckDB / SQLite 両方の接続を利用する実装を追加。monitoring 用 DB 初期化を保証する init_monitoring_db の呼び出しを含む。

### Changed
- ログ出力の統一
  - 全起動スクリプトから共通の logging_setup を使用することでログの形式・出力先を統一。
  - コンソール出力は stderr ではなく stdout を使用（cron 等で stdout/stderr をまとめてリダイレクトしやすくするため）。
- .env の優先順位
  - OS 環境変数 > .env.local > .env の順で設定を解決する仕様を採用。既存 OS 環境変数は保護され、.env.local は強制上書きを許可。

### Fixed
- 安全なフォールバック処理
  - MONITOR_POLL_INTERVAL が不正（非整数や 0 以下）の場合は警告を出してデフォルト（60 秒）にフォールバック。
  - DB / DuckDB 接続は finally ブロックで確実にクローズされるように実装。
  - ログディレクトリ作成やファイルハンドラ生成に失敗してもアプリケーションをクラッシュさせず、コンソールのみで継続するよう対処。
  - process_priority の権限不足等で設定に失敗した場合は警告して続行するように改善。
  - portfolio.calc_score_weights で全スコアが 0 の場合にゼロ除算や不正な重みを回避する処理を実装（等金額にフォールバック）。

### Documentation / UX
- 各種 CLI（config_setup, validate_config, tools.paper_verification_report）にヘルプ・使用例を追加し、初期構築と検証のフローをサポート。
- config_setup が生成する .env テンプレートにコメントを付与して利用者ガイドを組み込む。

---

未記載の内部実装や微細な修正は存在する可能性があります。上記はコードから推測できる主要な機能・振る舞いをまとめたものです。必要であれば、各モジュール（config, portfolio, utils, execution, monitoring, tools）の変更点をモジュール単位でさらに詳細に分解して記載します。どの粒度で整備したいかを教えてください。