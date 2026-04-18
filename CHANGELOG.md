CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日付はコードベース内のコメントおよび本時点の想定日付に基づいています。

フォーマット:
- 変更カテゴリ: Added / Changed / Fixed / Security / Removed / Deprecated

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 基本機能の初回リリース（バージョン 0.1.0）。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 等）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止制御を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用する仕様。
    - 停止フラグ検知による安全なループ終了、例外時のログ出力と継続動作を実装。
- 設定管理
  - config.py: Settings クラスを導入。環境変数から各種設定（DB パス、API トークン、KABUSYS_ENV、ログレベル、監視閾値等）を取得する API を提供。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。読み込みは OS 環境変数 > .env.local > .env の優先順。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。
    - is_live/is_paper/is_dev 等のユーティリティプロパティを追加。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 秘匿項目はマスク表示、既存 .env の読み込み、確認プロンプト、テンプレート形式でファイル書き出し。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML の存在とパース（PyYAML 未インストール時は警告）を実装。
    - --strict による警告の失敗扱いオプションを提供。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level)（"high"|"normal"|"low"）と set_cpu_affinity(cpu_count) を提供。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応、権限不足や未対応 OS は警告を出して安全にスキップ。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates) と重み計算 (calc_equal_weights, calc_score_weights) を追加。
  - portfolio/risk_adjustment.py: セクター集中制限適用 (apply_sector_cap) とレジーム乗数計算 (calc_regime_multiplier) を追加。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積りをサポート。
  - portfolio/__init__.py: 主要関数を公開するパッケージエクスポートを追加。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計・判定（閾値に基づく PASS/FAIL）して標準出力にレポートを生成。
    - --from/--to/--db オプションをサポート。P95 計算、SQL 日付フィルタ処理を実装。
- データベース / 解析
  - DuckDB 接続を受け取る研究モジュール（research/factor_research.py）の骨子を追加（モメンタム等のファクター計算を想定）。
  - 監視テーブル初期化ユーティリティ（monitoring/monitoring_db.init_monitoring_db）を使用して起動時に監視テーブルの存在を保証する仕組みを導入（run_monitoring / run_execution から呼び出し）。
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- ログ出力の扱い
  - ログは標準エラーではなく標準出力 (stdout) に出力する方針に統一（cron などのリダイレクトを容易にするため）。
- .env 読み込み
  - .env のパース挙動を改善（export KEY=val 形式、クォート内エスケープ、インラインコメントの扱いなどに対応）。
  - .env.local を .env の上書きとして利用する仕組みを追加（OS 環境変数は protected として上書き不可）。
- 設定検証
  - validate_config による起動前チェックを導入し、起動前に設定漏れや明らかな不整合を発見しやすくした。

Fixed
- 環境値の扱いでの堅牢性向上
  - MONITOR_POLL_INTERVAL の不正値に対して安全にフォールバックし、ログに警告を残すようにした（0 以下や非整数の処理）。
  - PAPER_FILL_MODE の不正値検出で早期に例外を投げるようにして誤設定を防止。

Security
- .env ファイル関連の注意書きを config_setup の出力に含め、.env を絶対に Git にコミットしないことを明示。

Known limitations / Notes
- research/factor_research.py はファクター計算の設計方針と定数を含むが、calc_momentum の完全実装は途中（ファイル末尾で切れている）。DuckDB を前提とした実装で、prices_daily / raw_financials テーブルに依存する設計。
- 一部の機能（ExecutionEngine, BrokerClientFactory, SystemMonitor 等）の具象実装は本差分では参照されるが、ここに含まれていない外部モジュールに依存する（execution.*、monitoring.* の内部実装が別ファイルに存在する想定）。
- ログディレクトリの作成やプロセス優先度設定は環境・権限に依存するため、権限不足時は警告ログを出してフォールバックします。

その他
- CLI エントリポイント:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 実運用用スクリプト: run_execution.py, run_monitoring.py（それぞれ python -m kabusys.run_execution / python -m kabusys.run_monitoring で実行可能）

----- End of CHANGELOG -----