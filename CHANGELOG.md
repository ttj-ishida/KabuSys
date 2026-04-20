# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
バージョン番号は semver を想定しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-20

初回リリース。日本株自動売買システムのコア機能群を実装しました。主な追加内容は以下の通りです。

### Added

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録することで本番 DB と分離。
    - プロセス優先度を "high" に設定する仕組みを導入。
    - 停止フラグ (data/stop_requested.flag) を監視し、フラグ検知時にエンジンを安全に停止。
    - エンジンは別スレッドで実行され、メインスレッドはフラグ検出やスレッド終了待ちを行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループを提供する起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は起動環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) の検知でループを終了。

- 設定管理・ウィザード・検証
  - config.py
    - .env 自動ロード機能を提供（プロジェクトルート検出: .git または pyproject.toml）。
    - export KEY=val、クォート文字列、インラインコメントなどに対応した .env パーサを実装。
    - Settings クラスを導入し、各種環境変数（J-Quants、kabu API、DB パス、監視閾値、paper_trading の設定など）をプロパティ経由で取得可能に。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）や KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - config_setup.py
    - 対話形式で .env を初期作成・更新するウィザードを実装。項目の説明、デフォルト、シークレットマスク表示、確認プロンプトを提供。
    - .env を書き出す際にコメントヘッダを挿入し、Git へのコミット禁止を明記。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、PyYAML による YAML パースチェック（未インストール時は警告）などを実行。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連（純粋関数群・DB非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択（同点時は signal_rank 小さい方優先）。
    - calc_equal_weights: 等金額配分（1/N）を算出。
    - calc_score_weights: スコア加重配分を算出。全銘柄スコアが 0 の場合は等金額配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）により新規候補から除外するロジックを実装。既存保有の評価額は price_map を使用し、売却予定銘柄は除外できる。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を提供（デフォルトで未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に対応した株数算出ロジック実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮。
    - スケーリング後の端数配分を残差順に lot_size 単位で追加するロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを実装。StreamHandler(stdout) と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - ログレベル、ログディレクトリは引数 / 環境変数 / デフォルトの順で解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することで cron 等の出力取り扱いに配慮。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）を OS に依存せず設定するヘルパを実装。Windows と POSIX (Linux, Darwin, FreeBSD) をサポート。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（権限不足時は警告でスキップ）。

- 監視・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db、--db/環境変数で指定可能。閾値はソース内で定義（稼働率 99%、成功率 90% など）。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - Momentum 等のファクター計算モジュールの実装を開始。DuckDB 接続を受け prices_daily / raw_financials を参照してモメンタム、MA200乖離、ATR、出来高指標等を計算する設計。momemtum 計算の基礎ロジックを実装中（未完）。

- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

### Changed

- 初回リリースのため変更履歴はありません。

### Fixed

- 初回リリースのため修正履歴はありません。

### Security

- .env ファイルに機密情報が含まれる旨を config_setup.py の出力ヘッダで明記（Git へのコミット禁止を推奨）。

---

注記:
- この CHANGELOG はソースコードから実装意図を推測して作成しています。細かな挙動や追加のドキュメント（API仕様、Engine の内部挙動など）はソースコードの該当モジュールを参照してください。