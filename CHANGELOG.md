# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。主な変更点を日本語でまとめています。

全般的注意
- このリポジトリはバージョン管理下の Python パッケージ形式で提供されます。パッケージのバージョンは src/kabusys/__init__.py の __version__ に記載されています。
- 多くの CLI スクリプトやユーティリティは環境変数で挙動を制御します。README や .env を参照してください。

Unreleased
- （なし）

[0.1.0] - 2026-04-18
====================
Added
- 基本アプリケーション基盤を追加
  - パッケージメタデータ: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 起動スクリプト / デーモン系
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止制御: プロジェクト直下 data/stop_requested.flag ファイルを検出してループを終了。
    - 起動時にプロセス優先度（high）を設定。
    - 監視用 DB（SQLite）と分析用 DuckDB への接続を行い、監視 DB の初期化（init_monitoring_db）を実施。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を参照する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を追加（MockBrokerClient を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - スレッドベースの実行（デーモンスレッド）と停止フラグによる安全停止処理を実装。
    - 起動時にプロセス優先度（high）を設定。
- 設定・環境変数関連
  - config.py
    - .env ファイル自動読み込み機能を実装（.env, .env.local の順、OS 環境変数は保護）。
    - .env の読み込みはプロジェクトルート（.git または pyproject.toml）を基準に探索。テスト等で自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理）。
    - Settings クラスを提供。J-Quants / kabu ステーション / LINE / DB / 監視閾値 / システム設定など多数のプロパティを環境変数から取得するユーティリティを実装。
    - PAPER_FILL_MODE の妥当性検査、有効値チェックを実装。
    - KABUSYS_ENV / LOG_LEVEL 等の検証ロジックを実装し、不正値時に例外を送出する。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 各設定項目の説明、デフォルト、シークレットマスク表示、確認プロンプト、書き込みロジックを提供。
    - .env 生成時に .env のテンプレート形式で安全に書き出す。
  - validate_config.py
    - 起動前の設定検証ツールを追加（必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在とパース検査など）。
    - --strict オプションで警告を失敗扱い（exit 1）にできる。
    - 本番（live）環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
- 監視関連
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出すことで監視テーブルの存在を保証（冪等）。
  - SystemMonitor を利用した単一チェック実行と例外ハンドリング（ログ出力して次ポーリングへ継続）。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。標準出力（stdout）用 StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/）をルートロガーに設定。
    - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力だけにフォールバック。
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定機能を追加（Windows / POSIX に対応）。set_process_priority(level) を提供。
    - CPU affinity 設定用 set_cpu_affinity(cpu_count) を追加（存在しない環境では安全にスキップ）。
    - 権限不足や未実装 API が存在する場合は警告ログを出して処理をスキップする安全設計。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates(): スコア降順で候補抽出、タイブレークルールを実装。
    - calc_equal_weights(), calc_score_weights(): 等金額配分およびスコア加重配分を実装。全スコアが 0 の場合は等金額へフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中上限を考慮して候補リストをフィルタする関数を実装。売却予定銘柄の除外や "unknown" セクターの扱いについて明記。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に対する乗数を返すユーティリティを実装（未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method（risk_based / equal / score）に応じた発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウンと残余の配分ロジックを実装。手数料・スリッページ見積り用 cost_buffer に対応。
- Paper Trading・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率・送信率、レイテンシ、リスク却下数）を集計してレポートを出力するツールを追加。
    - P95 計算、期間フィルタ（--from / --to）、DB ファイルパス上書き（--db または環境変数）をサポート。
    - デフォルト閾値を定義し、Fail/Pass 判定を行う（稼働率 >= 99%、注文成功率 >= 90% など）。
- research/factor_research.py
  - DuckDB を用いたファクター計算モジュール（モメンタム / MA200 / ATR / 流動性等を想定）の土台を追加。calc_momentum 等の関数が設計済み（DuckDB 接続受け取り、prices_daily テーブル参照の想定）。
- その他
  - pakage exports: portfolio パッケージの __init__ で主要関数を公開。

Changed
- .env 読み込みロジック
  - OS 環境変数の保護機構を導入。デフォルトで OS 側の環境変数を上書きしない動作に変更（.env.local で明示的上書き可能）。
- ログ出力先の標準化
  - stdout を StreamHandler に用いることで cron / Task Scheduler でのリダイレクト運用を想定。

Fixed
- 環境変数パースの堅牢化
  - .env のクォート内エスケープやインラインコメントの取り扱いに関するバグ回避処理を追加。

Security
- .env は絶対に Git にコミットしないことを .env 作成ウィザードのドキュメントにて強調。

Notes / Migration
- デフォルト DB/ファイルパス
  - DuckDB: data/kabusys.duckdb
  - 監視用 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
- 本番起動時には KABUSYS_ENV を "live" に設定し、LINE 通知等の設定が適切に行われていることを validate_config.py で事前確認してください。
- run_execution は paper_trading 環境で本番 DB にアクセスしない設計ですが、環境変数設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH 等）。

既知の制約 / TODO（コード内注釈より）
- position_sizing.calc_position_sizes: price が欠損（0.0）の場合のフォールバック価格に関する TODO が残っています（前日終値や取得原価のフォールバックを検討）。
- research/factor_research.py はファクター群の実装方針が記載されており、一部関数の実装が続く想定です。
- 一部機能（ブローカークライアントの具象実装、ExecutionEngine の詳細、SystemMonitor の実装など）は別モジュールに依存しており、その実装次第で挙動が変わります。

貢献
- 初期リリースにつき、バグ報告・改善提案は issue を立ててください。環境変数・ファイルパス周りの設定ミスが原因の質問が多く予想されますので、validate_config の活用を推奨します。