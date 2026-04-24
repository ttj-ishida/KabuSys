CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/) に準拠して記載しています。
バージョン番号はパッケージに埋め込まれた __version__ に基づきます。

Unreleased
----------

（なし）

0.1.0 - 2026-04-24
-----------------

Added
- 基本リリース: KabuSys 初期実装を追加。
  - パッケージバージョン: __version__ = "0.1.0"

- 設定管理
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索して検出）。
  - .env のパースは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを実装し、アプリ設定をプロパティ経由で取得可能に（J-Quants トークン、kabu API、DB パス、ログレベル、環境種別など）。
  - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）や KABUSYS_ENV の許容値検証を実装。

- 環境設定ウィザード CLI
  - kabusys.config_setup: 対話式ウィザードで .env を作成/更新するツールを追加。
  - シークレット入力のマスク表示、既存値の読み込みとデフォルト値の提示、保存の確認をサポート。
  - .env のテンプレート出力はコメント付き（Git にコミットしない旨を明記）。

- 設定検証 CLI
  - kabusys.validate_config: .env と config/*.yaml の基本チェックを行う CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML のパース確認（PyYAML 有無によるスキップ）を実施。
  - --strict フラグで警告も失敗扱いにできる。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper 用 SQLite (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止は data/stop_requested.flag を監視。停止時は engine.stop() を呼ぶ。
    - PID ファイル出力先を data/execution.pid に設定（Settings 経由で上書き可能）。
    - duckdb 統合（analytics 用ファイルへの接続）。

  - run_monitoring.py
    - SystemMonitor 用のポーリング起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし、警告を出す。
    - 監視用 DB 初期化（init_monitoring_db）を実行して監視テーブルの存在を保証。
    - 監視は監視 DB のパス（Settings.sqlite_path）を本番相当で参照する設計（環境に関わらず本番 sqlite_path を使用する旨の挙動）。
    - 停止フラグ（data/stop_requested.flag）を検知するとループを終了。

- ロギング & プロセス管理ユーティリティ
  - kabusys.utils.logging_setup
    - setup_logging を提供。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30世代保持）を設定。
    - LOG_LEVEL / LOG_DIR 環境変数や関数引数による解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで動作。
  - kabusys.utils.process_priority
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows/Linux/macOS 等の差分を吸収して適切に nice 値や Windows 優先度クラスを設定（psutil を利用）。権限不足等で設定できない場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: Buy シグナルをスコア降順（タイブレークは signal_rank）で選択。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等分にフォールバック、警告あり）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を検出して新規候補を除外するロジックを実装（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（警告）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケーリング（端数配分アルゴリズム含む）、cost_buffer（手数料/スリッページ見積）対応。
    - risk_based 方式は risk_pct / stop_loss_pct を用いた株数計算を実装。

- 研究（Research）
  - kabusys.research.factor_research にてファクター計算モジュールを開始。
    - モメンタム、MA200乖離、ATR、流動性などの計算を行う設計。DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針を採用。
    - （calc_momentum の実装が途中まで追加されている。詳細は Known issues を参照）

- ツール
  - kabusys.tools.paper_verification_report
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、レイテンシ（平均/最大/P95）を集計して PASS/FAIL を判定するしきい値を実装（デフォルト: 稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - SQLite（PAPER_TRADING_SQLITE_PATH / --db）からデータを読み込み、期間フィルタ（--from / --to）をサポート。
    - P95 計算、NULL 値やテーブル未存在時の安全なフォールバック対応あり。

- その他
  - duckdb 統合: 分析用に DuckDB 接続を利用する設計を各所で採用（起動スクリプトや研究モジュール）。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を参照して監視テーブルの存在を保証するフローを追加。

Notes / 注意事項
- 環境変数とファイルパス
  - .env の初期生成は kabusys.config_setup を推奨。生成後は kabusys.validate_config で検証してください。
  - paper_trading モードは paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使います。production の監視 DB と意図的に分離されています。
  - run_monitoring は監視 DB（Settings.sqlite_path）を環境に関係なく使用する実装です。必要な場合は環境変数で sqlite_path を上書きしてください。

- 停止/制御
  - run_execution/run_monitoring はプロジェクトルートの data/stop_requested.flag を監視して安全に停止します。停止フラグの場所はコード内定義（data/stop_requested.flag）に依存します。

Known issues / TODO
- kabusys.research.factor_research の calc_momentum 実装がファイル末尾で途中（トランケート）になっており、完全実装が未完です。以降のファクター実装（Value/Volatility/Liquidity）も未完成の可能性があります。
- position_sizing.apply の一部で price が欠損(0.0) の場合にエクスポージャーの過少見積りが発生する旨の TODO コメントがあります。将来的に前日終値等のフォールバック価格を導入する予定。
- set_process_priority / set_cpu_affinity は権限不足やプラットフォーム差分で動作できない場合があり、その際は警告を出してスキップします（意図的な安全設計）。
- monitoring / execution の細部（Engine 内部実装や SystemMonitor の挙動、DB スキーマなど）は本稿でカバーしていません。起動時はログや validate_config の出力で事前確認してください。

Security
- .env は決してリポジトリに含めないでください（config_setup のヘッダにも明記）。シークレット情報（API トークン等）は運用時に安全に管理してください。

参考コマンド
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上