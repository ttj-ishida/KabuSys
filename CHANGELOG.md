KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

変更履歴
========

[0.1.0] - 2026-04-19
-------------------

Added
- 基本リリース: パッケージ初期版を追加。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag を検知して行う。
    - 監視は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と完全分離。
    - 停止フラグ / PID 管理（data/stop_requested.flag, data/execution.pid）に対応。
- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数経由で各種設定へアクセス可能に。
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。
    - 自動ロード優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 環境変数パースの改善（export プレフィックス、クォート/エスケープ、インラインコメントの扱いなどをサポート）。
    - 各種プロパティ: J-Quants / kabu API / LINE / DuckDB / SQLite / Paper Trading のパス、閾値（CPU/MEM/DISK）などを提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 入力のマスク、選択肢、デフォルト表示、保存確認機能を提供。
  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリチェック、YAML パース（PyYAML が利用可能な場合）、本番用追加ガード（LINE 設定・Kill Switch）を実施。
    - --strict モード: 警告を FAIL として exit(1)。
- ログ / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテーション (TimedRotatingFileHandler) によるファイル出力（logs/<app_name>.log）を設定。デフォルトで 30 日分保持。
    - ログレベル / ログディレクトリの解決順を提供。ファイルハンドラ作成失敗時はコンソール出力にフォールバック。
  - utils/process_priority.py
    - set_process_priority(level) を追加。Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - set_cpu_affinity(cpu_count) を追加（任意で最初の N コアに固定）。
    - 権限不足や未対応 OS でも安全にスキップして警告出力。
- Portfolio 関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコア全て 0 の場合は等金額配分へフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を追加。
    - "unknown" セクターの扱いや、regime が未知の場合のフォールバックを明記。
  - portfolio/position_sizing.py
    - position sizing ロジックを追加。allocation_method ("risk_based", "equal", "score") に対応。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate 上限、cost_buffer（手数料/スリッページ見積）を考慮したスケーリングと再配分アルゴリズムを実装。
    - 不足データ（価格未取得）をスキップし、デバッグログを出力。
  - portfolio/__init__.py をエクスポート用に追加。
- paper trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite (デフォルト: data/paper_trading.db) から指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し、基準値で PASS/FAIL 判定を出力するスクリプトを追加。
    - CLI オプション: --from, --to（YYYY-MM-DD）、--db（DB パス）。閾値はソース内定数で定義。
- research
  - research/factor_research.py
    - DuckDB を用いたファクター計算の基礎を追加（モメンタム / MA / ATR / ボリューム等の計算を想定）。関数群は DuckDB 接続と prices_daily/raw_financials テーブルを参照する設計（実装の一部が追加済み）。
- パッケージスケルトン
  - utils/__init__.py, tools/__init__.py を追加。

Changed
- なし（初回リリースのため過去変更なし）

Fixed
- なし（初回リリースのため過去修正なし）

Notes / 実装上の重要点
- run_monitoring は KABUSYS_ENV に依存せず常に Settings.sqlite_path（production 想定）を使用するため、本番監視 DB の扱いに注意してください。
- run_execution は paper_trading 環境で paper_sqlite_path を使用して本番 DB とデータ分離を行います。paper_trading 用 DB のデフォルトは data/paper_trading.db。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップします（パッケージ配布後や特殊な配置での安全策）。
- ログは標準出力（stdout）へも出るため、cron/Task Scheduler などからの実行時にログ取得しやすくしています。ファイル出力に失敗しても stdout のみで継続します。
- process priority / cpu affinity 設定は権限や OS に依存するため、失敗時は警告ログを出して処理を続行します。
- portfolio/position_sizing の aggregate scaling は lot_size 単位で安全に再配分するアルゴリズムを実装していますが、将来的に銘柄別の lot_size を取り扱う拡張を想定しています（TODO コメントあり）。

Acknowledgments
- 本リリースは初期実装のため、今後ユニットテストの追加、ドキュメント充実、エラーケースのさらなる硬化を予定しています。