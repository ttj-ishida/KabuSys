# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
主要バージョンは semantic versioning を想定しています。

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-04-17
初回リリース。本リポジトリに含まれる主要機能・CLI・ユーティリティを追加。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB は環境にかかわらず本番用の sqlite_path を使用。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループを終了。
    - check_once() 実行中の例外を捕捉してログに記録し、次回ポーリングへ継続する堅牢化を実装。
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、paper_trading 用の専用 SQLite（data/paper_trading.db）で本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ検知時に ExecutionEngine を安全に停止する制御を実装（停止フラグ: data/stop_requested.flag）。
    - 実行中は別スレッドで engine.run_session を回し、メインスレッドで停止フラグ監視を行う。

- 設定・環境変数管理
  - Settings クラス（src/kabusys/config.py）を導入し、環境変数経由の一元管理を提供。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env ファイルの読み込み順序を OS 環境変数 > .env.local > .env として実装。既存 OS 環境変数は保護される。
    - .env パース機能は export 構文、クォート文字列、エスケープ、インラインコメント（クォートなしの特定条件）をサポート。
    - 設定プロパティ群を用意（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境等）。一部値は妥当性チェック（例: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE）。
    - settings = Settings() をモジュールレベルでエクスポート。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加（src/kabusys/config_setup.py）。
    - 秘匿項目は表示をマスク、既存 .env の読み込み・再利用、確認プロンプト、ファイル書き出しをサポート。
  - validate_config: 起動前チェック用 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向けの追加警告などを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で候補選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等重配分・スコア加重配分（全スコアが 0 の場合は等重へフォールバックし警告）。
  - portfolio.risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中上限を超える既存エクスポージャーがある場合に当該セクターの新規候補を除外。unknown セクターは上限適用除外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下倍率を返却（不明レジームは警告して 1.0 でフォールバック）。
  - portfolio.position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: equal/score/risk_based の配分方式に対応した株数計算。lot_size（単元）丸め、1 銘柄上限、aggregate cap によるスケールダウン、コストバッファを考慮した保守的な見積り、端数処理の再配分ロジックを実装。

- ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）
    - set_process_priority: Windows / POSIX (Linux/Mac/FreeBSD) を吸収してプロセス優先度 (nice / HIGH_PRIORITY_CLASS 等) を設定。権限不足や未サポート OS では警告を出してスキップ。
    - set_cpu_affinity: 指定コア数へ CPU affinity を固定するユーティリティ（エラー時は警告してスキップ）。
    - どちらも例外抑制とログ出力を行い、安全に呼び出せる設計。

- 研究用ファクターモジュール
  - research.factor_research（src/kabusys/research/factor_research.py）
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して各種ファクター（モメンタム: 1/3/6 ヶ月、MA200 乖離 / ボラティリティ: ATR20 / 流動性指標 等）を計算する関数を追加。
    - SQL + ウィンドウ関数を用いた実装。データ不足時は None を返す扱いにして堅牢化。

- ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ平均/最大/P95）を集計し、閾値と比較して PASS/FAIL を出力するレポート機能を追加。
    - P95 計算、日付フィルタ、DB 存在チェック、テーブル未存在時のフォールバック処理を実装。
    - デフォルト閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。

- その他
  - monitoring DB 初期化呼び出し（init_monitoring_db）を起動スクリプト側で行い、監視テーブルが存在することを冪等的に保証。

### Changed
- （初回リリースのため差分履歴なし）

### Fixed
- （初回リリースのため差分履歴なし）

### Security
- .env ファイルの取り扱いに際して、生成された .env を Git にコミットしない旨の注意書きを config_setup に記載。

---

注:
- 上記はコードベースから推測した変更履歴です。実際のコミット履歴やリリースノートと異なる場合があります。必要であれば、さらにファイル単位の詳細な変更点（関数シグネチャ、デフォルト値、ログメッセージ等）を追記します。