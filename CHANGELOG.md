# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
日付はリリース日を示します。

目次
- [Unreleased]
- [0.1.0] - 2026-04-21

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-21

初回公開リリース。以下の主要機能・改善点・挙動を実装しています。

### Added
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag によって制御。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 専用 SQLite（デフォルト data/paper_trading.db）へ記録して本番 DB と分離。

- 設定管理
  - config.py: 環境変数読み込み・アクセス用 Settings クラスを実装。プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local を自動読込（環境変数に応じて上書き制御）。クォート・エスケープ・コメントを考慮した .env パーサ実装、必須環境変数チェックユーティリティを提供。
  - config_setup.py: .env を対話式に作成・更新するウィザード CLI を追加。秘密項目はマスク表示、生成テンプレートの保存機能あり。
  - validate_config.py: 起動前に .env や config/*.yaml の不足を検出する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。

- Portfolio（純粋関数群、DB 非依存）
  - portfolio_builder.py: シグナル選定（select_candidates）と重み計算（等額／スコア加重）を追加。スコアが全て 0 の場合は等金額へフォールバックして警告ログを出力。
  - position_sizing.py: 発注株数算出ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、max_position（銘柄上限）、max_utilization（総投下上限）、コストバッファによる保守的見積り、合計資金超過時のスケーリングと端数処理を実装。
  - risk_adjustment.py: セクター集中抑制（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時はフォールバックと警告。

- ユーティリティ
  - utils/logging_setup.py: 全アプリケーション共通のログ設定ユーティリティを追加。stdout ストリームハンドラと日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: Windows / POSIX を抽象化したプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。対応外 OS や権限不足は警告でスキップする安全設計。

- モニタリング DB 初期化補助
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出して監視用テーブルの冪等な初期化を保証（monitoring / execution の両方で使用）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading ログ（SQLite）から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計して検証レポートを生成する CLI を追加。P95 計算実装、期間フィルタ（--from / --to）、閾値に基づく PASS/FAIL 判定を出力。デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH / data/paper_trading.db。

- リサーチ（ファクター計算）基盤
  - research/factor_research.py にモメンタム等のファクター計算の骨子（DuckDB 接続を受ける設計、複数期間のリターンや MA200 乖離、ATR、出来高系指標の計算方針）を導入（prices_daily / raw_financials に基づく）。

- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- DB 接続の挙動
  - 監視（run_monitoring）は KABUSYS_ENV に関係なく監視用 sqlite_path（settings.sqlite_path）を使用するよう明示。実行エンジン（run_execution）は paper_trading 環境なら paper_sqlite_path に接続して本番 DB と分離。
- ログ出力先の統一
  - setup_logging を全起動スクリプトで呼び出すようにしてログ設定を統一（ファイル名は app_name に依存）。
- 環境変数読み込みの保護
  - .env の自動ロードで OS 環境変数を protected として上書きを防止（.env.local は override=True だが protected により既存 OS 環境を保持）。

### Fixed / Robustness
- MONITOR_POLL_INTERVAL の不正値を安全に処理
  - run_monitoring._get_poll_interval で環境変数が整数でない、あるいは 1 未満の場合に警告ログを出してデフォルト（60 秒）へフォールバックするように修正（time.sleep に渡した際の ValueError を防止）。
- .env パーサ強化
  - config._parse_env_line: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、無効行のスキップなどを正しく処理するよう実装。
- 起動中の停止制御
  - run_execution / run_monitoring はプロジェクト data/stop_requested.flag を参照して安全に停止できるよう制御を追加。run_execution は起動前に停止フラグが立っている場合は起動を中止。
- 権限・環境差異でのフォールバック
  - process_priority/set_cpu_affinity や logging_setup のファイルハンドラ作成で発生する権限エラーや未対応 OS を警告ログに落とし、処理をスキップして安全に継続するよう実装。
- position_sizing の合計資金超過時の丸めロジック
  - aggregate cap でスケールダウンした際に lot_size 単位で端数処理を行い、残余キャッシュで最も fractional remainder が大きい銘柄から lot 単位で追加配分するアルゴリズムを実装（上限チェック付き）。

### Notes / Developer-oriented
- Settings.paper_fill_mode は許容値チェックを行い、不正な値は例外を発生させる（有効値: "instant" | "partial" | "never" | "reject"）。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出す（外部依存の柔軟な扱い）。
- ロギングは標準出力に stdout を使用（stderr ではない） — cron 等で stdout/stderr を一本化する運用を想定。
- research/factor_research.py はファクター計算の設計方針と定数を実装中（prices_daily テーブルに依存）。大規模データ処理は DuckDB を利用する設計。

---

今後の予定（例）
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity の具体的 SQL/集計）。
- 戦略実行/バックテスト用の追加ツール群。
- 各モジュールのユニットテスト追加と CI 設定。

もし個別のファイル変更やリリースノートの粒度を細かく分けたい場合は、対象期間やコミットログの情報を提供してください。それに基づきバージョンごとの差分を詳細化します。