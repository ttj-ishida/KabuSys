CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
このリポジトリ内のコードから推測できる機能追加・修正点・既知の制約をもとに作成しています（自動生成ではなく手作業での推測を含みます）。

バージョン
----------

### [0.1.0] - 初期リリース（推定）

Added
-----
- 基本アプリケーションパッケージを追加（kabusys）。
  - __version__ = "0.1.0"
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアントを BrokerClientFactory で生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動する。
    - 停止フラグ（data/stop_requested.flag）が立っている場合は起動しない、また実行中に検知したら安全に停止する仕組みを実装。
    - 実行 PID を data/execution.pid に記録。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db 等）を使用して監視用テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
- 設定関連
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出 .git / pyproject.toml ベース）。優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env パースロジックを実装（export 形式、クォート・エスケープ、インラインコメント対応）。
    - Settings クラスを導入。多くの設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値、KABUSYS_ENV, LOG_LEVEL 等）。
    - 環境値のバリデーション（有効な KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
- 設定支援ツール・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を作成 / 更新する CLI。
    - J-Quants / kabuステーション / DB パス / ログレベル / Kill Switch などの設定項目を対話的に入力可能。既存値を読み込み Enter で再利用可。
  - validate_config.py
    - 起動前検証 CLI。
    - 必須環境変数のチェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード事項を検査。
    - --strict オプションで警告を FAIL 扱いにできる。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg, max, P95）等。
    - デフォルト閾値を定義して PASS/FAIL を判定（例: 稼働率 >= 99.0%、P95 <= 200 ms など）。
    - --from / --to / --db オプションに対応。デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルの候補選定と重み計算（等分配 / スコア加重）。
    - スコア合計が 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）実装。既存保有を考慮して同一セクターが一定比率（デフォルト 30%）を超える場合は当該セクターの新規候補を除外。
    - レジーム乗数 calc_regime_multiplier を実装（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py
    - position sizing（allocation）ロジックを実装。allocation_method: "risk_based" / "equal" / "score" をサポート。デフォルトパラメータ例: risk_pct=0.005, stop_loss_pct=0.08, max_position_pct=0.10, max_utilization=0.70, lot_size=100, cost_buffer=0.0。
    - aggregate cap（利用可能現金を超える場合のスケールダウン）ロジックと残余キャッシュに基づく追加分配アルゴリズムを実装。
  - portfolio/__init__.py に API をエクスポート。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 一貫したロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログファイル出力（既定 logs/<app_name>.log）、30 日保持。
    - LOG_LEVEL / LOG_DIR の解決ルールを実装。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）設定をプラットフォーム非依存にラップ（Windows / POSIX に対応）。
    - CPU affinity 固定関数 set_cpu_affinity を提供（利用可能なコア数を尊重）。権限不足や未対応環境時は警告を出して安全にスキップ。

Changed
-------
- DuckDB を分析用 DB として採用し、複数モジュール（execution, monitoring, research 等）で DuckDB 接続を利用する設計に変更 / 追加。
- 監視（monitoring）は監視用 SQLite を初期化するヘルパー init_monitoring_db を呼び出して、監視テーブルの存在を保証する（冪等処理）。
- 実行（execution）では paper_trading 環境で本番 DB に誤って書き込まないための分離設計を明確化（paper_sqlite_path の利用）。
- 環境設定の自動ロード挙動を定義（.env, .env.local の優先順位と OS 環境保護）。

Fixed
-----
- 不正な MONITOR_POLL_INTERVAL 値（0/負数/非数）に対してデフォルト値にフォールバックし、警告を出す処理を追加。
- ログハンドラが二重に設定される問題を防ぐため、setup_logging() は既存ハンドラをすべて閉じてから再設定するように変更。

Security
--------
- .env ファイル作成ウィザードで秘密情報（トークン / パスワード）をマスク表示し、.env を誤ってコミットしないよう注意喚起のヘッダを付与。
- validate_config による必須キーの存在チェックを追加し、起動前の設定漏れ検出を強化。

Known issues / TODOs（既知の制約・注記）
----------------------------------------
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされ得る旨の注記があり、将来的に前日終値等でフォールバックすることが示唆されている（未実装の TODO）。
- portfolio/position_sizing:
  - 将来的に銘柄別の lot_size をサポートする設計に拡張可能とのコメントあり（現状は全銘柄共通 lot_size=100 を想定）。
- research/factor_research.py:
  - ファイルの末尾で calc_momentum の実装が途中で終わっている（切れている）。このためファクター計算モジュールは未完の可能性がある。実装継続が必要。
- config 自動読み込み:
  - プロジェクトルート検出は .git または pyproject.toml を基準とするため、配布後や特殊配置時に検出できない場合は自動ロードがスキップされる点に注意。
- process_priority / set_cpu_affinity:
  - 権限不足や未対応 OS では警告を出して処理をスキップするが、期待通りに優先度が変わらない可能性がある。
- tools/paper_verification_report:
  - DB テーブルが存在しない場合は例外回避のためにデフォルト値で出力する実装があるが、完全なデータ品質保証や詳細解析は別途必要。

Usage notes（起動時の主な環境変数と挙動）
-------------------------------------
- 主要 ENV:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL（デフォルト: INFO）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading モード用 DB、デフォルト: data/paper_trading.db）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト: 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env 読み込みを無効化）
  - KILL_FLAG_CLEAR_ON_START（本番での Kill Switch 自動クリア設定。デフォルト 0 推奨）
- 実行スクリプト:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

Contributors / Notes
--------------------
- 本 CHANGELOG はコードベースの内容（docstring・コメント・実装）から推測して作成しています。リポジトリの実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。