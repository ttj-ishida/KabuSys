# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠しています。  
日付は本変更セットの仮定日です。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-23

### Added
- 基本機能の初期実装を追加（KabuSys v0.1.0 リリース相当）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全にループ終了。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する旨を明確化。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db）を利用し、本番 DB と分離。
    - 停止フラグで実行停止、実行用 pid ファイルの取り扱いを実装。
- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env / .env.local の読み込みルール（OS 環境変数を保護）。
    - .env 行パーサを実装（export プレフィックス対応、クォートとエスケープ、インラインコメントの取り扱い）。
    - Settings クラスで環境変数をプロパティ化（データベースパス、paper_trading 用パス、PID / Kill flag パス、閾値等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
- 設定ユーティリティ
  - config_setup.py
    - 対話式ウィザードで .env の初期作成 / 更新を支援。
    - シークレット項目はマスク表示。既存 .env の読み込みとデフォルトの再利用に対応。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在・本番時のガード等を検証。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML が無ければ YAML の中身検証をスキップし、その旨を警告。
- ロギング / プロセス制御
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを提供。コンソール(stdout)と日次ローテーションファイル（logs/<app>.log）を設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみで継続）。
    - ログレベル解決順（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。
- Portfolio 構築ロジック（pure functions）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレークルール）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（スコア合計 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（売却予定銘柄を除外して既存エクスポージャーを計算）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング。未知レジームはフォールバックして 1.0）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジック（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積り。
    - スケーリング後の残差配分（fractional remainder を用いた lot 単位での追加配分）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db、--db/環境変数で上書き可能。
    - デフォルトの合格閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
- research/factor_research.py
  - ファクター計算モジュールの骨格を追加（モメンタム、MA200、ATR、流動性等を DuckDB の prices_daily / raw_financials を参照して計算する設計）。
  - 実装方針・定数の定義を含む（計算窓やスキャン日数等）。

### Changed
- .env 読み込みの設計
  - OS 環境変数が優先され、.env.local は .env の後に上書きする（OS 環境変数は protected として上書き不可）。
  - export KEY=val 形式とクォート処理、インラインコメント処理を強化。
- ログ出力
  - StreamHandler を stdout に固定（stderr ではなく）し、Task Scheduler / cron での扱いを考慮。
  - 既存ハンドラがある場合は一度 flush/close してから再設定することで二重ハンドラ設定を防止。
- run_monitoring / run_execution
  - 起動時に最初にプロセス優先度を "high" に設定するよう変更。
  - run_execution は paper_trading 環境で BrokerClientFactory による Mock ブローカー利用を想定（DB 分離）。
  - monitoring 用 DB 初期化（init_monitoring_db）を冪等に呼び出すように統一。

### Fixed
- .env パーサのバグ対応（推定）
  - クォート内のバックスラッシュエスケープと閉じクォート検出の処理を改善。
  - クォートなしの値に対するインラインコメント認識ロジックを修正（'#' の直前がスペース/タブのときのみコメント扱い）。
- 環境変数の不正値に対するフォールバック
  - MONITOR_POLL_INTERVAL が不正（数値以外や 0/負数）だった場合、デフォルト 60 秒にフォールバックして警告を出力。
  - PAPER_FILL_MODE の値チェックを追加し、不正値で ValueError を送出（有効値: instant/partial/never/reject）。
  - KABUSYS_ENV / LOG_LEVEL の不正値に対するエラーチェックを追加。

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- 環境変数作成ウィザード / ファイル出力で .env を誤ってコミットしないよう注意書きを追加（config_setup.py）。

---

参照:
- 各モジュールの実装は src/kabusys 以下に含まれます。詳細な使用方法は各スクリプトの docstring およびコメントを参照してください。